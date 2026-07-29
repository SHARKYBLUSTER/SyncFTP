#!/usr/bin/env python3
"""
SyncFTP - Application Web
========================

Application web pour gérer et synchroniser plusieurs serveurs FTP.
Utilise Flask pour le backend et fournit une interface simple.

Utilisation:
    python app.py              # Mode normal (logs visibles)
    python app.py --silent     # Mode silencieux (seulement les erreurs)
    python app.py --verbose    # Mode verbeux (tous les logs)
"""

import os
import json
import re
import argparse
import logging
import threading
import time
import signal
import uuid
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for
from ftp_tools import FTPConfig, FTPConnector

# Add SUCCESS log level
logging.addLevelName(25, "SUCCESS")
logging.SUCCESS = 25

# Configuration
APP_NAME = "SyncFTP"
APP_VERSION = "2.5.3"
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

# Variable globale pour l'arrêt
shutdown_requested = False

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
    
    # Add success method to Flask app logger
    if not hasattr(app.logger, 'success'):
        app.logger.success = lambda msg, *args, **kwargs: app.logger.log(logging.SUCCESS, msg, *args, **kwargs)


def apply_log_level_from_config():
    """Applique le niveau de log basé sur la configuration actuelle"""
    global file_handler, stream_handler
    
    config = load_config()
    
    # Mapping des modes CLI vers niveaux Python
    mode_level_map = {
        'verbose': logging.DEBUG,
        'standard': logging.INFO,
        'silent': logging.ERROR
    }

    # Si debug_logging_enabled est vrai, forcer le niveau à DEBUG
    debug_enabled = config.get('debug_logging_enabled', False)
    if debug_enabled:
        new_level = logging.DEBUG
    else:
        # Utiliser log_mode s'il existe, sinon laisser le niveau actuel
        new_level = mode_level_map.get(config.get('log_mode', 'standard'), logging.INFO)
    
    app.logger.setLevel(new_level)
    if file_handler:
        file_handler.setLevel(new_level)
    if stream_handler:
        stream_handler.setLevel(new_level)


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
        'app_name': 'SyncFTP',
        'app_version': '1.0.0',
        'log_retention_days': 7,
        'log_refresh_interval': 3,
        'log_mode': 'standard',
        'auto_refresh': True,
        'corrupted_files_check_interval': 300,  # 5 minutes en secondes
        'exclude_patterns': '*.tmp,*.part,*.temp,*.~lk,*.lock,Thumbs.db,desktop.ini',  # Patterns à exclure
        'debug_logging_enabled': False,  # Active les logs DEBUG de performance
        'task_save_throttle': 10,  # Nombre de fichiers entre chaque sauvegarde pendant la sync
        'small_file_timeout': 10,  # Timeout en secondes pour les petits fichiers
        'large_file_timeout': 60,  # Timeout en secondes pour les gros fichiers (> threshold)
        'large_file_threshold_mb': 50,  # Seuil en Mo pour les gros fichiers
        'connection_timeout': 30,  # Timeout de connexion en secondes
        'max_connections': 5,  # Nombre maximum de connexions simultanées
        'retry_attempts': 3,  # Nombre de tentatives de reconnexion
        'retry_delay': 5,  # Délai entre les tentatives en secondes
        'max_log_size_mb': 10  # Taille maximale des logs en Mo avant nettoyage
    }
    if not os.path.exists(CONFIG_FILE):
        save_config(default_config)
        return default_config
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        # Migration de l'ancien log_level vers log_mode
        if 'log_level' in config and 'log_mode' not in config:
            old_level = config['log_level']
            if old_level in ['WARNING', 'ERROR']:
                config['log_mode'] = 'silent'
            elif old_level == 'DEBUG':
                config['log_mode'] = 'verbose'
            else:  # INFO, SUCCESS
                config['log_mode'] = 'standard'
            save_config(config)
        
        # Ajouter les valeurs par défaut si elles n'existent pas
        if 'log_mode' not in config:
            config['log_mode'] = 'standard'
            save_config(config)
        if 'corrupted_files_check_interval' not in config:
            config['corrupted_files_check_interval'] = 300
            save_config(config)
        if 'exclude_patterns' not in config:
            config['exclude_patterns'] = '*.tmp,*.part,*.temp,*.~lk,*.lock,Thumbs.db,desktop.ini'
            save_config(config)
        if 'debug_logging_enabled' not in config:
            config['debug_logging_enabled'] = False
            save_config(config)
        if 'task_save_throttle' not in config:
            config['task_save_throttle'] = 10
            save_config(config)
        if 'small_file_timeout' not in config:
            config['small_file_timeout'] = 10
            save_config(config)
        if 'large_file_timeout' not in config:
            config['large_file_timeout'] = 60
            save_config(config)
        if 'large_file_threshold_mb' not in config:
            config['large_file_threshold_mb'] = 50
            save_config(config)
        if 'connection_timeout' not in config:
            config['connection_timeout'] = 30
            save_config(config)
        if 'max_connections' not in config:
            config['max_connections'] = 5
            save_config(config)
        if 'retry_attempts' not in config:
            config['retry_attempts'] = 3
            save_config(config)
        if 'retry_delay' not in config:
            config['retry_delay'] = 5
            save_config(config)
        if 'app_name' not in config:
            config['app_name'] = 'SyncFTP'
            save_config(config)
        if 'app_version' not in config:
            config['app_version'] = '1.0.0'
            save_config(config)
        if 'log_retention_days' not in config:
            config['log_retention_days'] = 7
            save_config(config)
        if 'log_refresh_interval' not in config:
            config['log_refresh_interval'] = 3
            save_config(config)
        if 'auto_refresh' not in config:
            config['auto_refresh'] = True
            save_config(config)
        if 'max_log_size_mb' not in config:
            config['max_log_size_mb'] = 10
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


