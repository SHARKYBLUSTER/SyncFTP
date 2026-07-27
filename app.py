#!/usr/bin/env python3
"""
FTP Server Manager - Application Web
=====================================

Application web pour gérer et tester plusieurs serveurs FTP.
Utilise Flask pour le backend et fournit une interface simple.

Utilisation:
    python app.py              # Mode normal (logs visibles)
    python app.py --silent     # Mode silencieux (seulement les erreurs)
    python app.py --verbose    # Mode verbeux (tous les logs)
"""

import os
import json
import argparse
import logging
import threading
import time
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for
from ftp_tools import FTPConfig, FTPConnector

# Configuration
APP_NAME = "FTP Server Manager"
DATA_FILE = "ftp_servers.json"
TASKS_FILE = "sync_tasks.json"
LOG_FILE = "app.log"
CONFIG_FILE = "config.json"
LOG_FORMAT = "[%(asctime)s] %(levelname)s: %(message)s"

# Initialisation de l'app Flask
app = Flask(__name__)

# Références globales pour les handlers de logging
file_handler = None
stream_handler = None

def setup_logging(verbose=False, silent=False):
    """Configure le niveau de logging"""
    global file_handler, stream_handler
    
    log_level = logging.ERROR if silent else (logging.DEBUG if verbose else logging.INFO)
    
    # Créer les handlers
    file_handler = logging.FileHandler(LOG_FILE, mode='a', encoding='utf-8')
    stream_handler = logging.StreamHandler()
    
    # Configurer le logging
    logging.basicConfig(
        level=log_level,
        format=LOG_FORMAT,
        handlers=[file_handler, stream_handler]
    )
    app.logger.setLevel(log_level)


def get_logs():
    """Récupère le contenu du fichier de logs (du plus récent au plus ancien)"""
    if not os.path.exists(LOG_FILE):
        return "Aucun log disponible"
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        # Inverser l'ordre pour afficher du plus récent au plus ancien
        return ''.join(reversed(lines))
    except Exception as e:
        return f"Erreur lors de la lecture des logs: {e}"


def load_config():
    """Charge la configuration depuis le fichier JSON"""
    default_config = {
        'log_retention_days': 7,
        'log_refresh_interval': 3,
        'log_level': 'INFO',
        'auto_refresh': True,
        'corrupted_files_check_interval': 300,  # 5 minutes en secondes
        'exclude_patterns': '*.tmp,*.part,*.temp,*.~lk,*.lock,Thumbs.db,desktop.ini'  # Patterns à exclure
    }
    if not os.path.exists(CONFIG_FILE):
        save_config(default_config)
        return default_config
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        # Ajouter les valeurs par défaut si elles n'existent pas
        if 'corrupted_files_check_interval' not in config:
            config['corrupted_files_check_interval'] = 300
            save_config(config)
        if 'exclude_patterns' not in config:
            config['exclude_patterns'] = '*.tmp,*.part,*.temp,*.~lk,*.lock,Thumbs.db,desktop.ini'
            save_config(config)
        return config
    except Exception as e:
        app.logger.error(f"Erreur lors du chargement de la config: {e}")
        return default_config


