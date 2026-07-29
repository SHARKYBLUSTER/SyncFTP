# SyncFTP

**Version 1.0.0**

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

---

## Structure du Projet

SyncFTP/
├── app.py
├── ftp_tools.py
├── templates/
│   ├── index.html
│   ├── add.html
│   ├── list.html
│   ├── tasks.html
│   ├── logs.html
│   └── config.html
├── ftp_servers.json
├── sync_tasks.json
├── app.log
├── config.json
├── start_server.vbs
├── stop_server.vbs
└── README.md

---

## Installation

### Prérequis
- Python 3.7+
- pip

### Étapes

git clone https://github.com/SHARKYBLUSTER/SyncFTP.git
cd SyncFTP
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scriptsctivate  # Windows
pip install flask

---

## Utilisation

python app.py              # Mode normal
python app.py --silent     # Mode silencieux
python app.py --verbose    # Mode verbeux
python app.py --port 8080  # Port spécifique

Accessible à: http://localhost:5000

### Scripts Windows
start_server.vbs  # Démarrer
stop_server.vbs   # Arrêter

---

## Pages

| Page | URL | Description |
|------|-----|-------------|
| Tableau de bord | / | Statistiques |
| Ajouter serveur | /add | Formulaire serveur |
| Liste serveurs | /list | Liste avec tests |
| Tâches | /tasks | Gestion synchronisation |
| Logs | /logs | Logs en temps réel |
| Configuration | /config | Paramètres |

---

## API REST

### Serveurs
GET /api/servers - Liste
GET /api/servers/<id> - Détails

### Tâches
GET /api/tasks - Liste
POST /add_task - Créer
POST /update_task/<id> - Mettre à jour
POST /delete_task/<id> - Supprimer
POST /run_task/<id> - Exécuter
POST /toggle_task/<id> - Activer/Désactiver

### Logs
GET /api/logs - Récupérer (filtre ?type=)
DELETE /api/logs - Effacer
POST /api/cleanup_logs - Nettoyer

### Configuration
GET /api/config - Récupérer
POST /api/config - Sauvegarder

---

## Configuration

Fichiers:
- ftp_servers.json - Serveurs FTP
- sync_tasks.json - Tâches de synchronisation
- config.json - Paramètres
- app.log - Logs

Paramètres config.json:
- log_retention_days: 7
- log_refresh_interval: 3
- log_level: INFO
- auto_refresh: true
- corrupted_files_check_interval: 300
- exclude_patterns: *.tmp,*.part,*.temp,...
- debug_logging_enabled: false
- task_save_throttle: 10
- small_file_timeout: 10
- large_file_timeout: 60
- large_file_threshold_mb: 50

---

## Sécurité

- Mots de passe jamais affichés
- Mots de passe masqués dans l'API
- Stockage local (pas de base de données)

---

## Technologie

- Backend: Flask (Python)
- Frontend: HTML5, CSS3, JavaScript
- FTP: ftplib Python
- Stockage: Fichiers JSON
- Logging: logging Python

---

## Licence

Licence libre - Utilisation, modification et distribution autorisées.