def is_debug_logging_enabled():
    """Vérifie si le debug logging est activé dans la configuration"""
    try:
        config = load_config()
        return config.get('debug_logging_enabled', False)
    except Exception:
        return False


def debug_log(message):
    """
    Log un message en mode DEBUG si le debug logging est activé.
    Utilise le logger de l'application avec un préfixe [PERF] pour les logs de performance.
    """
    if is_debug_logging_enabled():
        app.logger.debug(f"[PERF] {message}")


def should_save_tasks(force_during_sync=False):
    """
    Vérifie si on doit sauvegarder les tâches en fonction du throttle configuré.
    Utilise un compteur thread-safe pour limiter la fréquence des sauvegardes.
    Si force_during_sync est True, on sauvegarde plus souvent (toutes les 2 fois au lieu de 10).
    """
    global task_save_counter
    config = load_config()
    throttle = config.get('task_save_throttle', 10)
    
    # Pendant une synchronisation active, on sauvegarde plus souvent pour les stats en temps réel
    if force_during_sync:
        effective_throttle = 2  # Sauvegarder toutes les 2 progressions pendant une sync
    else:
        effective_throttle = throttle
    
    with task_save_counter_lock:
        task_save_counter += 1
        if task_save_counter >= effective_throttle:
            task_save_counter = 0
            return True
        return False