def save_config(config):
    """Sauvegarde la configuration dans le fichier JSON"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        app.logger.info("Configuration sauvegardée")
    except Exception as e:
        app.logger.error(f"Erreur lors de la sauvegarde de la config: {e}")


def cleanup_old_logs():
    """Nettoie les logs anciens selon la période de rétention"""
    config = load_config()
    retention_days = config.get('log_retention_days', 7)
    
    if not os.path.exists(LOG_FILE):
        return
    
    try:
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        new_lines = []
        for line in lines:
            try:
                # Extraire la date du log [2024-01-15 10:30:45]
                date_str = line.split(']')[0].strip('[')
                log_date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                if log_date >= cutoff_date:
                    new_lines.append(line)
            except:
                new_lines.append(line)
        
        with open(LOG_FILE, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        
        app.logger.info(f"Nettoyage des logs: conservés {len(new_lines)} lignes sur {len(lines)}")
    except Exception as e:
        app.logger.error(f"Erreur lors du nettoyage des logs: {e}")


def filter_logs(logs, log_type=None):
    """Filtre les logs par type"""
    if not log_type or log_type == 'ALL':
        return logs
    
    filtered_lines = []
    for line in logs.split('\n'):
        # Exclure les logs des requêtes API 200 du filtre INFO
        if log_type == 'INFO' and ('" 200 ' in line or '" 200-' in line):
            continue
        if f'] {log_type}:' in line:
            filtered_lines.append(line)
    
    return '\n'.join(filtered_lines)


def load_servers():
    """Charge la liste des serveurs FTP depuis le fichier JSON"""
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        app.logger.error(f"Erreur lors du chargement des serveurs: {e}")
        return []


def save_servers(servers):
    """Sauvegarde la liste des serveurs FTP dans le fichier JSON"""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(servers, f, indent=2, ensure_ascii=False)
        app.logger.info(f"Serveurs sauvegardés ({len(servers)} configurations)")
    except Exception as e:
        app.logger.error(f"Erreur lors de la sauvegarde des serveurs: {e}")


def test_ftp_connection(server):
    """
    Teste la connexion FTP avec une configuration
    Retourne un dictionnaire avec le résultat
    """
    config = FTPConfig(
        host=server['host'],
        port=int(server.get('port', 21)),
        username=server.get('username', 'anonymous'),
        password=server.get('password', ''),
        use_ssl=server.get('use_ssl', False),
        timeout=int(server.get('timeout', 30))
    )
    
    connector = FTPConnector(config)
    result = {
        'server_id': server['id'],
        'server_name': server['name'],
        'success': False,
        'message': '',
        'file_count': 0,
        'test_directory': server.get('test_directory', ''),
        'directory_success': False,
        'directory_message': ''
    }
    
    try:
        # Test de connexion
        app.logger.info(f"Test de connexion FTP: {server['name']} ({server['host']})")
        connection_success = connector.connect()
        
        if connection_success:
            app.logger.info(f"Connexion réussie pour {server['name']}")
            try:
                pwd = connector._ftp.pwd()
                app.logger.info(f"Répertoire courant: {pwd}")
                result['success'] = True
                result['message'] = f"Connexion réussie ! Répertoire: {pwd}"
                
                # Test du répertoire si spécifié
                test_dir = server.get('test_directory', '')
                if test_dir:
                    app.logger.info(f"Test du répertoire: {test_dir}")
                    dir_success, dir_message, file_count = connector.list_directory(test_dir)
                    result['directory_success'] = dir_success
                    result['directory_message'] = dir_message
                    result['file_count'] = file_count
                    
                    if dir_success:
                        app.logger.info(f"Répertoire {test_dir}: {file_count} fichiers")
                    else:
                        app.logger.error(f"Échec du test du répertoire {test_dir}: {dir_message}")
                
            except Exception as e:
                app.logger.error(f"Erreur lors de la vérification de la connexion pour {server['name']}: {e}")
                result['message'] = f"Connexion réussie mais erreur: {e}"
            finally:
                connector.disconnect()
        else:
            result['message'] = "Échec de la connexion"
            app.logger.error(f"Échec de connexion pour {server['name']}")
            
    except Exception as e:
        result['message'] = f"Erreur: {e}"
        app.logger.error(f"Erreur FTP pour {server['name']}: {e}")
    
    return result


# ==================== Gestion des tâches de synchronisation ====================

sync_lock = threading.Lock()
sync_tasks = []
sync_threads = {}
sync_stop_event = threading.Event()
tasks_file_lock = threading.Lock()  # Verrou pour protéger l'accès au fichier tasks.json

# Variables pour la vérification des fichiers corrompus
corrupted_check_lock = threading.Lock()
corrupted_check_thread = None
corrupted_check_stop_event = threading.Event()


def load_tasks():
    """Charge la liste des tâches de synchronisation depuis le fichier JSON"""
    with tasks_file_lock:
        if not os.path.exists(TASKS_FILE):
            return []
        try:
            with open(TASKS_FILE, 'r', encoding='utf-8') as f:
                tasks = json.load(f)
            
            # S'assurer que toutes les tâches ont un champ status
            for task in tasks:
                if 'status' not in task:
                    task['status'] = 'idle'
            
            return tasks
        except Exception as e:
            app.logger.error(f"Erreur lors du chargement des tâches: {e}")
            return []


def save_tasks(tasks):
    """Sauvegarde la liste des tâches de synchronisation dans le fichier JSON"""
    with tasks_file_lock:
        try:
            with open(TASKS_FILE, 'w', encoding='utf-8') as f:
                json.dump(tasks, f, indent=2, ensure_ascii=False)
            app.logger.info(f"Tâches sauvegardées ({len(tasks)} tâches)")
        except Exception as e:
            app.logger.error(f"Erreur lors de la sauvegarde des tâches: {e}")


def get_server_by_id(server_id):
    """Récupère un serveur par son ID"""
    servers = load_servers()
    return next((s for s in servers if s['id'] == server_id), None)


def execute_sync_task(task):
    """
    Exécute une tâche de synchronisation unique
    
    Args:
        task: Dictionnaire contenant les informations de la tâche
    
    Returns:
        dict: Résultat de la synchronisation
    """
    result = {
        'task_id': task['id'],
        'success': False,
        'message': '',
        'stats': {},
        'timestamp': datetime.now().isoformat()
    }
    
    # Acquérir le verrou global pour éviter les conflits
    with sync_lock:
        try:
            # Marquer la tâche comme en cours
            tasks = load_tasks()
            task_index = None
            for i, t in enumerate(tasks):
                if t['id'] == task['id']:
                    t['status'] = 'running'
                    t['running_since'] = datetime.now().isoformat()
                    task_index = i
                    break
            
            if task_index is not None:
                save_tasks(tasks)
                app.logger.info(f"Tâche {task['id']} démarrée: {task['name']}")
            
            # Récupérer le serveur
            server = get_server_by_id(task['server_id'])
            if not server:
                result['message'] = f"Serveur non trouvé: {task['server_id']}"
                app.logger.error(result['message'])
                # Réinitialiser le statut
                if task_index is not None:
                    tasks[task_index]['status'] = 'failed'
                    save_tasks(tasks)
                return result
            
            # Créer la configuration FTP
            config = FTPConfig(
                host=server['host'],
                port=int(server.get('port', 21)),
                username=server.get('username', 'anonymous'),
                password=server.get('password', ''),
                use_ssl=server.get('use_ssl', False),
                timeout=int(server.get('timeout', 30))
            )
            
            connector = FTPConnector(config)
            
            # Créer un callback de progression pour mettre à jour les stats en temps réel
            def progress_callback(current_stats):
                # Mettre à jour les stats de la tâche en cours
                nonlocal tasks, task_index
                if task_index is not None:
                    tasks = load_tasks()
                    for t in tasks:
                        if t['id'] == task['id']:
                            t['last_result'] = {
                                'success': False,  # Pas encore terminé
                                'message': 'En cours',
                                'stats': current_stats,
                                'timestamp': datetime.now().isoformat()
                            }
                            t['status'] = 'running'
                            break
                    save_tasks(tasks)
            
            # Exécuter la synchronisation
            app.logger.info(f"Exécution de la tâche {task['id']}: {task['name']}")
            app.logger.info(f"Source: {task['source_directory']} -> Cible: {task['target_directory']}")
            
            # Charger la configuration pour obtenir les patterns d'exclusion
            config = load_config()
            exclude_patterns = config.get('exclude_patterns', '')
            
            success, message, stats = connector.sync_directory_to_ftp(
                task['source_directory'],
                task['target_directory'],
                logger=app.logger,
                exclude_patterns=exclude_patterns,
                progress_callback=progress_callback
            )
            
            result['success'] = success
            result['message'] = message
            result['stats'] = stats
            
            if success:
                app.logger.info(f"Tâche {task['id']} terminée avec succès: {stats.get('uploaded', 0)} fichiers synchronisés")
            else:
                app.logger.error(f"Échec de la tâche {task['id']}: {message}")
            
            # Mettre à jour le dernier statut de la tâche
            tasks = load_tasks()
            for t in tasks:
                if t['id'] == task['id']:
                    t['status'] = 'completed' if success else 'failed'
                    t['last_run'] = datetime.now().isoformat()
                    t['last_result'] = result
                    # Nettoyer le champ running_since
                    t.pop('running_since', None)
                    break
            save_tasks(tasks)
            
        except Exception as e:
            result['message'] = f"Erreur: {e}"
            app.logger.error(f"Erreur lors de l'exécution de la tâche {task['id']}: {e}")
            
            # Réinitialiser le statut en cas d'erreur
            try:
                tasks = load_tasks()
                for t in tasks:
                    if t['id'] == task['id']:
                        t['status'] = 'failed'
                        t['last_run'] = datetime.now().isoformat()
                        t.pop('running_since', None)
                        break
                save_tasks(tasks)
            except Exception:
                pass
    
    return result


def sync_worker(task):
    """
    Worker thread qui exécute une tâche de synchronisation périodiquement
    
    Args:
        task: Dictionnaire contenant les informations de la tâche
    """
    task_id = task['id']
    interval = task.get('sync_interval', 60)  # en secondes
    
    app.logger.info(f"Démarrage du worker pour la tâche {task_id} (intervalle: {interval}s)")
    
    # Exécuter immédiatement la première synchronisation
    if not sync_stop_event.is_set():
        execute_sync_task(task)
    
    # Boucle principale
    while not sync_stop_event.is_set():
        try:
            # Attendre l'intervalle
            time.sleep(interval)
            
            # Vérifier si la tâche existe toujours
            tasks = load_tasks()
            task_exists = any(t['id'] == task_id for t in tasks)
            if not task_exists:
                break
            
            # Exécuter la synchronisation
            if not sync_stop_event.is_set():
                execute_sync_task(task)
                
        except Exception as e:
            app.logger.error(f"Erreur dans le worker de la tâche {task_id}: {e}")
            break
    
    app.logger.info(f"Worker pour la tâche {task_id} arrêté")


def start_sync_threads():
    """Démarre les threads de synchronisation pour toutes les tâches actives"""
    global sync_threads
    
    sync_stop_event.clear()
    
    # Arrêter les threads existants
    for thread in sync_threads.values():
        if thread.is_alive():
            thread.join(timeout=1)
    sync_threads = {}
    
    # Charger les tâches
    tasks = load_tasks()
    
    # Démarrer un thread pour chaque tâche active
    for task in tasks:
        if task.get('enabled', True):
            thread = threading.Thread(
                target=sync_worker,
                args=(task,),
                daemon=True,
                name=f"SyncWorker-{task['id']}"
            )
            thread.start()
            sync_threads[task['id']] = thread
            app.logger.info(f"Thread de synchronisation démarré pour: {task['name']}")


def stop_sync_threads():
    """Arrête tous les threads de synchronisation"""
    global sync_threads
    sync_stop_event.set()
    
    for thread in sync_threads.values():
        if thread.is_alive():
            thread.join(timeout=2)
    sync_threads = {}
    app.logger.info("Tous les threads de synchronisation arrêtés")


def check_corrupted_files_worker():
    """
    Worker thread qui vérifie et supprime périodiquement les fichiers corrompus.
    Ne s'exécute que quand toutes les tâches de synchronisation sont terminées.
    """
    global corrupted_check_thread
    
    app.logger.info("Démarrage du worker de vérification des fichiers corrompus")
    
    while not corrupted_check_stop_event.is_set():
        try:
            # Charger la configuration
            config = load_config()
            interval = config.get('corrupted_files_check_interval', 300)
            
            # Attendre l'intervalle
            time.sleep(interval)
            
            # Vérifier si on doit arrêter
            if corrupted_check_stop_event.is_set():
                break
            
            # Charger les tâches et serveurs
            tasks = load_tasks()
            servers = load_servers()
            
            # Exécuter la vérification (la fonction crée ses propres connecteurs)
            from ftp_tools import FTPConnector
            result = FTPConnector(None).check_and_delete_corrupted_files(tasks, servers, logger=app.logger)
            
            if result.get('corrupted_found', 0) > 0:
                app.logger.info(f"Vérification des fichiers corrompus: {result['message']}")
            
        except Exception as e:
            app.logger.error(f"Erreur dans le worker de vérification des fichiers corrompus: {e}")
            break
    
    app.logger.info("Worker de vérification des fichiers corrompus arrêté")


def start_corrupted_check_thread():
    """Démarre le thread de vérification des fichiers corrompus"""
    global corrupted_check_thread
    
    corrupted_check_stop_event.clear()
    
    # Arrêter le thread existant s'il y en a un
    if corrupted_check_thread and corrupted_check_thread.is_alive():
        corrupted_check_stop_event.set()
        corrupted_check_thread.join(timeout=2)
    
    # Démarrer un nouveau thread
    corrupted_check_thread = threading.Thread(
        target=check_corrupted_files_worker,
        daemon=True,
        name="CorruptedFilesCheckWorker"
    )
    corrupted_check_thread.start()
    app.logger.info("Thread de vérification des fichiers corrompus démarré")


def stop_corrupted_check_thread():
    """Arrête le thread de vérification des fichiers corrompus"""
    global corrupted_check_thread
    corrupted_check_stop_event.set()
    
    if corrupted_check_thread and corrupted_check_thread.is_alive():
        corrupted_check_thread.join(timeout=2)
    corrupted_check_thread = None
    app.logger.info("Thread de vérification des fichiers corrompus arrêté")


# Routes
@app.route('/')
def index():
    """Page d'accueil - tableau de bord"""
    servers = load_servers()
    tasks = load_tasks()
    return render_template('index.html', server_count=len(servers), task_count=len(tasks), app_name=APP_NAME)


