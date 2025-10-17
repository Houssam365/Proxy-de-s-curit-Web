# proxy_entree.py
import socket
import threading
from crypto_utils import generate_rsa_keys, rsa_encrypt, rsa_decrypt, aes_encrypt, aes_decrypt, generate_aes_key

# ========================
# Configuration
# ========================
HOST = "127.0.0.1"       # Adresse du proxy source
PORT = 8080              # Port sur lequel le navigateur se connecte

PROXY_SORTIE_HOST = "127.0.0.1"  # Adresse du proxy de sortie
PROXY_SORTIE_PORT = 9090         # Port du proxy de sortie

# ========================
# Clés RSA pour échange AES
# ========================
private_key, public_key = generate_rsa_keys()

# ========================
# Fonction de gestion d'une connexion
# ========================
def handle_client(client_socket):
    try:
        # 1️⃣ Connexion au proxy de sortie
        sortie_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sortie_socket.connect((PROXY_SORTIE_HOST, PROXY_SORTIE_PORT))
        
        # 2️⃣ Génération de la clé AES et envoi via RSA
        aes_key = generate_aes_key()
        encrypted_aes_key = rsa_encrypt(public_key, aes_key)  # Ici on simule échange, en vrai il faut utiliser clé publique du proxy sortie
        sortie_socket.sendall(encrypted_aes_key)
        
        # 3️⃣ Boucle de réception de requêtes du navigateur
        while True:
            request = client_socket.recv(4096)
            if not request:
                break
            
            # Chiffrement AES
            nonce, ciphertext, tag = aes_encrypt(aes_key, request)
            # Envoi au proxy de sortie
            sortie_socket.sendall(nonce + tag + ciphertext)
            
            # Réception de la réponse chiffrée du proxy de sortie
            data = sortie_socket.recv(8192)
            if not data:
                break
            # Extraction nonce, tag, ciphertext
            nonce_r = data[:12]
            tag_r = data[12:28]
            ciphertext_r = data[28:]
            decrypted_response = aes_decrypt(aes_key, nonce_r, ciphertext_r, tag_r)
            
            # Renvoi au navigateur
            client_socket.sendall(decrypted_response)
    
    except Exception as e:
        print("Erreur dans handle_client:", e)
    finally:
        client_socket.close()
        sortie_socket.close()

# ========================
# Serveur principal
# ========================
def start_proxy():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(5)
    print(f"Proxy d’entrée démarré sur {HOST}:{PORT}")
    
    while True:
        client_socket, addr = server.accept()
        print(f"Connexion reçue de {addr}")
        client_handler = threading.Thread(target=handle_client, args=(client_socket,))
        client_handler.start()

# ========================
# Point d’entrée
# ========================
if __name__ == "__main__":
    start_proxy()
