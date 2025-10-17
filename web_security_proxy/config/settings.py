# Fichier: config/settings.py

# Configuration du Proxy Source (écoute du navigateur)
SOURCE_PROXY_HOST = "127.0.0.1"
SOURCE_PROXY_PORT = 8080

# Configuration du Proxy de Sortie (écoute du Proxy Source)
DESTINATION_PROXY_HOST = "127.0.0.1"
DESTINATION_PROXY_PORT = 9090

# Taille du buffer pour les transferts de données
BUFFER_SIZE = 4096

# --- Configuration Cryptographique ---

# Algorithme RSA pour l'échange de clé
RSA_KEY_SIZE = 2048
RSA_PUBLIC_EXPONENT = 65537

# Algorithme AES pour le chiffrement symétrique
AES_KEY_SIZE = 256  # bits (32 octets)
AES_IV_SIZE = 12    # bits (96 bits pour GCM)
AES_TAG_SIZE = 128  # bits (16 octets)

# Mode de chiffrement
CIPHER_MODE = "GCM"  # Galois/Counter Mode (authentification incluse)

# --- Configuration de Débogage ---
DEBUG = True
LOG_TRAFFIC = False  # Active les logs détaillés du trafic (attention : données sensibles)