@app.route('/add')
def add_page():
    """Page d'ajout d'un serveur FTP"""
    return render_template('add.html', app_name=APP_NAME)


@app.route('/list')
def list_servers():
    """Page de liste des serveurs"""
    servers = load_servers()
    return render_template('list.html', servers=servers, app_name=APP_NAME)


@app.route('/logs')
def logs_page():
    """Page d'affichage des logs"""
    return render_template('logs.html', app_name=APP_NAME)


@app.route('/config')
def config_page():
    """Page de configuration"""
    config = load_config()
    return render_template('config.html', config=config, app_name=APP_NAME)


def recreate_file_handler():
    """Recrée le FileHandler pour le fichier de logs"""
    global file_handler
    if file_handler:
        # Flusher et fermer l'ancien handler
        file_handler.flush()
        file_handler.close()
        # Retirer de la liste des handlers
        logging.getLogger().removeHandler(file_handler)
    # Créer un nouveau handler avec le même format
    file_handler = logging.FileHandler(LOG_FILE, mode='a', encoding='utf-8')
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logging.getLogger().addHandler(file_handler)


@app.route('/api/logs', methods=['GET', 'DELETE'])
def api_logs():
    """API: Retourne ou efface le contenu des logs"""
    log_type = request.args.get('type', 'ALL')
    
    if request.method == 'DELETE':
        try:
            if os.path.exists(LOG_FILE):
                # Fermer le handler avant de supprimer
                if file_handler:
                    file_handler.flush()
                    file_handler.close()
                    logging.getLogger().removeHandler(file_handler)
                
                os.remove(LOG_FILE)
                
                # Recréer le handler
                recreate_file_handler()
                
                app.logger.warning("Fichier de logs effacé")
                return jsonify({'success': True, 'message': 'Logs effacés avec succès'})
            else:
                return jsonify({'success': True, 'message': 'Aucun fichier de logs à effacer'})
        except Exception as e:
            # Recréer le handler en cas d'erreur
            recreate_file_handler()
            return jsonify({'success': False, 'message': str(e)}), 500
    else:
        logs = get_logs()
        filtered_logs = filter_logs(logs, log_type)
        return jsonify({'logs': filtered_logs})


