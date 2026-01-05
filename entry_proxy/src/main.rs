use axum::{
    body::Body,
    extract::{State, Request},
    response::Response,
    Router,
};
use common::{
    decrypt_aes, encrypt_aes, encrypt_with_rsa, generate_aes_key, EncryptedPayload,
    EncryptedResponse, ProxyRequest, ProxyResponse,
};
use http_body_util::BodyExt;
use std::sync::Arc;
use tokio::net::TcpListener;
use base64::{Engine as _, engine::general_purpose::STANDARD as b64};
use reqwest::Client;
use std::env;

struct AppState {
    exit_proxy_url: String,
    exit_proxy_pubkey: String,
    client: Client,
}

#[tokio::main]
async fn main() {
    println!("Starting Entry Proxy...");
    let exit_proxy_base = env::var("EXIT_PROXY_URL").unwrap_or_else(|_| "http://exit_proxy:8080".to_string());
    
    // 1. Fetch Public Key
    let client = Client::new();
    let pub_key_url = format!("{}/public-key", exit_proxy_base);
    println!("Fetching public key from: {}", pub_key_url);
    
    // Retry loop for startup
    let mut exit_proxy_pubkey = String::new();
    loop {
        match client.get(&pub_key_url).send().await {
            Ok(resp) => {
                if let Ok(text) = resp.text().await {
                    exit_proxy_pubkey = text;
                    println!("Got Public Key!");
                    break;
                }
            }
            Err(_) => {
                println!("Waiting for Exit Proxy...");
                tokio::time::sleep(tokio::time::Duration::from_secs(2)).await;
            }
        }
    }

    let state = Arc::new(AppState {
        exit_proxy_url: format!("{}/proxy", exit_proxy_base),
        exit_proxy_pubkey,
        client,
    });

    // 2. Setup Router - specific handler for everything
    let app = Router::new()
        .fallback(handle_incoming_request)
        .with_state(state);

    // 3. Bind
    let listener = TcpListener::bind("0.0.0.0:8081").await.unwrap();
    println!("Entry Proxy listening on 0.0.0.0:8081");
    axum::serve(listener, app).await.unwrap();
}

async fn handle_incoming_request(
    State(state): State<Arc<AppState>>,
    req: Request<Body>,
) -> Response<Body> {
    // 1. Parse incoming request
    let (parts, body) = req.into_parts();
    let method = parts.method.to_string();
    let uri = parts.uri.to_string(); // In proxy mode, this is full URL
    
    // Check if it's strictly HTTP (basic requirement)
    // If browser uses this as proxy, URI is absolute "http://example.com/foo"
    // If testing via curl directly, might be path only.
    // We assume target is in the URI.
    
    let headers: Vec<(String, String)> = parts.headers.iter()
        .map(|(k, v)| (k.to_string(), v.to_str().unwrap_or("").to_string()))
        .collect();
    
    let body_bytes = body.collect().await.unwrap().to_bytes().to_vec();

    let proxy_req = ProxyRequest {
        target_url: uri,
        method,
        headers,
        body: body_bytes,
    };

    println!("Encrypting request for: {}", proxy_req.target_url);

    // 2. Crypto Setup
    let aes_key = generate_aes_key();
    let serialized_req = serde_json::to_vec(&proxy_req).unwrap();

    // 3. Encrypt AES Key with RSA
    let encrypted_aes_key_bytes = encrypt_with_rsa(&state.exit_proxy_pubkey, &aes_key).unwrap();
    
    // 4. Encrypt Data with AES
    let (nonce, encrypted_data_bytes) = encrypt_aes(&aes_key, &serialized_req).unwrap();

    // 5. Send to Exit Proxy
    let payload = EncryptedPayload {
        encrypted_aes_key: b64.encode(encrypted_aes_key_bytes),
        aes_nonce: b64.encode(nonce),
        encrypted_data: b64.encode(encrypted_data_bytes),
    };

    let exit_resp_result = state.client.post(&state.exit_proxy_url)
        .json(&payload)
        .send()
        .await;

    match exit_resp_result {
        Ok(exit_resp) => {
            if exit_resp.status().is_success() {
                let enc_resp: EncryptedResponse = match exit_resp.json().await {
                    Ok(val) => val,
                    Err(e) => return Response::builder().status(502).body(Body::from(format!("Failed to parse JSON from Exit Proxy: {}", e))).unwrap(),
                };
                
                // Decrypt
                let nonce_bytes = match b64.decode(&enc_resp.aes_nonce) {
                    Ok(v) => v,
                    Err(e) => return Response::builder().status(502).body(Body::from(format!("Failed to decode nonce: {}", e))).unwrap(),
                };
                let params_bytes = match b64.decode(&enc_resp.encrypted_data) {
                    Ok(v) => v,
                    Err(e) => return Response::builder().status(502).body(Body::from(format!("Failed to decode data: {}", e))).unwrap(),
                };
                
                let decrypted_resp_bytes = match decrypt_aes(&aes_key, &nonce_bytes, &params_bytes) {
                    Ok(v) => v,
                    Err(e) => return Response::builder().status(502).body(Body::from(format!("Failed to decrypt response: {}", e))).unwrap(),
                };

                let proxy_resp: ProxyResponse = match serde_json::from_slice(&decrypted_resp_bytes) {
                    Ok(v) => v,
                    Err(e) => return Response::builder().status(502).body(Body::from(format!("Failed to deserialize proxy response: {}", e))).unwrap(),
                };

                println!("Decrypted response. Status: {}", proxy_resp.status);

                // Build Axum Response
                let mut builder = Response::builder().status(proxy_resp.status);
                for (k, v) in proxy_resp.headers {
                     // Check for validity before adding to avoid panic
                     if let Ok(hname) = axum::http::HeaderName::from_bytes(k.as_bytes()) {
                        if let Ok(hval) = axum::http::HeaderValue::from_str(&v) {
                            builder = builder.header(hname, hval);
                        }
                     }
                }
                builder.body(Body::from(proxy_resp.body)).unwrap()
            } else {
                let status = exit_resp.status();
                let text = exit_resp.text().await.unwrap_or_default();
                println!("Exit proxy returned error: {} - {}", status, text);
                Response::builder()
                    .status(502)
                    .body(Body::from(format!("Exit Proxy returned error status {}: {}", status, text)))
                    .unwrap()
            }
        },
        Err(e) => {
             println!("Failed to contact Exit Proxy: {}", e);
             Response::builder()
                .status(502)
                .body(Body::from(format!("Failed to reach Exit Proxy: {}", e)))
                .unwrap()
        }
    }
}