def cleanup_logs_by_size():
    """Nettoie les logs si le fichier dépasse la taille maximale configurée"""
    config = load_config()
    max_size_mb = config.get('max_log_size_mb', 10)
    
    if not os.path.exists(LOG_FILE):
        return
    
    try:
        # Vérifier la taille actuelle du fichier
        file_size_bytes = os.path.getsize(LOG_FILE)
        max_size_bytes = max_size_mb * 1024 * 1024  # Convertir Mo en octets
        
        if file_size_bytes <= max_size_bytes:
            return  # Pas besoin de nettoyer
        
        # Lire toutes les lignes
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Supprimer 20% des lignes les plus anciennes pour réduire la taille
        # Cela permet un nettoyage progressif plutôt que de tout supprimer
        lines_to_remove = max(1, int(len(lines) * 0.2))
        new_lines = lines[lines_to_remove:]
        
        # Écrire les lignes restantes
        with open(LOG_FILE, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        
        app.logger.info(f"Nettoyage des logs par taille: supprimées {lines_to_remove} lignes, taille réduite de {file_size_bytes} à {os.path.getsize(LOG_FILE)} octets")
    except Exception as e:
        app.logger.error(f"Erreur lors du nettoyage des logs par taille: {e}")


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
        
        # Après le nettoyage par date, vérifier aussi la taille
        cleanup_logs_by_size()
        
        app.logger.info(f"Nettoyage des logs: conservés {len(new_lines)} lignes sur {len(lines)}")
    except Exception as e:
        app.logger.error(f"Erreur lors du nettoyage des logs: {e}")


def filter_logs(logs, log_type=None, level=None, search=None, limit=None):
    """Filtre les logs par type, niveau, recherche et limite"""
    if not logs or logs.strip() == "":
        return []
    
    lines = logs.split('\n')
    filtered_lines = []
    
    for line in lines:
        if not line.strip():
            continue
            
        # Filtrer par type (ancienne méthode pour compatibilité)
        if log_type and log_type != 'ALL':
            if log_type == 'INFO' and ('" 200 ' in line or '" 200-' in line):
                continue
            if f'] {log_type}:' not in line:
                continue
        
        # Filtrer par niveau (nouveau système)
        if level and level != '':
            # Extraire le niveau du log (format: [timestamp] LEVEL: message)
            level_match = re.search(r'\] (INFO|WARNING|ERROR|SUCCESS|DEBUG):', line)
            if level_match:
                log_level = level_match.group(1)
                if log_level != level:
                    continue
            else:
                # Si on ne trouve pas le niveau, on saute
                if 'INFO' not in line and 'WARNING' not in line and 'ERROR' not in line and 'SUCCESS' not in line and 'DEBUG' not in line:
                    continue
        
        # Filtrer par recherche
        if search and search != '':
            if search.lower() not in line.lower():
                continue
        
        filtered_lines.append(line)
    
    # Appliquer la limite (du plus récent au plus ancien)
    if limit and limit != '':
        try:
            limit_num = int(limit)
            filtered_lines = filtered_lines[:limit_num]
        except ValueError:
            pass
    
    return filtered_lines


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

# Variable globale pour le throttling des sauvegardes de tâches
task_save_counter = 0
task_save_counter_lock = threading.Lock()


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
    
    # Vérifier si la tâche est activée
    if not task.get('enabled', True):
        result['message'] = f"Tâche désactivée: {task['name']}"
        app.logger.warning(result['message'])
        return result
    
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
            
            # Charger la configuration globale pour les timeouts
            sync_config = load_config()
            small_file_timeout = sync_config.get('small_file_timeout', 10)
            large_file_timeout = sync_config.get('large_file_timeout', 60)
            large_file_threshold_mb = sync_config.get('large_file_threshold_mb', 50)
            large_file_threshold = large_file_threshold_mb * 1024 * 1024
            
            # Créer la configuration FTP
            config = FTPConfig(
                host=server['host'],
                port=int(server.get('port', 21)),
                username=server.get('username', 'anonymous'),
                password=server.get('password', ''),
                use_ssl=server.get('use_ssl', False),
                timeout=small_file_timeout,
                large_file_threshold=large_file_threshold,
                large_file_timeout=large_file_timeout
            )
            
            connector = FTPConnector(config)
            
            # Charger la configuration pour le throttling et le debug
            throttle = sync_config.get('task_save_throttle', 10)
            debug_enabled = sync_config.get('debug_logging_enabled', False)
            
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
                    
                    # Log de performance si activé
                    if debug_enabled:
                        uploaded = current_stats.get('uploaded', 0)
                        total = current_stats.get('total_files_to_process', 0)
                        if total > 0:
                            percentage = (uploaded / total) * 100
                            elapsed = current_stats.get('duration_seconds', 0)
                            speed = current_stats.get('average_speed_fps', 0)
                            debug_log(f"Tâche {task['id']}: Progression {uploaded}/{total} ({percentage:.1f}%), "
                                    f"vitesse: {speed:.2f} fichiers/s, temps écoulé: {elapsed:.1f}s")
                    
                    # Sauvegarder les tâches toutes les 2 progressions pendant l'exécution pour des stats quasi temps réel
                    if should_save_tasks(force_during_sync=True):
                        save_tasks(tasks)
            
            # Exécuter la synchronisation
            app.logger.info(f"Exécution de la tâche {task['id']}: {task['name']}")
            debug_log(f"Démarrage synchronisation: {task['source_directory']} -> {task['target_directory']}")
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
                app.logger.success(f"Tâche {task['id']} terminée avec succès: {stats.get('uploaded', 0)} fichiers synchronisés")
                debug_log(f"Tâche {task['id']} terminée: {stats.get('uploaded', 0)} uploadés, "
                         f"{stats.get('deleted', 0)} supprimés, durée: {stats.get('duration_seconds', 0):.2f}s, "
                         f"vitesse moyenne: {stats.get('average_speed_fps', 0):.2f} fichiers/s")
            else:
                app.logger.error(f"Échec de la tâche {task['id']}: {message}")
                debug_log(f"Échec tâche {task['id']}: {message}")
            
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
    debug_log(f"Worker démarré pour tâche {task_id}, intervalle: {interval}s")
    
    # Exécuter immédiatement la première synchronisation
    if not sync_stop_event.is_set():
        debug_log(f"Premier lancer immédiat pour tâche {task_id}")
        execute_sync_task(task)
    
    # Boucle principale
    iteration_count = 0
    while not sync_stop_event.is_set():
        try:
            iteration_count += 1
            start_wait = time.time()
            
            # Attendre l'intervalle
            time.sleep(interval)
            
            wait_duration = time.time() - start_wait
            debug_log(f"Tâche {task_id}: Attente terminée, durée réelle: {wait_duration:.2f}s (attendu: {interval}s)")
            
            # Vérifier si la tâche existe toujours
            tasks = load_tasks()
            task_exists = any(t['id'] == task_id for t in tasks)
            if not task_exists:
                debug_log(f"Tâche {task_id} supprimée, arrêt du worker")
                break
            
            # Exécuter la synchronisation
            if not sync_stop_event.is_set():
                debug_log(f"Lancement synchronisation itération {iteration_count} pour tâche {task_id}")
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
            result = FTPConnector.check_and_delete_corrupted_files(tasks, servers, logger=app.logger)
            
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
    
    # Compter les tâches par statut
    disabled_count = sum(1 for t in tasks if not t.get('enabled', True))
    running_count = sum(1 for t in tasks if t.get('status') == 'running')
    completed_count = sum(1 for t in tasks if t.get('status') == 'completed')
    failed_count = sum(1 for t in tasks if t.get('status') == 'failed')
    idle_count = sum(1 for t in tasks if t.get('status') == 'idle')
    
    # Collecter les fichiers échoués des tâches avec statut 'failed'
    failed_files = []
    for task in tasks:
        if task.get('status') == 'failed' and task.get('last_result'):
            stats = task['last_result'].get('stats', {})
            if 'failed_files' in stats:
                for file in stats['failed_files']:
                    # Gérer les anciens formats (chaîne) et le nouveau format (dict)
                    if isinstance(file, dict):
                        file_path = file.get('path', 'Chemin inconnu')
                        file_size = file.get('size', 0)
                    else:
                        # Ancien format: juste le chemin en chaîne
                        file_path = file
                        file_size = 0
                    
                    failed_files.append({
                        'task_name': task.get('name', 'Tâche inconnue'),
                        'file_path': file_path,
                        'file_size': file_size
                    })
    
    return render_template('index.html', 
                         server_count=len(servers), 
                         task_count=len(tasks),
                         disabled_count=disabled_count,
                         running_count=running_count,
                         completed_count=completed_count,
                         failed_count=failed_count,
                         idle_count=idle_count,
                         failed_files=failed_files,
                         app_name=APP_NAME, 
                         app_version=APP_VERSION)


# @app.route('/add')
# def add_page():
#     """Page d'ajout d'un serveur FTP - Désactivée car remplacée par la modale dans /list"""
#     return render_template('add.html', app_name=APP_NAME, app_version=APP_VERSION)


@app.route('/list')
def list_servers():
    """Page de liste des serveurs"""
    servers = load_servers()
    return render_template('list.html', servers=servers, app_name=APP_NAME, app_version=APP_VERSION)


@app.route('/logs')
def logs_page():
    """Page d'affichage des logs"""
    config = load_config()
    return render_template('logs.html', config=config, app_name=APP_NAME, app_version=APP_VERSION)


@app.route('/config')
def config_page():
    """Page de configuration"""
    config = load_config()
    return render_template('config.html', config=config, app_name=APP_NAME, app_version=APP_VERSION, shutdown_requested=shutdown_requested)


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
    level = request.args.get('level', '')
    search = request.args.get('search', '')
    limit = request.args.get('limit', '')
    
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
        filtered_logs = filter_logs(logs, log_type, level, search, limit)
        
        # Formater les logs pour le frontend
        log_entries = []
        for line in filtered_logs:
            if line.strip():
                # Parser la ligne de log: [timestamp] LEVEL: message
                match = re.match(r'\[([^\]]+)\] (INFO|WARNING|ERROR|SUCCESS|DEBUG): (.+)', line)
                if match:
                    timestamp = match.group(1)
                    level_str = match.group(2)
                    message = match.group(3)
                    log_entries.append({
                        'timestamp': timestamp,
                        'level': level_str,
                        'message': message
                    })
                else:
                    # Format alternatif ou ligne mal formatée
                    log_entries.append({
                        'timestamp': '',
                        'level': 'INFO',
                        'message': line.strip()
                    })
        
        return jsonify({'logs': log_entries})


@app.route('/api/config', methods=['GET', 'POST'])
def api_config():
    """API: Récupère ou sauvegarde la configuration"""
    if request.method == 'POST':
        config = request.json
        save_config(config)
        
        # Appliquer le nouveau niveau de log
        apply_log_level_from_config()
        
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


@app.route('/api/clear_database', methods=['POST'])
def api_clear_database():
    """API: Supprime tous les logs et l'historique des synchronisations"""
    try:
        # Fermer et retirer le file handler pour permettre la suppression sous Windows
        global file_handler
        if file_handler:
            file_handler.flush()
            file_handler.close()
            logging.getLogger().removeHandler(file_handler)
            file_handler = None
        
        # Supprimer le fichier de logs
        if os.path.exists(LOG_FILE):
            os.remove(LOG_FILE)
        
        # Supprimer l'historique des tâches (sync_tasks.json)
        if os.path.exists(TASKS_FILE):
            os.remove(TASKS_FILE)
        
        # Recréer le file handler pour que le logging continue de fonctionner
        recreate_file_handler()
        
        # Logger la réussite après avoir recréé le handler
        app.logger.info("Logs et historique supprimés")
        
        return jsonify({'success': True, 'message': 'Logs et historique supprimés'})
    except Exception as e:
        # Recréer le handler en cas d'erreur avant de logger
        recreate_file_handler()
        app.logger.error(f"Erreur lors de la suppression des logs et historique: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/shutdown', methods=['POST'])
def api_shutdown():
    """API: Arrête proprement le service"""
    global shutdown_requested
    
    if shutdown_requested:
        return jsonify({'success': False, 'message': 'Arrêt déjà en cours'}), 400
    
    shutdown_requested = True
    app.logger.warning("Arrêt du service demandé via API")
    
    # Arrêter les threads de synchronisation
    stop_sync_threads()
    
    # Arrêter le thread de vérification des fichiers corrompus
    stop_corrupted_check_thread()
    
    # Fermer les handlers de logging
    global file_handler, stream_handler
    
    if file_handler:
        try:
            file_handler.flush()
            file_handler.close()
            logging.getLogger().removeHandler(file_handler)
        except:
            pass
    
    if stream_handler:
        try:
            stream_handler.flush()
            stream_handler.close()
            logging.getLogger().removeHandler(stream_handler)
        except:
            pass
    
    # Essayer d'arrêter le serveur via werkzeug
    try:
        request.environ.get('werkzeug.server.shutdown')()
        return jsonify({'success': True, 'message': 'Arrêt du service en cours...'}), 200
    except:
        # Si werkzeug.server.shutdown n'est pas disponible, utiliser os._exit
        # Mais d'abord retourner une réponse
        def delayed_shutdown():
            import time
            time.sleep(1)  # Donner le temps à la réponse de partir
            app.logger.warning("Forçage de l'arrêt du service")
            os._exit(0)
        
        threading.Thread(target=delayed_shutdown, daemon=True).start()
        return jsonify({'success': True, 'message': 'Arrêt du service en cours...'}), 200


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


@app.route('/add_server_ajax', methods=['POST'])
def add_server_ajax():
    """Ajoute un nouveau serveur FTP via AJAX (retourne JSON)"""
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
    
    app.logger.info(f"Serveur FTP ajouté via AJAX: {server['name']} ({server['host']})")
    
    return jsonify({'success': True, 'server_id': server_id, 'message': 'Serveur ajouté avec succès'})


@app.route('/delete_server/<server_id>', methods=['POST'])
def delete_server(server_id):
    """Supprime un serveur FTP"""
    servers = load_servers()
    servers = [s for s in servers if s['id'] != server_id]
    save_servers(servers)
    
    app.logger.info(f"Serveur FTP supprimé: {server_id}")
    
    return redirect(url_for('index'))


@app.route('/update_server', methods=['POST'])
def update_server():
    """Met à jour un serveur FTP existant"""
    data = request.form.to_dict()
    server_id = data.get('server_id')
    
    if not server_id:
        return jsonify({'success': False, 'error': 'ID de serveur manquant'}), 400
    
    servers = load_servers()
    server_index = next((i for i, s in enumerate(servers) if s['id'] == server_id), None)
    
    if server_index is None:
        return jsonify({'success': False, 'error': 'Serveur non trouvé'}), 404
    
    # Mettre à jour les données du serveur
    servers[server_index].update({
        'name': data.get('name', servers[server_index]['name']),
        'host': data.get('host', servers[server_index]['host']),
        'port': data.get('port', servers[server_index]['port']),
        'username': data.get('username', servers[server_index]['username']),
        'password': data.get('password', servers[server_index]['password']),
        'use_ssl': data.get('use_ssl') == 'true' if 'use_ssl' in data else servers[server_index]['use_ssl'],
        'timeout': data.get('timeout', servers[server_index]['timeout']),
        'test_directory': data.get('test_directory', servers[server_index]['test_directory']),
        'updated_at': datetime.now().isoformat()
    })
    
    save_servers(servers)
    
    app.logger.info(f"Serveur FTP mis à jour: {servers[server_index]['name']} ({servers[server_index]['host']})")
    
    return jsonify({'success': True, 'message': 'Serveur mis à jour avec succès'})


@app.route('/test_server', methods=['POST'])
def test_server():
    """Teste la connexion à un serveur FTP"""
    try:
        server_id = request.form.get('server_id')
        test_directory = request.form.get('test_directory', '')
        
        if not server_id:
            return jsonify({
                'success': False,
                'server_name': 'Inconnu',
                'server_id': None,
                'message': 'Aucun ID de serveur fourni',
                'error': 'Le paramètre server_id est manquant'
            }), 400
        
        servers = load_servers()
        server = next((s for s in servers if s['id'] == server_id), None)
        
        if not server:
            return jsonify({
                'success': False,
                'server_name': 'Inconnu',
                'server_id': server_id,
                'message': 'Serveur non trouvé',
                'error': 'Le serveur avec cet ID n\'existe pas'
            }), 404
        
        # Si un répertoire de test est fourni, l'utiliser temporairement
        original_test_dir = server.get('test_directory', '')
        if test_directory:
            server['test_directory'] = test_directory
        
        result = test_ftp_connection(server)
        
        # Restaurer le répertoire de test original
        if test_directory:
            server['test_directory'] = original_test_dir
        
        return jsonify(result)
    except Exception as e:
        app.logger.error(f"Erreur dans test_server: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'server_name': 'Inconnu',
            'server_id': server_id if 'server_id' in locals() else None,
            'message': 'Erreur interne du serveur',
            'error': str(e)
        }), 500


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
    return render_template('tasks.html', tasks=tasks, servers=servers, app_name=APP_NAME, app_version=APP_VERSION)


@app.route('/api/tasks', methods=['GET'])
def api_tasks():
    """API: Retourne la liste des tâches"""
    tasks = load_tasks()
    return jsonify(tasks)


@app.route('/get_task/<task_id>', methods=['GET'])
def get_task(task_id):
    """Récupère les informations d'une tâche"""
    tasks = load_tasks()
    task = next((t for t in tasks if t['id'] == task_id), None)
    if not task:
        return jsonify({'success': False, 'message': 'Tâche non trouvée'}), 404
    return jsonify({'success': True, 'task': task})


@app.route('/save_task', methods=['POST'])
def save_task():
    """Sauvegarde une tâche (création ou modification)"""
    data = request.form.to_dict()
    task_id = data.get('task_id', '')
    
    if task_id:
        # Modification de tâche existante
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
    else:
        # Nouvelle tâche
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
            'status': 'idle'
        }
        
        tasks = load_tasks()
        tasks.append(task)
        save_tasks(tasks)
        
        app.logger.info(f"Tâche de synchronisation ajoutée: {task['name']}")
        
        # Démarrer le thread pour cette nouvelle tâche
        start_sync_threads()
    
    return redirect(url_for('tasks_page'))


