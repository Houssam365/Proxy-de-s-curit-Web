# Fichier: proxy_source/client_proxy.py

import socket
import threading
from urllib.parse import urlparse
import sys
from cryptography import exceptions as crypto_exceptions

# Imports des configurations et des fonctions cryptographiques
from web_security_proxy.config.settings import SOURCE_PROXY_HOST, SOURCE_PROXY_PORT, DESTINATION_PROXY_HOST, DESTINATION_PROXY_PORT, BUFFER_SIZE
from .crypto_client import load_public_key, generate_and_encrypt_session_key, encrypt_data, decrypt_data

# --- Fonctions de Gestion de Connexion ---

def get_request_headers(client_socket):
    """Lit la requête HTTP brute du navigateur jusqu'à la fin des en-têtes."""
    data = b""
    while True:
        try:
            chunk = client_socket.recv(BUFFER_SIZE)
            if not chunk: return None
            data += chunk
            if b'\r\n\r\n' in data: return data
        except socket.error: return None

def initiate_secure_handshake(target_socket):
    """Exécute l'échange de clé RSA avec le Proxy de Sortie."""
    global SESSION_KEY, ENCRYPTED_SESSION_KEY
    
    # 1. Envoi du message 'HELLO'
    target_socket.sendall(b"PROXY_SECURITY_HELLO\r\n") 
    
    # 2. Réception de la clé publique (PEM)
    pem_data = b""
    while True:
        chunk = target_socket.recv(BUFFER_SIZE)
        if not chunk:
            raise Exception("Connexion fermée pendant l'échange de clé.")
        pem_data += chunk
        if b'-----END PUBLIC KEY-----\n' in pem_data:
            break
    
    load_public_key(pem_data)
    
    # 3. Génération et Chiffrement de la Clé de Session
    encrypted_session_key, session_key = generate_and_encrypt_session_key()
    
    # 4. Envoi de la clé de session chiffrée
    key_transmission = b"ENCRYPTED_SESSION_KEY:" + encrypted_session_key + b":END_KEY\r\n"
    target_socket.sendall(key_transmission)
    
    print("[*] Poignée de main réussie. Clé de session AES établie.")
    return session_key

def handle_browser_connection(browser_socket):
    """Gère la connexion du navigateur, établissement du tunnel chiffré et relai."""
    target_socket = None
    session_key = None
    
    try:
        # 1. Connexion au Proxy de Sortie
        target_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        target_socket.connect((DESTINATION_PROXY_HOST, DESTINATION_PROXY_PORT))
        
        # 2. Poignée de main RSA (Échange de clé)
        session_key = initiate_secure_handshake(target_socket)
        
        # --- PHASE 2 : TRAFIC CHIFFRÉ (Étape 3) ---
        
        # 3. Réception de la requête HTTP brute du navigateur
        raw_http_request = get_request_headers(browser_socket) 
        if not raw_http_request: return

        # 4. CHIFFREMENT de la requête
        encrypted_request = encrypt_data(raw_http_request, session_key) 

        # 5. Envoi au Proxy de Sortie
        target_socket.sendall(encrypted_request)

        # 6. Relais de la réponse (Réception CHIFFRÉE, DÉCHIFFREMENT, Renvoi au navigateur)
        while True:
            # Réception du bloc de données CHIFFRÉ
            encrypted_response_chunk = target_socket.recv(BUFFER_SIZE)
            if not encrypted_response_chunk:
                break
            
            # DÉCHIFFREMENT
            decrypted_response = decrypt_data(encrypted_response_chunk, session_key)
            
            # Renvoi au navigateur
            browser_socket.sendall(decrypted_response) 
            
    except crypto_exceptions.InvalidTag:
        print("[!!!] ALERTE SÉCURITÉ : Trafic altéré ou clé invalide dans la réponse.")
    except socket.error as e:
        print(f"[!] Erreur de socket (cible injoignable ou autre) : {e}")
    except Exception as e:
        print(f"[!] Erreur inattendue : {e}")
        
    finally:
        if target_socket: target_socket.close()
        browser_socket.close()
        print("[*] Fin de la session chiffrée.")


def start_proxy():
    """Point d'entrée du Proxy Source."""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_socket.bind((SOURCE_PROXY_HOST, SOURCE_PROXY_PORT))
    except socket.error as e:
        print(f"[!] Échec de la liaison au port {SOURCE_PROXY_PORT} : {e}")
        sys.exit(1)
        
    server_socket.listen(5) 
    print(f"[*] Proxy Source en écoute sur {SOURCE_PROXY_HOST}:{SOURCE_PROXY_PORT}")
    
    while True:
        try:
            browser_socket, _ = server_socket.accept()
            client_handler = threading.Thread(target=handle_browser_connection, args=(browser_socket,))
            client_handler.start()
        except KeyboardInterrupt:
            print("\n[*] Arrêt du Proxy Source.")
            break
        except Exception as e:
            print(f"[!] Erreur générale dans la boucle d'acceptation : {e}")
            
    server_socket.close()

if __name__ == "__main__":
    start_proxy()