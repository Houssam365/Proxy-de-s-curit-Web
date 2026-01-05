use axum::{
    extract::State,
    routing::{get, post},
    Json, Router,
};
use common::{
    decrypt_aes, decrypt_with_rsa, encrypt_aes, generate_rsa_keys, EncryptedPayload,
    EncryptedResponse, ProxyRequest, ProxyResponse,
};
use std::sync::Arc;
use tokio::net::TcpListener;
use base64::{Engine as _, engine::general_purpose::STANDARD as b64};

struct AppState {
    priv_key: String,
    pub_key: String,
}

#[tokio::main]
async fn main() {
    println!("Starting Exit Proxy...");
    // 1. Generate RSA keys
    let (priv_key, pub_key) = generate_rsa_keys().expect("Failed to generate keys");
    println!("RSA Keys generated.");

    let state = Arc::new(AppState { priv_key, pub_key });

    // 2. Setup Router
    let app = Router::new()
        .route("/public-key", get(get_public_key))
        .route("/proxy", post(handle_proxy))
        .with_state(state);

    // 3. Bind and Serve
    let listener = TcpListener::bind("0.0.0.0:8080").await.unwrap();
    println!("Exit Proxy listening on 0.0.0.0:8080");
    axum::serve(listener, app).await.unwrap();
}

async fn get_public_key(State(state): State<Arc<AppState>>) -> String {
    state.pub_key.clone()
}

async fn handle_proxy(
    State(state): State<Arc<AppState>>,
    Json(payload): Json<EncryptedPayload>,
) -> Json<EncryptedResponse> {
    // 1. Decode Base64 fields
    let encrypted_aes_key = b64.decode(&payload.encrypted_aes_key).unwrap();
    let aes_nonce = b64.decode(&payload.aes_nonce).unwrap();
    let encrypted_data = b64.decode(&payload.encrypted_data).unwrap();

    // 2. Decrypt AES Key using RSA Private Key
    let aes_key_vec = decrypt_with_rsa(&state.priv_key, &encrypted_aes_key)
        .expect("RSA Decryption failed");
    
    // Convert to [u8; 32]
    let mut aes_key = [0u8; 32];
    aes_key.copy_from_slice(&aes_key_vec);

    // 3. Decrypt Body using AES Key
    let plaintext_json = decrypt_aes(&aes_key, &aes_nonce, &encrypted_data)
        .expect("AES Decryption failed");

    // 4. Deserialize ProxyRequest
    let req_data: ProxyRequest = serde_json::from_slice(&plaintext_json).unwrap();
    println!("Processing request for: {}", req_data.target_url);

    // 5. Execute Request
    let client = reqwest::Client::new();
    let mut req_builder = client.request(
        req_data.method.parse().unwrap(),
        &req_data.target_url
    );
    
    for (k, v) in req_data.headers {
        req_builder = req_builder.header(k, v);
    }
    
    // If body exists
    if !req_data.body.is_empty() {
        req_builder = req_builder.body(req_data.body);
    }

    let resp = req_builder.send().await;

    // 6. Form ProxyResponse
    let proxy_resp = match resp {
        Ok(res) => {
            let status = res.status().as_u16();
            let mut headers = Vec::new();
            for (k, v) in res.headers() {
                let k_str = k.as_str();
                // Filter content-length (we re-compute it) and connection controls
                if !k_str.eq_ignore_ascii_case("content-length") 
                   && !k_str.eq_ignore_ascii_case("transfer-encoding") 
                   && !k_str.eq_ignore_ascii_case("connection") 
                   && !k_str.eq_ignore_ascii_case("keep-alive")
                   && !k_str.eq_ignore_ascii_case("proxy-authenticate")
                   && !k_str.eq_ignore_ascii_case("proxy-authorization")
                   && !k_str.eq_ignore_ascii_case("te")
                   && !k_str.eq_ignore_ascii_case("trailer")
                   && !k_str.eq_ignore_ascii_case("upgrade") {
                    if let Ok(val) = v.to_str() {
                        headers.push((k.to_string(), val.to_string()));
                    }
                }
            }
            let body = res.bytes().await.unwrap_or_default().to_vec();
            println!("Response fetched from target. Status: {}", status);
            ProxyResponse { status, headers, body }
        }
        Err(e) => {
            println!("Request failed: {}", e);
            ProxyResponse {
                status: 502,
                headers: vec![],
                body: format!("Proxy Error: {}", e).into_bytes(),
            }
        }
    };

    // 7. Encrypt Response
    let resp_bytes = serde_json::to_vec(&proxy_resp).unwrap();
    let (new_nonce, encrypted_resp_data) = encrypt_aes(&aes_key, &resp_bytes).unwrap();

    println!("Response encrypted and sending back.");
    // 8. Return
    Json(EncryptedResponse {
        aes_nonce: b64.encode(new_nonce),
        encrypted_data: b64.encode(encrypted_resp_data),
    })
}
