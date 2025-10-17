# Fichier: proxy_source/crypto_client.py

from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography import exceptions as crypto_exceptions
import os

# Clés globales pour le Proxy Source
PUBLIC_KEY = None
SESSION_KEY = None

# --- Fonctions RSA ---

def load_public_key(pem_data):
    """Charge la clé publique RSA reçue du Proxy de Sortie (format PEM)."""
    global PUBLIC_KEY
    
    try:
        PUBLIC_KEY = serialization.load_pem_public_key(
            pem_data,
            backend=default_backend()
        )
        print("[*] Clé publique RSA chargée avec succès.")
    except Exception as e:
        raise Exception(f"Erreur lors du chargement de la clé publique : {e}")

def generate_and_encrypt_session_key():
    """Génère une clé de session AES-256 et la chiffre avec la clé publique RSA."""
    if PUBLIC_KEY is None:
        raise Exception("Clé publique RSA non chargée.")
    
    # Générer une clé de session AES-256 (32 octets)
    session_key = os.urandom(32)
    
    # Chiffrer la clé de session avec RSA OAEP
    encrypted_session_key = PUBLIC_KEY.encrypt(
        session_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    
    print(f"[*] Clé de session AES-256 générée et chiffrée ({len(session_key)} octets).")
    return encrypted_session_key, session_key

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
    
    if len(encrypted_data) < 28:  # 12 (IV) + 16 (Tag)
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