@app.route('/api/config', methods=['GET', 'POST'])
def api_config():
    """API: Récupère ou sauvegarde la configuration"""
    if request.method == 'POST':
        config = request.json
        save_config(config)
        
        # Appliquer le nouveau niveau de log
        log_level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR
        }
        new_level = log_level_map.get(config.get('log_level', 'INFO'), logging.INFO)
        app.logger.setLevel(new_level)
        
        # Nettoyer les logs si la rétention a changé
        cleanup_old_logs()
        
        return jsonify({'success': True, 'message': 'Configuration sauvegardée'})
    else:
        config = load_config()
        return jsonify(config)


@app.route('/api/cleanup_logs', methods=['POST'])
def api_cleanup_logs():
    """API: Nettoie les logs anciens"""
    cleanup_old_logs()
    return jsonify({'success': True, 'message': 'Logs nettoyés'})


@app.route('/add_server', methods=['POST'])
def add_server():
    """Ajoute un nouveau serveur FTP"""
    data = request.form.to_dict()
    
    # Générer un ID unique
    import uuid
    server_id = str(uuid.uuid4())
    
    server = {
        'id': server_id,
        'name': data.get('name', 'Nouveau Serveur'),
        'host': data.get('host', ''),
        'port': data.get('port', '21'),
        'username': data.get('username', 'anonymous'),
        'password': data.get('password', ''),
        'use_ssl': data.get('use_ssl') == 'true',
        'timeout': data.get('timeout', '30'),
        'test_directory': data.get('test_directory', ''),
        'created_at': datetime.now().isoformat()
    }
    
    servers = load_servers()
    servers.append(server)
    save_servers(servers)
    
    app.logger.info(f"Serveur FTP ajouté: {server['name']} ({server['host']})")
    
    return redirect(url_for('index'))


