# crypto_utils.py
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding as sym_padding
from cryptography.hazmat.backends import default_backend
import os

# ========================
# RSA
# ========================

def generate_rsa_keys():
    """Génère une paire de clés RSA (privée + publique)."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    public_key = private_key.public_key()
    return private_key, public_key

def rsa_encrypt(public_key, message: bytes) -> bytes:
    """Chiffre un message avec la clé publique RSA."""
    return public_key.encrypt(
        message,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )

def rsa_decrypt(private_key, ciphertext: bytes) -> bytes:
    """Déchiffre un message avec la clé privée RSA."""
    return private_key.decrypt(
        ciphertext,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )

# ========================
# AES-GCM
# ========================

def generate_aes_key(key_size=32):
    """Génère une clé AES aléatoire (32 bytes = 256 bits)."""
    return os.urandom(key_size)

def aes_encrypt(key: bytes, plaintext: bytes) -> tuple[bytes, bytes, bytes]:
    """
    Chiffre les données avec AES-GCM.
    Retourne (nonce, ciphertext, tag)
    """
    nonce = os.urandom(12)  # 96 bits recommandé pour GCM
    cipher = Cipher(algorithms.AES(key), modes.GCM(nonce), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(plaintext) + encryptor.finalize()
    tag = encryptor.tag
    return nonce, ciphertext, tag

def aes_decrypt(key: bytes, nonce: bytes, ciphertext: bytes, tag: bytes) -> bytes:
    """
    Déchiffre les données avec AES-GCM.
    """
    cipher = Cipher(algorithms.AES(key), modes.GCM(nonce, tag), backend=default_backend())
    decryptor = cipher.decryptor()
    return decryptor.update(ciphertext) + decryptor.finalize()


# ========================
# Test rapide du module
# ========================
if __name__ == "__main__":
    print("Module crypto_utils exécuté directement")
    
    # Test RSA
    priv, pub = generate_rsa_keys()
    msg = b"Bonjour anas !"
    encrypted = rsa_encrypt(pub, msg)
    decrypted = rsa_decrypt(priv, encrypted)
    print("RSA:", decrypted)
    
    # Test AES
    aes_key = generate_aes_key()
    nonce, ciphertext, tag = aes_encrypt(aes_key, b"Message secret")
    decrypted_aes = aes_decrypt(aes_key, nonce, ciphertext, tag)
    print("AES-GCM:", decrypted_aes)
