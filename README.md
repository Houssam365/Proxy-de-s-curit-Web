# Proxy de Sécurité Web

Ce projet implémente un système de proxy sécurisé permettant d'anonymiser et de chiffrer le trafic web entre un client et l'internet public pour garantir la confidentialité des échanges.

Le projet a été entièrement réalisé en **Rust** pour des performances et une sécurité maximales, et conteneurisé avec **Docker** pour un déploiement simplifié.

## 🏗️ Architecture du Système

Le système repose sur deux composants principaux fonctionnant en tandem :

1.  **Entry Proxy (Proxy d'Entrée)**
    *   **Localisation** : `localhost:8081` (Côté Client)
    *   **Rôle** : Point d'entrée pour le client (navigateur/curl).
    *   **Fonction** : Intercepte les requêtes HTTP, génère une clé de session AES, chiffre la requête, et l'envoie via un tunnel sécurisé.

2.  **Exit Proxy (Proxy de Sortie)**
    *   **Localisation** : `exit_proxy:8080` (Interne au réseau Docker)
    *   **Rôle** : Passerelle vers Internet.
    *   **Fonction** : Reçoit le trafic chiffré, le déchiffre, effectue la requête réelle vers le site cible (ex: Google, Facebook), et rechiffre la réponse pour le retour.

## 🛠️ Choix Technologiques

### Langage : Rust 🦀
Nous avons choisi Rust pour :
*   **Sécurité Mémoire** : Prévient les failles critiques comme les dépassements de tampon.
*   **Performance** : Binaire natif ultra-rapide sans Garbage Collector.
*   **Concurrence** : Utilisation de `Tokio` et `Axum` pour gérer un grand nombre de connexions simultanées.

**Bibliothèques Clés :**
*   `axum` : Framework web asynchrone.
*   `rsa` & `aes-gcm` : Cryptographie robuste.
*   `serde` : Sérialisation haute performance.

### Déploiement : Docker 🐳
*   **Conteneurs Multi-stage** : Compilation dans une image dédiée, exécution dans une image `debian-slim` légère.
*   **Docker Compose** : Orchestration du réseau virtuel isolé entre les deux proxys.

## 🔒 Protocole Cryptographique

Le projet utilise un chiffrement hybride **RSA + AES** :

1.  **Initialisation (RSA-2048)** : Le `Exit Proxy` génère une paire de clés au démarrage. Le `Entry Proxy` télécharge la clé publique.
2.  **Par Requête (AES-256-GCM)** :
    *   Le `Entry Proxy` crée une clé AES unique pour chaque requête.
    *   Il chiffre cette clé AES avec la clé publique RSA du `Exit Proxy`.
    *   Il chiffre les données HTTP (URL, Headers, Body) avec la clé AES.
    *   Seul le `Exit Proxy` (possédant la clé privée RSA) peut récupérer la clé AES et lire les données.

## 🚀 Comment Lancer le Projet

### Pré-requis
*   Docker & Docker Compose

### Lancement
1.  Placez-vous à la racine du projet.
2.  Lancez la commande :
    ```bash
    docker compose up --build
    ```
3.  Attendez de voir les messages `Listening on...`.

## 🧪 Validation et Tests

### 1. Test Fonctionnel
Configurez votre navigateur ou utilisez `curl` pour passer par le proxy d'entrée :

```bash
curl -v -x http://localhost:8081 http://google.com
```

**Résultat attendu** : Vous recevez le code HTML de la page demandée. Cela prouve que le tunnel fonctionne de bout en bout.

### 2. Validation de la Sécurité (Wireshark) 🦈
Pour prouver que le trafic est bien chiffré, une analyse de paquets a été menée.

**Observation sur le réseau local (Port 8081)** :
*   Le trafic entre VOUS et le Proxy d'Entrée est en clair (`GET http://google.com`). C'est normal.

**Observation sur le réseau intermédiaire (Port 8080)** :
*   En écoutant l'interface Docker, le trafic est illisible.
*   Tout est encapsulé dans des objets JSON chiffrés :
    ```json
    {
      "encrypted_aes_key": "MIIEvw...", 
      "encrypted_data": "7df82a..."
    }
    ```
*   **Conclusion** : Le contenu de vos requêtes (URL, mots de passe, données) est totalement invisible pour tout espion situé sur le réseau entre le proxy d'entrée et de sortie.