@app.route('/add_task', methods=['POST'])
def add_task():
    """Ajoute une nouvelle tâche de synchronisation"""
    data = request.form.to_dict()
    
    # Générer un ID unique
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
    
    # Vérifier si la tâche est activée
    if not task.get('enabled', True):
        return jsonify({'success': False, 'message': f"Tâche désactivée: {task['name']}. Activez-la d'abord."}), 400
    
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
            
            # Si last_result existe mais stats est vide, on garde les valeurs par défaut
            # Les stats sont mises à jour en temps réel via progress_callback dans execute_sync_task
            if not stats:
                # Initialiser avec des valeurs par défaut si aucune stat disponible
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
                'excluded': stats.get('excluded', 0),
                'excluded_files': stats.get('excluded_files', []),
                'uploaded_files': stats.get('uploaded_files', []),
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
                            'excluded': stats.get('excluded', 0),
                            'excluded_files': stats.get('excluded_files', []),
                            'uploaded_files': stats.get('uploaded_files', []),
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


@app.route('/api/active_tasks', methods=['GET'])
def api_active_tasks():
    """API: Retourne les tâches actives - alias pour /api/sync_stats"""
    return api_sync_stats()


@app.route('/api/reset_failed_tasks', methods=['POST'])
def reset_failed_tasks():
    """API: Réinitialise toutes les tâches échouées au statut 'idle'"""
    tasks = load_tasks()
    
    reset_count = 0
    for task in tasks:
        if task.get('status') == 'failed':
            task['status'] = 'idle'
            # Réinitialiser les infos de dernière exécution
            if 'last_execution' in task:
                del task['last_execution']
            if 'last_result' in task:
                del task['last_result']
            if 'last_error' in task:
                del task['last_error']
            reset_count += 1
    
    save_tasks(tasks)
    app.logger.info(f"Réinitialisation de {reset_count} tâche(s) échouée(s)")
    
    # Redémarrer les threads de synchronisation
    start_sync_threads()
    
    return jsonify({
        'success': True,
        'message': f'{reset_count} tâche(s) échouée(s) réinitialisée(s)',
        'reset_count': reset_count
    })


