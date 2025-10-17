import socket

# Configuration
HOST = '127.0.0.1'       # Adresse locale (le proxy écoute ici)
PORT = 8080              # Port d'écoute du proxy d'entrée
PROXY_SORTIE_HOST = '127.0.0.1'  # Adresse du proxy de sortie
PROXY_SORTIE_PORT = 9090         # Port du proxy de sortie

def start_proxy_entree():
    # Création du socket serveur
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((HOST, PORT))
        server_socket.listen(5)
        print(f"[+] Proxy d'entrée en écoute sur {HOST}:{PORT}...")

        while True:
            client_conn, client_addr = server_socket.accept()
            print(f"[>] Connexion du navigateur depuis {client_addr}")

            with client_conn:
                # Lire la requête HTTP du navigateur
                request = client_conn.recv(4096)
                print(f"[>] Requête reçue du navigateur :\n{request.decode(errors='ignore')}")

                # Envoyer la requête au proxy de sortie
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sortie_socket:
                    sortie_socket.connect((PROXY_SORTIE_HOST, PROXY_SORTIE_PORT))
                    sortie_socket.sendall(request)

                    # Lire la réponse du proxy de sortie
                    response = b""
                    while True:
                        data = sortie_socket.recv(4096)
                        if not data:
                            break
                        response += data

                # Renvoyer la réponse au navigateur
                client_conn.sendall(response)
                print(f"[<] Réponse renvoyée au navigateur.")

if __name__ == "__main__":
    start_proxy_entree()
