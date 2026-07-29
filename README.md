# SyncFTP

**Version 2.5.3**

**Application Web de Gestion et Synchronisation FTP**

SyncFTP est une application web légère qui permet de gérer plusieurs serveurs FTP et de configurer des tâches de synchronisation automatique entre des répertoires locaux et distants. L'application propose un système de synchronisation unidirectionnelle (miroir) avec gestion intelligente des erreurs, timeout dynamique pour les gros fichiers, et vérification automatique des fichiers corrompus.

---

## Fonctionnalités

### Gestion des Serveurs FTP
- Ajouter, modifier et supprimer des configurations de serveurs FTP
- Tester la connexion à chaque serveur
- Tester l'accès à des répertoires spécifiques
- Afficher le nombre de fichiers dans les répertoires FTP
- Support SSL/FTPS
- Configuration du timeout par serveur

### Synchronisation Automatique
- Créer des tâches de synchronisation entre un répertoire local et un répertoire FTP
- Configurer la fréquence de synchronisation (en secondes, minimum: 10 secondes)
- Exécution automatique en arrière-plan via des threads dédiés
- La première synchronisation démarre automatiquement à la création de la tâche
- Exécution manuelle immédiate des tâches
- Activation/Désactivation des tâches
- Statistiques d'exécution en temps réel
- Synchronisation unidirectionnelle (miroir)

### Gestion des Fichiers
- Suppression automatique des fichiers orphelins
- Vérification automatique des fichiers corrompus
- Patterns d'exclusion configurables
- Timeout dynamique pour les gros fichiers
- Gestion intelligente des erreurs avec reconnexion automatique

### Interface et Configuration
- Interface responsive adaptée aux mobiles
- Journalisation complète avec filtres par niveau
- Configuration de la rétention des logs
- Mode debug de performance activable
- Configuration de la taille maximale des logs (nettoyage automatique)

---

## Structure du Projet

```
SyncFTP/
├── app.py                 # Application Flask principale
├── ftp_tools.py           # Outils de connexion et gestion FTP
├── templates/
│   ├── base.html          # Template de base
│   ├── index.html         # Tableau de bord
│   ├── add.html           # Ajouter un serveur
│   ├── list.html          # Liste des serveurs
│   ├── tasks.html         # Gestion des tâches
│   ├── logs.html          # Affichage des logs
│   └── config.html        # Configuration
├── static/
│   ├── css/
│   │   ├── main.css       # Styles principaux (fusionné)
│   │   └── pages/         # Styles spécifiques par page
│   └── js/
│       └── main.js        # JavaScript principal
├── ftp_servers.json       # Configurations des serveurs
├── sync_tasks.json        # Configurations des tâches
├── config.json            # Paramètres de l'application
├── app.log                # Fichier de logs
├── start_server.vbs       # Script de démarrage Windows
└── stop_server.vbs        # Script d'arrêt Windows
```

---

## Installation

### Prérequis
- Python 3.7+
- pip

### Étapes

```bash
git clone https://github.com/SHARKYBLUSTER/SyncFTP.git
cd SyncFTP
python -m venv venv
```

**Sur Windows:**
```bash
venv\Scripts\activate
pip install flask
```

**Sur Linux/Mac:**
```bash
source venv/bin/activate
pip install flask
```

### Avec Gitbash (Windows)
```bash
git clone https://github.com/SHARKYBLUSTER/SyncFTP.git
cd SyncFTP
python -m venv venv
```

```bash
source venv/Scripts/activate
pip install flask
```

## Mise à jour

Pour mettre à jour l'application vers la dernière version :

```bash
git pull origin main
```

Cette commande télécharge et applique automatiquement les dernières modifications depuis le dépôt GitHub.

## Utilisation

### Démarrage standard
```bash
python app.py
```

Accessible à: http://localhost:5000

### Options de lancement
```bash
# Mode normal (logs visibles)
python app.py

# Mode silencieux (seulement les erreurs)
python app.py --silent

# Mode verbeux (tous les logs)
python app.py --verbose

# Port spécifique
python app.py --port 8080

# Adresse et port spécifiques
python app.py --host 127.0.0.1 --port 8080
```

### Scripts Windows
- `start_server.vbs` - Démarrer le serveur
- `stop_server.vbs` - Arrêter le serveur

---

## Pages