@app.route('/api/failed_files', methods=['GET'])
def api_failed_files():
    """API: Retourne la liste des fichiers échoués avec le nom de la tâche"""
    tasks = load_tasks()
    
    failed_files = []
    for task in tasks:
        if task.get('status') == 'failed' and task.get('last_result'):
            stats = task['last_result'].get('stats', {})
            if 'failed_files' in stats:
                for file in stats['failed_files']:
                    # Gérer les anciens formats (chaîne) et le nouveau format (dict)
                    if isinstance(file, dict):
                        file_path = file.get('path', 'Chemin inconnu')
                        file_size = file.get('size', 0)
                    else:
                        # Ancien format: juste le chemin en chaîne
                        file_path = file
                        file_size = 0
                    
                    failed_files.append({
                        'task_name': task.get('name', 'Tâche inconnue'),
                        'file_path': file_path,
                        'file_size': file_size
                    })
    
    return jsonify({
        'success': True,
        'failed_files': failed_files,
        'count': len(failed_files)
    })


def run_flask_app():
    """Lance le serveur Flask"""
    app.run(host=args.host, port=args.port, debug=False)


if __name__ == '__main__':
    # Parsing des arguments CLI
    parser = argparse.ArgumentParser(description='SyncFTP')
    parser.add_argument('--silent', action='store_true', help='Mode silencieux (seulement les erreurs)')
    parser.add_argument('--verbose', action='store_true', help='Mode verbeux (tous les logs)')
    parser.add_argument('--host', default='0.0.0.0', help='Host pour le serveur web')
    parser.add_argument('--port', type=int, default=5000, help='Port pour le serveur web')
    args = parser.parse_args()
    
    # Configuration du logging
    setup_logging(verbose=args.verbose, silent=args.silent)
    
    # Appliquer la configuration de niveau de log depuis config.json
    # (pour prendre en compte debug_logging_enabled au démarrage)
    apply_log_level_from_config()
    
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
    run_flask_app()