@app.route('/delete_server/<server_id>', methods=['POST'])
def delete_server(server_id):
    """Supprime un serveur FTP"""
    servers = load_servers()
    servers = [s for s in servers if s['id'] != server_id]
    save_servers(servers)
    
    app.logger.info(f"Serveur FTP supprimé: {server_id}")
    
    return redirect(url_for('index'))


@app.route('/test_server', methods=['POST'])
def test_server():
    """Teste la connexion à un serveur FTP"""
    server_id = request.form.get('server_id')
    
    servers = load_servers()
    server = next((s for s in servers if s['id'] == server_id), None)
    
    if not server:
        return jsonify({'error': 'Serveur non trouvé'}), 404
    
    result = test_ftp_connection(server)
    
    return jsonify(result)


@app.route('/api/servers')
def api_servers():
    """API: Retourne la liste des serveurs"""
    servers = load_servers()
    # Masquer les mots de passe pour la sécurité
    for server in servers:
        server['password'] = '********' if server.get('password') else ''
    return jsonify(servers)


# Routes pour les tâches de synchronisation
@app.route('/tasks')
def tasks_page():
    """Page des tâches de synchronisation"""
    tasks = load_tasks()
    servers = load_servers()
    # Masquer les mots de passe
    for server in servers:
        server['password'] = '********' if server.get('password') else ''
    return render_template('tasks.html', tasks=tasks, servers=servers, app_name=APP_NAME)


