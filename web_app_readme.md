# FTP Server Manager - Application Web

Application web pour gérer et tester plusieurs serveurs FTP.

## Installation

### Prérequis
- Python 3.7+
- pip

### Étapes

1. **Cloner le dépôt ou accéder au dossier**
   ```bash
   cd SyncFTP
   ```

2. **Installer les dépendances**
   ```bash
   pip install -r requirements.txt
   ```

3. **Lancer l'application**
   ```bash
   # Mode normal (logs visibles)
   python app.py
   
   # Mode silencieux (seulement les erreurs)
   python app.py --silent
   
   # Mode verbeux (tous les logs)
   python app.py --verbose
   
   # Sur un port spécifique
   python app.py --port 8080
   
   # Sur une interface spécifique
   python app.py --host 127.0.0.1 --port 8080
   ```

4. **Accéder à l'application**
   Ouvrez votre navigateur et allez sur :
   ```
   http://localhost:5000
   ```

## Fonctionnalités

### 📝 Enregistrer un serveur FTP
1. Remplissez le formulaire "Ajouter un serveur FTP"
   - **Nom du serveur** : Nom pour identifier votre configuration
   - **Hôte** : Adresse du serveur FTP (ex: `ftp.example.com` ou `192.168.1.100`)
   - **Port** : Port FTP (par défaut: 21)
   - **Utilisateur** : Nom d'utilisateur (par défaut: `anonymous`)
   - **Mot de passe** : Mot de passe FTP
   - **Utiliser SSL (FTPS)** : Cocher si votre serveur utilise FTPS
   - **Timeout** : Délai d'attente en secondes (par défaut: 30)
   - **Répertoire à tester** : Chemin du répertoire à analyser (optionnel)
2. Cliquez sur **💾 ENREGISTRER FTP**

### 🔍 Tester une connexion FTP
Il y a deux façons de tester :

**Méthode 1 : Depuis la carte du serveur**
- Trouvez la carte de votre serveur dans la section "Vos serveurs FTP"
- Cliquez sur le bouton **🔍 TESTER FTP**

**Méthode 2 : Depuis le modal**
- Cliquez sur un bouton "TESTER FTP" ou utilisez le modal de sélection
- Sélectionnez un serveur dans la liste
- Cliquez sur **TESTER FTP**

Les résultats s'affichent automatiquement dans la section "Résultats des tests" avec :
- ✅ Succès : Connexion réussie + nombre de fichiers dans le répertoire
- ❌ Échec : Message d'erreur détaillé

### 🗑️ Supprimer un serveur
- Trouvez la carte de votre serveur
- Cliquez sur **🗑️ Supprimer**
- Confirmez la suppression

### 📊 Résultats des tests
Tous les tests effectués sont affichés avec :
- Le nom du serveur testé
- Le statut (succès/échec)
- Le message de résultat
- Si un répertoire a été testé : le nombre de fichiers trouvés

## Modes de lancement

| Argument | Description |
|----------|-------------|
| `--silent` | Mode silencieux - Affiche seulement les erreurs |
| `--verbose` | Mode verbeux - Affiche tous les logs (DEBUG) |
| `--host` | Adresse IP pour le serveur web (défaut: 0.0.0.0) |
| `--port` | Port pour le serveur web (défaut: 5000) |

### Exemples

```bash
# Lancement standard
python app.py

# Lancement silencieux (pour la production)
python app.py --silent

# Lancement avec logs détaillés (pour le debug)
python app.py --verbose

# Lancement sur un port différent
python app.py --port 8080

# Lancement en local seulement
python app.py --host 127.0.0.1 --port 8000
```

## Stockage des données

Les configurations des serveurs FTP sont stockées dans le fichier `ftp_servers.json` (format JSON).

**Emplacement** : Dans le même dossier que `app.py`

**Exemple de structure** :
```json
[
  {
    "id": "uuid-unique",
    "name": "Mon Serveur Freebox",
    "host": "mafreebox.freebox.fr",
    "port": 21,
    "username": "mon_user",
    "password": "mon_mot_de_passe",
    "use_ssl": false,
    "timeout": 30,
    "test_directory": "/Freebox/Backup/photo_Icloud_Alex",
    "created_at": "2024-01-01T12:00:00"
  }
]
```

⚠️ **Important** : Le fichier `.env` (pour la version CLI) et `ftp_servers.json` ne sont pas inclus dans le dépôt Git grâce au `.gitignore`.

## Sécurité

- Les mots de passe sont stockés en clair dans `ftp_servers.json`
- Ne partagez pas ce fichier
- Assurez-vous que votre serveur web n'est accessible que localement ou protégé
- En production, utilisez HTTPS et des mécanismes d'authentification

## Technologie

- **Backend** : Flask (Python)
- **Frontend** : HTML5, CSS3, JavaScript (Vanilla)
- **Stockage** : JSON
- **FTP** : ftplib (Python standard library)

## Dépannage

### Flask n'est pas installé
```bash
pip install flask
```

### Port déjà utilisé
Changez le port avec `--port` :
```bash
python app.py --port 5001
```

### Problème de connexion FTP
Vérifiez :
- L'adresse du serveur est correcte
- Le port est ouvert
- Les identifiants sont valides
- Le pare-feu autorise les connexions sortantes
- Si SSL est utilisé, vérifiez que le serveur supporte FTPS

### Erreur de décodage
Certains serveurs FTP utilisent des encodages différents. L'application essaie automatiquement UTF-8 et Latin-1.

## API (pour utilisation avancée)

### GET /api/servers
Retourne la liste de tous les serveurs (sans les mots de passe complets).

**Réponse** :
```json
[
  {
    "id": "...",
    "name": "...",
    "host": "...",
    "port": 21,
    "username": "...",
    "password": "********",
    "use_ssl": false,
    "timeout": 30,
    "test_directory": "...",
    "created_at": "..."
  }
]
```

### POST /test_server
Teste la connexion à un serveur spécifique.

**Paramètres** :
```
server_id: UUID du serveur
```

**Réponse** :
```json
{
  "server_id": "...",
  "server_name": "...",
  "success": true/false,
  "message": "...",
  "file_count": 0,
  "test_directory": "...",
  "directory_success": true/false,
  "directory_message": "..."
}
```
