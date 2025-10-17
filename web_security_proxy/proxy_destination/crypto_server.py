# Fichier: proxy_destination/crypto_server.py

from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography import exceptions as crypto_exceptions
import os

# Clés globales pour le Proxy de Sortie
PRIVATE_KEY = None
PUBLIC_KEY_SERIALIZED = None # Clé publique à envoyer au Proxy Source

# --- Fonctions RSA ---

def generate_rsa_keys():
    """Génère la paire de clés RSA et sérialise la clé publique."""
    global PRIVATE_KEY, PUBLIC_KEY_SERIALIZED
    
    print("[*] Génération de la paire de clés RSA (2048 bits)...")
    
    # Générer la clé privée
    PRIVATE_KEY = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    
    # Sérialiser la clé publique au format PEM
    public_key = PRIVATE_KEY.public_key()
    PUBLIC_KEY_SERIALIZED = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    
    print("[*] Clés RSA générées.")
    return PUBLIC_KEY_SERIALIZED

def decrypt_session_key(encrypted_session_key):
    """Déchiffre la clé de session symétrique avec la clé privée RSA (OAEP)."""
    if PRIVATE_KEY is None:
        raise Exception("Clé privée RSA non initialisée.")
        
    session_key = PRIVATE_KEY.decrypt(
        encrypted_session_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return session_key

# --- Fonctions AES (Chiffrement Symétrique) ---

def encrypt_data(data, session_key):
    """Chiffre les données en utilisant AES-256 GCM (IV || Tag || Ciphertext)."""
    iv = os.urandom(12) 
    
    cipher = Cipher(
        algorithms.AES(session_key), 
        modes.GCM(iv), 
        backend=default_backend()
    )
    encryptor = cipher.encryptor()
    
    ciphertext = encryptor.update(data) + encryptor.finalize()
    tag = encryptor.tag
    
    return iv + tag + ciphertext

def decrypt_data(encrypted_data, session_key):
    """Déchiffre les données chiffrées par AES-256 GCM et vérifie l'authenticité."""
    
    if len(encrypted_data) < 28: # 12 (IV) + 16 (Tag)
        raise ValueError("Bloc chiffré trop court pour contenir IV et Tag.")

    iv = encrypted_data[:12]
    tag = encrypted_data[12:28]
    ciphertext = encrypted_data[28:]
    
    cipher = Cipher(
        algorithms.AES(session_key), 
        modes.GCM(iv, tag), 
        backend=default_backend()
    )
    decryptor = cipher.decryptor()
    
    return decryptor.update(ciphertext) + decryptor.finalize()