@app.route('/api/tasks', methods=['GET'])
def api_tasks():
    """API: Retourne la liste des tâches"""
    tasks = load_tasks()
    return jsonify(tasks)


@app.route('/add_task', methods=['POST'])
def add_task():
    """Ajoute une nouvelle tâche de synchronisation"""
    data = request.form.to_dict()
    
    # Générer un ID unique
    import uuid
    task_id = str(uuid.uuid4())
    
    task = {
        'id': task_id,
        'name': data.get('name', f"Tâche {datetime.now().strftime('%Y%m%d_%H%M%S')}"),
        'server_id': data.get('server_id', ''),
        'source_directory': data.get('source_directory', ''),
        'target_directory': data.get('target_directory', ''),
        'sync_interval': int(data.get('sync_interval', 60)),
        'enabled': data.get('enabled') == 'true',
        'created_at': datetime.now().isoformat(),
        'last_run': None,
        'last_result': None,
        'status': 'idle'  # Statut par défaut: idle, running, completed, failed
    }
    
    tasks = load_tasks()
    tasks.append(task)
    save_tasks(tasks)
    
    app.logger.info(f"Tâche de synchronisation ajoutée: {task['name']}")
    
    # Démarrer le thread pour cette nouvelle tâche
    start_sync_threads()
    
    return redirect(url_for('tasks_page'))


@app.route('/update_task/<task_id>', methods=['POST'])
def update_task(task_id):
    """Met à jour une tâche de synchronisation"""
    data = request.form.to_dict()
    
    tasks = load_tasks()
    task = next((t for t in tasks if t['id'] == task_id), None)
    
    if not task:
        return jsonify({'success': False, 'message': 'Tâche non trouvée'}), 404
    
    # Mettre à jour les champs
    task['name'] = data.get('name', task['name'])
    task['server_id'] = data.get('server_id', task['server_id'])
    task['source_directory'] = data.get('source_directory', task['source_directory'])
    task['target_directory'] = data.get('target_directory', task['target_directory'])
    task['sync_interval'] = int(data.get('sync_interval', task['sync_interval']))
    task['enabled'] = data.get('enabled') == 'true'
    
    save_tasks(tasks)
    
    app.logger.info(f"Tâche mise à jour: {task['name']}")
    
    # Redémarrer les threads pour appliquer les changements
    start_sync_threads()
    
    return jsonify({'success': True, 'message': 'Tâche mise à jour avec succès'})


@app.route('/delete_task/<task_id>', methods=['POST'])
def delete_task(task_id):
    """Supprime une tâche de synchronisation"""
    tasks = load_tasks()
    tasks = [t for t in tasks if t['id'] != task_id]
    save_tasks(tasks)
    
    # Arrêter le thread associé
    if task_id in sync_threads:
        sync_stop_event.set()
        if sync_threads[task_id].is_alive():
            sync_threads[task_id].join(timeout=1)
        del sync_threads[task_id]
        sync_stop_event.clear()
    
    app.logger.info(f"Tâche supprimée: {task_id}")
    
    return jsonify({'success': True, 'message': 'Tâche supprimée avec succès'})


