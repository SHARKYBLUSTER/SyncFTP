# SyncFTP

**Application Web de Gestion et Synchronisation FTP**

SyncFTP est une application web légère qui permet de gérer plusieurs serveurs FTP et de configurer des tâches de synchronisation automatique entre des répertoires locaux et distants.

---

## 📋 Fonctionnalités

### Gestion des Serveurs FTP
- ✅ Ajouter, modifier et supprimer des configurations de serveurs FTP
- ✅ Tester la connexion à chaque serveur
- ✅ Tester l'accès à des répertoires spécifiques
- ✅ Afficher le nombre de fichiers dans les répertoires FTP

### Synchronisation Automatique
- ✅ Créer des tâches de synchronisation entre un répertoire local et un répertoire FTP
- ✅ Configurer la fréquence de synchronisation (en secondes)
- ✅ Exécution automatique en arrière-plan via des threads dédiés
- ✅ **La première synchronisation démarre automatiquement à la création de la tâche**
- ✅ Exécution manuelle immédiate des tâches
- ✅ Activation/Désactivation des tâches
- ✅ Statistiques d'exécution (fichiers uploadés, erreurs, etc.)

### Interface Utilisateur
- ✅ Tableau de bord avec statistiques (nombre de serveurs et tâches)
- ✅ Interface responsive adaptée aux mobiles
- ✅ Navigation intuitive entre toutes les pages

### Logging et Configuration
- ✅ Journalisation complète des activités (connexions, synchronisations, erreurs)
- ✅ Page de logs en temps réel avec filtres par niveau (INFO, WARNING, ERROR, DEBUG)
- ✅ Configuration de la rétention des logs
- ✅ Configuration du niveau de logging et de l'intervalle de rafraîchissement

---

## 🏗️ Structure du Projet

```
SyncFTP/
├── app.py                  # Application Flask principale
├── ftp_tools.py            # Module de gestion des connexions FTP
├── templates/
│   ├── index.html          # Tableau de bord
│   ├── add.html            # Ajout d'un serveur FTP
│   ├── list.html           # Liste des serveurs FTP
│   ├── tasks.html          # Gestion des tâches de synchronisation
│   ├── logs.html           # Affichage des logs
│   └── config.html         # Configuration de l'application
├── ftp_servers.json        # Stockage des configurations serveurs (généré)
├── sync_tasks.json         # Stockage des tâches de synchronisation (généré)
├── app.log                 # Fichier de logs (généré)
├── config.json             # Configuration de l'application (généré)
└── README.md               # Documentation
```

---

## 🚀 Installation

### Prérequis
- Python 3.7+
- pip

### Installation des dépendances

```bash
# Cloner le dépôt
git clone https://github.com/SHARKYBLUSTER/SyncFTP.git
cd SyncFTP

# Créer un environnement virtuel (recommandé)
python -m venv venv
source venv/bin/activate  # Sur Linux/Mac
# ou
venv\Scripts\activate  # Sur Windows

# Installer les dépendances
pip install flask
```

---

## 📡 Utilisation

### Démarrer l'application

```bash
# Mode normal (logs visibles dans le terminal)
python app.py

# Mode silencieux (seulement les erreurs)
python app.py --silent

# Mode verbeux (tous les logs)
python app.py --verbose

# Démarrer sur un port spécifique
python app.py --port 8080
```

L'application sera accessible à l'adresse : `http://localhost:5000`

### Pages disponibles

| Page | URL | Description |
|------|-----|-------------|
| Tableau de bord | `/` | Vue d'ensemble avec statistiques |
| Ajouter serveur | `/add` | Formulaire pour ajouter un serveur FTP |
| Liste serveurs | `/list` | Liste de tous les serveurs configurés avec test de connexion |
| **Tâches de sync** | `/tasks` | **Gestion des tâches de synchronisation** |
| Logs | `/logs` | Affichage des logs en temps réel avec filtres |
| Configuration | `/config` | Paramètres de l'application |

---

## 🔄 Configuration des Tâches de Synchronisation

### Créer une nouvelle tâche

1. Allez sur la page **TACHES DE SYNC** (`/tasks`)
2. Remplissez le formulaire :
   - **Nom de la tâche** : Un nom descriptif
   - **Serveur FTP** : Sélectionnez un serveur déjà configuré
   - **Répertoire source (local)** : Chemin absolu du répertoire local (ex: `C:\Backup\Photos`)
   - **Répertoire cible (FTP)** : Chemin du répertoire sur le serveur FTP (ex: `/Backup/Photos`)
   - **Fréquence (secondes)** : Intervalle entre chaque synchronisation (minimum: 10 secondes)
   - **Activé** : Oui pour démarrer la tâche immédiatement, Non pour la créer en pause
