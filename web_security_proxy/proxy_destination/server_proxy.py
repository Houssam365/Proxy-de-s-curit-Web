# Fichier: proxy_destination/server_proxy.py

import socket
import threading
import sys
from urllib.parse import urlparse
from cryptography import exceptions as crypto_exceptions

# Imports des configurations et des fonctions cryptographiques
from web_security_proxy.config.settings import DESTINATION_PROXY_HOST, DESTINATION_PROXY_PORT, BUFFER_SIZE
# Puis utilisez settings.DESTINATION_PROXY_HOST, etc.
from .crypto_server import generate_rsa_keys, decrypt_session_key, encrypt_data, decrypt_data

# --- Fonctions de Gestion de Connexion ---

def handle_proxy_client(client_socket):
    """Gère la connexion du Proxy Source."""
    
    try:
        # --- PHASE 1 : ÉCHANGE DE CLÉ RSA ---
        
        # 1. Réception du message HELLO
        hello = client_socket.recv(BUFFER_SIZE)
        if b"PROXY_SECURITY_HELLO" not in hello:
            raise Exception("Protocole de poignée de main invalide.")
        
        print("[*] Message HELLO reçu du Proxy Source.")
        
        # 2. Envoi de la clé publique RSA (générée au démarrage)
        from .crypto_server import PUBLIC_KEY_SERIALIZED
        client_socket.sendall(PUBLIC_KEY_SERIALIZED)
        print("[*] Clé publique RSA envoyée.")
        
        # 3. Réception de la clé de session chiffrée
        encrypted_key_data = b""
        while True:
            chunk = client_socket.recv(BUFFER_SIZE)
            if not chunk:
                raise Exception("Connexion fermée avant la réception de la clé de session.")
            encrypted_key_data += chunk
            if b":END_KEY" in encrypted_key_data:
                break
        
        # Extraction de la clé de session chiffrée
        start_idx = encrypted_key_data.find(b"ENCRYPTED_SESSION_KEY:") + len(b"ENCRYPTED_SESSION_KEY:")
        end_idx = encrypted_key_data.find(b":END_KEY")
        encrypted_session_key = encrypted_key_data[start_idx:end_idx]
        
        # 4. Déchiffrement de la clé de session
        session_key = decrypt_session_key(encrypted_session_key)
        print("[*] Clé de session déchiffrée et établie.")
        
        # --- PHASE 2 : TRAFIC CHIFFRÉ ---
        
        # 5. Réception et déchiffrement de la requête HTTP chiffrée
        encrypted_request = client_socket.recv(BUFFER_SIZE)
        if not encrypted_request:
            return
        
        # Déchiffrement de la requête
        try:
            decrypted_request = decrypt_data(encrypted_request, session_key)
        except crypto_exceptions.InvalidTag:
            print("[!!!] ALERTE SÉCURITÉ : Requête altérée ou clé invalide détectée.")
            return
        
        print(f"[*] Requête déchiffrée ({len(decrypted_request)} octets).")
        
        # 6. Extraction de l'URL cible depuis la requête HTTP
        target_host, target_port, request_path = parse_http_request(decrypted_request)
        
        # 7. Connexion au serveur web cible
        target_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        target_socket.connect((target_host, target_port))
        print(f"[*] Connecté au serveur web : {target_host}:{target_port}")
        
        # 8. Envoi de la requête au serveur web
        target_socket.sendall(decrypted_request)
        
        # 9. Relais de la réponse (Réception, CHIFFREMENT, Renvoi au Proxy Source)
        while True:
            response_chunk = target_socket.recv(BUFFER_SIZE)
            if not response_chunk:
                break
            
            # CHIFFREMENT de la réponse
            encrypted_response = encrypt_data(response_chunk, session_key)
            
            # Envoi au Proxy Source
            client_socket.sendall(encrypted_response)
        
        target_socket.close()
        print("[*] Relais de la réponse terminé.")
        
    except crypto_exceptions.InvalidTag:
        print("[!!!] ALERTE SÉCURITÉ : Trafic altéré ou clé invalide.")
    except socket.error as e:
        print(f"[!] Erreur de socket : {e}")
    except Exception as e:
        print(f"[!] Erreur inattendue : {e}")
    finally:
        client_socket.close()
        print("[*] Fin de la session du Proxy de Sortie.")

def parse_http_request(request_data):
    """Extrait l'hôte, le port et le chemin de la requête HTTP."""
    try:
        request_str = request_data.decode('utf-8', errors='ignore')
        lines = request_str.split('\r\n')
        
        # Extraire la ligne de requête (ex: "GET / HTTP/1.1")
        request_line = lines[0].split()
        request_path = request_line[1]
        
        # Extraire l'hôte depuis les en-têtes
        target_host = None
        target_port = 80
        
        for line in lines[1:]:
            if line.lower().startswith('host:'):
                host_header = line.split(':', 1)[1].strip()
                if ':' in host_header:
                    target_host, port_str = host_header.split(':', 1)
                    target_port = int(port_str)
                else:
                    target_host = host_header
                break
        
        if not target_host:
            raise ValueError("En-tête Host manquant dans la requête HTTP.")
        
        print(f"[*] URL cible extraite : {target_host}:{target_port}{request_path}")
        return target_host, target_port, request_path
        
    except Exception as e:
        print(f"[!] Erreur lors de l'analyse de la requête HTTP : {e}")
        raise

def start_proxy():
    """Point d'entrée du Proxy de Sortie."""
    
    # Générer les clés RSA au démarrage
    generate_rsa_keys()
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_socket.bind((DESTINATION_PROXY_HOST, DESTINATION_PROXY_PORT))
    except socket.error as e:
        print(f"[!] Échec de la liaison au port {DESTINATION_PROXY_PORT} : {e}")
        sys.exit(1)
    
    server_socket.listen(5)
    print(f"[*] Proxy de Sortie en écoute sur {DESTINATION_PROXY_HOST}:{DESTINATION_PROXY_PORT}")
    
    while True:
        try:
            client_socket, addr = server_socket.accept()
            print(f"[*] Nouvelle connexion du Proxy Source : {addr}")
            client_handler = threading.Thread(target=handle_proxy_client, args=(client_socket,))
            client_handler.daemon = True
            client_handler.start()
        except KeyboardInterrupt:
            print("\n[*] Arrêt du Proxy de Sortie.")
            break
        except Exception as e:
            print(f"[!] Erreur générale dans la boucle d'acceptation : {e}")
    
    server_socket.close()

if __name__ == "__main__":
    start_proxy()