@app.route('/run_task/<task_id>', methods=['POST'])
def run_task(task_id):
    """Exécute immédiatement une tâche de synchronisation"""
    tasks = load_tasks()
    task = next((t for t in tasks if t['id'] == task_id), None)
    
    if not task:
        return jsonify({'success': False, 'message': 'Tâche non trouvée'}), 404
    
    result = execute_sync_task(task)
    
    return jsonify(result)


@app.route('/toggle_task/<task_id>', methods=['POST'])
def toggle_task(task_id):
    """Active ou désactive une tâche"""
    tasks = load_tasks()
    task = next((t for t in tasks if t['id'] == task_id), None)
    
    if not task:
        return jsonify({'success': False, 'message': 'Tâche non trouvée'}), 404
    
    task['enabled'] = not task.get('enabled', True)
    save_tasks(tasks)
    
    # Redémarrer les threads
    start_sync_threads()
    
    action = "activée" if task['enabled'] else "désactivée"
    app.logger.info(f"Tâche {action}: {task['name']}")
    
    return jsonify({'success': True, 'enabled': task['enabled'], 'message': f"Tâche {action}"})


@app.route('/api/sync_stats', methods=['GET'])
def api_sync_stats():
    """API: Retourne les statistiques de synchronisation en cours pour toutes les tâches"""
    tasks = load_tasks()
    
    # Trouver les tâches en cours
    active_syncs = []
    for task in tasks:
        if task.get('status') == 'running':
            # Si la tâche est en cours, essayer de récupérer les stats
            result = task.get('last_result', {})
            stats = result.get('stats', {})
            
            # Si last_result est vide mais que la tâche est en cours depuis un moment,
            # on peut essayer de charger les stats depuis le fichier
            if not stats and task.get('running_since'):
                # Pour les tâches en cours, les stats sont dans last_result seulement à la fin
                # Donc on initialise avec des valeurs par défaut
                stats = {}
            
            sync_info = {
                'task_id': task['id'],
                'task_name': task['name'],
                'server_id': task.get('server_id', ''),
                'source_directory': task.get('source_directory', ''),
                'target_directory': task.get('target_directory', ''),
                'status': task.get('status', 'idle'),
                'source_file_count': stats.get('source_file_count', 0),
                'target_file_count': stats.get('target_file_count', 0),
                'files_uploaded': stats.get('uploaded', 0),
                'files_remaining': stats.get('files_remaining', 0),
                'total_files_to_process': stats.get('total_files_to_process', 0),
                'average_speed_bps': stats.get('average_speed_bps', 0),
                'average_speed_fps': stats.get('average_speed_fps', 0),
                'average_speed_mbps': round(stats.get('average_speed_bps', 0) / (1024 * 1024), 2) if stats.get('average_speed_bps', 0) > 0 else 0,
                'total_bytes_transferred': stats.get('total_bytes_transferred', 0),
                'total_mb_transferred': round(stats.get('total_bytes_transferred', 0) / (1024 * 1024), 2),
                'duration_seconds': stats.get('duration_seconds', 0),
                'estimated_end_time': stats.get('estimated_end_time', ''),
                'start_time': stats.get('start_time', task.get('running_since', '')),
                'errors': stats.get('errors', 0),
                'is_active': True
            }
            active_syncs.append(sync_info)
    
    # Si aucune tâche en cours, retourner les stats de la dernière synchronisation
    if not active_syncs:
        for task in tasks:
            if task.get('last_result'):
                result = task.get('last_result', {})
                stats = result.get('stats', {})
                
                # Vérifier si la tâche a été exécutée récemment (dans la dernière heure)
                last_run = task.get('last_run', '')
                if last_run:
                    from datetime import datetime, timedelta
                    last_run_dt = datetime.fromisoformat(last_run.replace('Z', '+00:00'))
                    if datetime.now() - last_run_dt < timedelta(hours=1):
                        active_syncs.append({
                            'task_id': task['id'],
                            'task_name': task['name'],
                            'server_id': task.get('server_id', ''),
                            'source_directory': task.get('source_directory', ''),
                            'target_directory': task.get('target_directory', ''),
                            'status': 'completed',
                            'source_file_count': stats.get('source_file_count', 0),
                            'target_file_count': stats.get('target_file_count', 0),
                            'files_uploaded': stats.get('uploaded', 0),
                            'files_remaining': 0,
                            'total_files_to_process': stats.get('total_files_to_process', 0),
                            'average_speed_bps': stats.get('average_speed_bps', 0),
                            'average_speed_fps': stats.get('average_speed_fps', 0),
                            'average_speed_mbps': round(stats.get('average_speed_bps', 0) / (1024 * 1024), 2) if stats.get('average_speed_bps', 0) > 0 else 0,
                            'total_bytes_transferred': stats.get('total_bytes_transferred', 0),
                            'total_mb_transferred': round(stats.get('total_bytes_transferred', 0) / (1024 * 1024), 2),
                            'duration_seconds': stats.get('duration_seconds', 0),
                            'estimated_end_time': None,
                            'start_time': stats.get('start_time', ''),
                            'end_time': stats.get('end_time', ''),
                            'errors': stats.get('errors', 0),
                            'is_active': False
                        })
                        break
    
    # Calculer les statistiques globales si plusieurs tâches en cours
    global_stats = {
        'total_source_files': sum(s.get('source_file_count', 0) for s in active_syncs),
        'total_target_files': sum(s.get('target_file_count', 0) for s in active_syncs),
        'total_files_uploaded': sum(s.get('files_uploaded', 0) for s in active_syncs),
        'total_files_remaining': sum(s.get('files_remaining', 0) for s in active_syncs),
        'total_bytes_transferred': sum(s.get('total_bytes_transferred', 0) for s in active_syncs),
        'total_mb_transferred': round(sum(s.get('total_bytes_transferred', 0) for s in active_syncs) / (1024 * 1024), 2),
        'average_speed_bps': sum(s.get('average_speed_bps', 0) for s in active_syncs),
        'average_speed_fps': sum(s.get('average_speed_fps', 0) for s in active_syncs),
        'average_speed_mbps': round(sum(s.get('average_speed_bps', 0) for s in active_syncs) / (1024 * 1024), 2),
        'active_syncs_count': len(active_syncs),
        'has_active_sync': len(active_syncs) > 0
    }
    
    # Si vitesse moyenne > 0 et fichiers restants > 0, calculer l'heure estimée de fin globale
    if global_stats['average_speed_fps'] > 0 and global_stats['total_files_remaining'] > 0:
        remaining_time = global_stats['total_files_remaining'] / global_stats['average_speed_fps']
        from datetime import datetime, timedelta
        estimated_end = datetime.now() + timedelta(seconds=remaining_time)
        global_stats['estimated_end_time'] = estimated_end.strftime('%H:%M:%S')
    
    return jsonify({
        'success': True,
        'active_syncs': active_syncs,
        'global_stats': global_stats
    })


