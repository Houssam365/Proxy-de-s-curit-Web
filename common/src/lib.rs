use aes_gcm::{
    aead::{Aead, AeadCore, KeyInit, OsRng},
    Aes256Gcm, Key, Nonce
};
use rsa::{
    Pkcs1v15Encrypt, RsaPrivateKey, RsaPublicKey,
    pkcs8::{DecodePublicKey, EncodePublicKey, LineEnding},
    pkcs1::{EncodeRsaPrivateKey, DecodeRsaPrivateKey},
};
use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize, Debug)]
pub struct ProxyRequest {
    pub target_url: String,
    pub method: String,
    pub headers: Vec<(String, String)>,
    pub body: Vec<u8>,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct ProxyResponse {
    pub status: u16,
    pub headers: Vec<(String, String)>,
    pub body: Vec<u8>,
}

pub fn generate_rsa_keys() -> anyhow::Result<(String, String)> {
    let mut rng = rand::thread_rng();
    let bits = 2048;
    let priv_key = RsaPrivateKey::new(&mut rng, bits)?;
    let pub_key = RsaPublicKey::from(&priv_key);

    let priv_pem = priv_key.to_pkcs1_pem(LineEnding::LF)?;
    let pub_pem = pub_key.to_public_key_pem(LineEnding::LF)?;

    Ok((priv_pem.to_string(), pub_pem.to_string()))
}

pub fn encrypt_with_rsa(pub_key_pem: &str, data: &[u8]) -> anyhow::Result<Vec<u8>> {
    let pub_key = RsaPublicKey::from_public_key_pem(pub_key_pem)?;
    let mut rng = rand::thread_rng();
    let enc_data = pub_key.encrypt(&mut rng, Pkcs1v15Encrypt, data)?;
    Ok(enc_data)
}

pub fn decrypt_with_rsa(priv_key_pem: &str, data: &[u8]) -> anyhow::Result<Vec<u8>> {
    let priv_key = RsaPrivateKey::from_pkcs1_pem(priv_key_pem)?;
    let dec_data = priv_key.decrypt(Pkcs1v15Encrypt, data)?;
    Ok(dec_data)
}

pub fn generate_aes_key() -> [u8; 32] {
    let key = Aes256Gcm::generate_key(&mut OsRng);
    key.into()
}

pub fn encrypt_aes(key: &[u8; 32], plaintext: &[u8]) -> anyhow::Result<(Vec<u8>, Vec<u8>)> {
    let key = Key::<Aes256Gcm>::from_slice(key);
    let cipher = Aes256Gcm::new(key);
    let nonce = Aes256Gcm::generate_nonce(&mut OsRng); // 96-bits; unique per message
    let ciphertext = cipher.encrypt(&nonce, plaintext).map_err(|e| anyhow::anyhow!("AES encrypt error: {}", e))?;
    Ok((nonce.to_vec(), ciphertext))
}

pub fn decrypt_aes(key: &[u8; 32], nonce: &[u8], ciphertext: &[u8]) -> anyhow::Result<Vec<u8>> {
    let key = Key::<Aes256Gcm>::from_slice(key);
    let cipher = Aes256Gcm::new(key);
    let nonce = Nonce::from_slice(nonce);
    let plaintext = cipher.decrypt(nonce, ciphertext).map_err(|e| anyhow::anyhow!("AES decrypt error: {}", e))?;
    Ok(plaintext)
}

#[derive(Serialize, Deserialize)]
pub struct EncryptedPayload {
    pub encrypted_aes_key: String, // Base64 RSA encrypted AES key
    pub aes_nonce: String,         // Base64
    pub encrypted_data: String,    // Base64 AES encrypted data (serialized ProxyRequest)
}

#[derive(Serialize, Deserialize)]
pub struct EncryptedResponse {
    pub aes_nonce: String,
    pub encrypted_data: String, // AES encrypted ProxyResponse (using same key as request)
}