| Page | URL | Description |
|------|-----|-------------|
| Tableau de bord | / | Statistiques (nombre de serveurs et tâches) |
| Ajouter serveur | /add | Formulaire d'ajout de serveur |
| Liste serveurs | /list | Liste avec tests de connexion |
| Tâches | /tasks | Gestion des tâches de synchronisation |
| Logs | /logs | Logs en temps réel avec filtres |
| Configuration | /config | Paramètres de l'application |

---

## API REST

### Serveurs
- `GET /api/servers` - Liste de tous les serveurs
- `GET /api/servers/<id>` - Détails d'un serveur
- `POST /add_server` - Ajouter un serveur
- `POST /update_server/<id>` - Mettre à jour un serveur
- `POST /delete_server/<id>` - Supprimer un serveur
- `POST /test_server/<id>` - Tester la connexion

### Tâches
- `GET /api/tasks` - Liste de toutes les tâches
- `POST /add_task` - Créer une tâche
- `POST /update_task/<id>` - Mettre à jour une tâche
- `POST /delete_task/<id>` - Supprimer une tâche
- `POST /run_task/<id>` - Exécuter une tâche
- `POST /toggle_task/<id>` - Activer/Désactiver une tâche

### Logs
- `GET /api/logs` - Récupérer les logs (filtre ?type=)
- `DELETE /api/logs` - Effacer tous les logs
- `POST /api/cleanup_logs` - Nettoyer les logs anciens

### Configuration
- `GET /api/config` - Récupérer la configuration
- `POST /api/config` - Sauvegarder la configuration

---

## Configuration

### Fichiers
- `ftp_servers.json` - Serveurs FTP
- `sync_tasks.json` - Tâches de synchronisation
- `config.json` - Paramètres de l'application
- `app.log` - Logs

### Paramètres principaux (config.json)
```json
{
  "log_retention_days": 7,
  "log_refresh_interval": 3,
  "log_mode": "standard",
  "max_log_size_mb": 10,
  "auto_refresh": true,
  "corrupted_files_check_interval": 300,
  "exclude_patterns": "*.tmp,*.part,*.temp,*.~lk,*.lock,Thumbs.db,desktop.ini,.github*,.env",
  "debug_logging_enabled": false,
  "task_save_throttle": 10,
  "small_file_timeout": 10,
  "large_file_timeout": 60,
  "large_file_threshold_mb": 50,
  "connection_timeout": 30,
  "max_connections": 5,
  "retry_attempts": 3,
  "retry_delay": 5
}
```

### Niveaux de logging
- **Silent** : Erreurs seulement
- **Standard** : INFO et supérieurs
- **Verbose** : Tous les logs (DEBUG inclus)

---

## Sécurité

- Les mots de passe ne sont jamais affichés en clair dans l'interface
- Les mots de passe sont masqués dans l'API
- Stockage local (pas de base de données)
- Les fichiers de configuration (.json, .log) sont exclus du dépôt Git

---

## Technologie

- **Backend** : Flask (Python)
- **Frontend** : HTML5, CSS3, JavaScript (Vanilla)
- **FTP** : ftplib (Python standard library)
- **Stockage** : Fichiers JSON
- **Logging** : logging Python

---

## Dépannage

### Flask n'est pas installé
```bash
pip install flask
```

### Port déjà utilisé
```bash
python app.py --port 5001
```

### Problème de connexion FTP
Vérifiez:
- L'adresse du serveur est correcte
- Le port est ouvert
- Les identifiants sont valides
- Le pare-feu autorise les connexions sortantes
- Si SSL est utilisé, vérifiez que le serveur supporte FTPS

### Erreur de décodage
Certains serveurs FTP utilisent des encodages différents. L'application essaie automatiquement UTF-8 et Latin-1.

---

## Licence

Licence libre - Utilisation, modification et distribution autorisées.

---

## Historique des versions

- **2.5.3** - Ajout section mise à jour via git pull dans README
- **2.5.2** - Correction réactivation bouton arrêt serveur
- **2.5.1** - Ajout bouton arret serveur dans page configuration
- **2.5.0** - Affichage des fichiers échoués par tâche sur le tableau de bord, suppression du copyright, améliorations UI
- **2.0.0** - Mise à jour majeure de l'UI, correction des bugs, amélioration des fonctionnalités
- **1.0.0** - Version initiale
