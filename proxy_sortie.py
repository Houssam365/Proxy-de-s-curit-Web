# proxy_sortie.py
import socket
import threading
import requests  # Pour faire les requêtes HTTP
from crypto_utils import generate_rsa_keys, rsa_encrypt, rsa_decrypt, aes_encrypt, aes_decrypt

# ========================
# Configuration
# ========================
HOST = "127.0.0.1"   # Adresse du proxy de sortie
PORT = 9090          # Port d'écoute pour le proxy d'entrée

# ========================
# Clés RSA pour échange AES
# ========================
private_key, public_key = generate_rsa_keys()

# ========================
# Gestion d'une connexion depuis le proxy d'entrée
# ========================
def handle_proxy_entree(client_socket):
    try:
        # 1️⃣ Réception de la clé AES chiffrée via RSA
        encrypted_aes_key = client_socket.recv(1024)  # Taille max de clé RSA chiffrée
        aes_key = rsa_decrypt(private_key, encrypted_aes_key)
        print("Clé AES reçue et déchiffrée avec succès")

        while True:
            # 2️⃣ Réception du trafic chiffré
            data = client_socket.recv(8192)
            if not data:
                break

            # Extraction nonce, tag, ciphertext
            nonce = data[:12]
            tag = data[12:28]
            ciphertext = data[28:]
            
            # Déchiffrement AES
            decrypted_request = aes_decrypt(aes_key, nonce, ciphertext, tag)
            
            # 3️⃣ Envoyer la requête HTTP réelle
            # Pour simplification, on envoie uniquement GET
            try:
                request_lines = decrypted_request.decode().split("\r\n")
                url = request_lines[0].split()[1]  # "GET /path HTTP/1.1" -> "/path"
                headers = {}  # Optionnel: ajouter les headers si besoin
                
                if not url.startswith("http"):
                    # Ajouter un domaine de test si seulement le path est envoyé
                    url = "http://example.com" + url

                response = requests.get(url, headers=headers)
                response_data = response.content
            except Exception as e:
                response_data = f"Erreur lors de la requête HTTP: {e}".encode()

            # 4️⃣ Chiffrement AES de la réponse
            nonce_r, ciphertext_r, tag_r = aes_encrypt(aes_key, response_data)
            client_socket.sendall(nonce_r + tag_r + ciphertext_r)

    except Exception as e:
        print("Erreur dans handle_proxy_entree:", e)
    finally:
        client_socket.close()


# ========================
# Serveur principal
# ========================
def start_proxy_sortie():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(5)
    print(f"Proxy de sortie démarré sur {HOST}:{PORT}")
    
    while True:
        client_socket, addr = server.accept()
        print(f"Connexion reçue du proxy d'entrée {addr}")
        client_handler = threading.Thread(target=handle_proxy_entree, args=(client_socket,))
        client_handler.start()


# ========================
# Point d’entrée
# ========================
if __name__ == "__main__":
    start_proxy_sortie()
