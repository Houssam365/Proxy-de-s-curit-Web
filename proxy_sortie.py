import socket

# Configuration
HOST = '127.0.0.1'  # Adresse locale
PORT = 9090         # Port d'écoute du proxy de sortie

def start_proxy_sortie():
    # Création du socket serveur
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((HOST, PORT))
        server_socket.listen(5)
        print(f"[+] Proxy de sortie en écoute sur {HOST}:{PORT}...")

        while True:
            client_conn, client_addr = server_socket.accept()
            print(f"[>] Connexion du proxy d'entrée depuis {client_addr}")

            with client_conn:
                # Lire la requête HTTP envoyée par le proxy d'entrée
                request = client_conn.recv(4096)
                print(f"[>] Requête reçue :\n{request.decode(errors='ignore')}")

                # Extraire l'hôte cible depuis la requête HTTP
                try:
                    first_line = request.decode().split('\n')[0]
                    url = first_line.split(' ')[1]
                    if url.startswith("http://"):
                        url = url[7:]
                    host = url.split('/')[0]
                    print(f"[i] Hôte cible : {host}")
                except Exception as e:
                    print(f"[!] Erreur d'analyse de la requête : {e}")
                    continue

                # Connexion au serveur web réel
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as web_socket:
                        web_socket.connect((host, 80))
                        web_socket.sendall(request)

                        # Lire la réponse du serveur web
                        response = b""
                        while True:
                            data = web_socket.recv(4096)
                            if not data:
                                break
                            response += data
                except Exception as e:
                    print(f"[!] Erreur lors de la connexion au serveur web : {e}")
                    response = b"HTTP/1.1 502 Bad Gateway\r\n\r\nErreur de connexion au serveur web."

                # Renvoyer la réponse au proxy d'entrée
                client_conn.sendall(response)
                print(f"[<] Réponse renvoyée au proxy d'entrée.")

if __name__ == "__main__":
    start_proxy_sortie()