if __name__ == '__main__':
    # Parsing des arguments CLI
    parser = argparse.ArgumentParser(description='FTP Server Manager')
    parser.add_argument('--silent', action='store_true', help='Mode silencieux (seulement les erreurs)')
    parser.add_argument('--verbose', action='store_true', help='Mode verbeux (tous les logs)')
    parser.add_argument('--host', default='0.0.0.0', help='Host pour le serveur web')
    parser.add_argument('--port', type=int, default=5000, help='Port pour le serveur web')
    args = parser.parse_args()
    
    # Configuration du logging
    setup_logging(verbose=args.verbose, silent=args.silent)
    
    # Message de démarrage
    mode = "silencieux" if args.silent else ("verbeux" if args.verbose else "normal")
    app.logger.info(f"Démarrage de {APP_NAME} en mode {mode}")
    app.logger.info(f"Serveur web: http://{args.host}:{args.port}")
    
    # Chargement initial des serveurs
    servers = load_servers()
    app.logger.info(f"Chargé {len(servers)} configurations de serveurs FTP")
    for server in servers:
        app.logger.info(f"  - {server['name']}: {server['host']}")
    
    # Chargement des tâches de synchronisation
    tasks = load_tasks()
    app.logger.info(f"Chargé {len(tasks)} tâches de synchronisation")
    for task in tasks:
        app.logger.info(f"  - {task['name']}: {task['source_directory']} -> {task['target_directory']} (toutes les {task['sync_interval']}s)")
    
    # Démarrer les threads de synchronisation
    start_sync_threads()
    
    # Démarrer le thread de vérification des fichiers corrompus
    start_corrupted_check_thread()
    
    # Lancement du serveur Flask
    app.run(host=args.host, port=args.port, debug=False)