3. Cliquez sur **AJOUTER TÂCHE**

### Gestion des tâches

- **▶️ EXECUTER** : Lance la synchronisation immédiatement
- **⏸️ PAUSE / ▶️ REPRENDRE** : Active ou désactive la tâche
- **✏️ MODIFIER** : Modifie les paramètres de la tâche
- **🗑️ SUPPRIMER** : Supprime définitivement la tâche

### Comportement

- **À la création** : La première synchronisation démarre automatiquement
- **En arrière-plan** : Les tâches activées s'exécutent selon leur fréquence configurée
- **Logs** : Toutes les opérations sont journalisées dans `app.log` et visibles dans l'interface

---

## 🔧 Configuration FTP

### Ajouter un serveur FTP

1. Allez sur la page **AJOUTER SERVEUR FTP** (`/add`)
2. Remplissez les informations :
   - Nom du serveur
   - Hôte (ex: `ftp.monserveur.com`)
   - Port (par défaut: 21)
   - Utilisateur
   - Mot de passe
   - Utiliser SSL (FTPS) : Oui/Non
   - Timeout (secondes)
   - Répertoire à tester (optionnel)
3. Cliquez sur **ENREGISTRER FTP**

### Tester un serveur

1. Allez sur la page **LISTE DES SERVEURS** (`/list`)
2. Cliquez sur **🔍 TESTER** pour tester la connexion
3. Les résultats s'affichent avec le nombre de fichiers dans le répertoire testé

---

## 📊 API REST

### Serveurs FTP

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/api/servers` | GET | Liste de tous les serveurs (mots de passe masqués) |

### Tâches de Synchronisation

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/api/tasks` | GET | Liste de toutes les tâches |
| `/add_task` | POST | Créer une nouvelle tâche |
| `/update_task/<task_id>` | POST | Mettre à jour une tâche |
| `/delete_task/<task_id>` | POST | Supprimer une tâche |
| `/run_task/<task_id>` | POST | Exécuter une tâche immédiatement |
| `/toggle_task/<task_id>` | POST | Activer/Désactiver une tâche |

### Logs

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/api/logs` | GET | Récupérer les logs (avec filtre optionnel `?type=INFO|ERROR|WARNING|DEBUG`) |
| `/api/logs` | DELETE | Effacer tous les logs |
| `/api/cleanup_logs` | POST | Nettoyer les logs anciens |

### Configuration

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/api/config` | GET | Récupérer la configuration |
| `/api/config` | POST | Sauvegarder la configuration |

---

## 📝 Configuration

### Fichiers de données

- **`ftp_servers.json`** : Contient la liste des serveurs FTP configurés
- **`sync_tasks.json`** : Contient la liste des tâches de synchronisation
- **`config.json`** : Contient les paramètres de l'application
- **`app.log`** : Fichier de logs de l'application

### Paramètres de configuration (config.json)

```json
{
  "log_retention_days": 7,
  "log_refresh_interval": 3,
  "log_level": "INFO",
  "auto_refresh": true
}
```

---

## 🎨 Interface Utilisateur

### Menu de Navigation

Le menu est présent sur toutes les pages et permet d'accéder rapidement à :
- 🏠 TABLEAU DE BORD
- ➕ AJOUTER SERVEUR FTP
- 📋 LISTE DES SERVEURS
- 🔄 **TACHES DE SYNC**
- 📜 LOGS
- ⚙️ CONFIGURATION

### Design

- Design moderne avec dégradés et ombres
- Interface responsive (adaptée mobile/tablette)
- Cartes interactives avec animations
- Feedback visuel pour toutes les actions

---

## 🔒 Sécurité

- Les mots de passe ne sont **jamais** affichés dans l'interface
- Les mots de passe sont masqués dans les réponses API
- Stockage local des configurations (pas de base de données externe)

---

## 🛠️ Technologie

- **Backend** : Flask (Python)
- **Frontend** : HTML5, CSS3, JavaScript (Vanilla)
- **Connexion FTP** : Module `ftplib` standard Python
- **Stockage** : Fichiers JSON
- **Logging** : Module `logging` Python

---

## 📞 Support

Pour toute question ou problème, consultez les logs dans `app.log` ou ouvrez une issue sur GitHub.

---

## 📄 Licence

Ce projet est sous licence libre. Vous êtes autorisé à l'utiliser, le modifier et le distribuer selon vos besoins.

---

*Développé avec ❤️ pour simplifier la gestion FTP*
