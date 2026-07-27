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
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for
from ftp_tools import FTPConfig, FTPConnector

# Configuration
APP_NAME = "FTP Server Manager"
DATA_FILE = "ftp_servers.json"
LOG_FORMAT = "[%(asctime)s] %(levelname)s: %(message)s"

# Initialisation de l'app Flask
app = Flask(__name__)

# Configuration du logging
def setup_logging(verbose=False, silent=False):
    """Configure le niveau de logging"""
    if silent:
        logging.basicConfig(level=logging.ERROR, format=LOG_FORMAT)
        app.logger.setLevel(logging.ERROR)
    elif verbose:
        logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)
        app.logger.setLevel(logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
        app.logger.setLevel(logging.INFO)


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


# Routes
@app.route('/')
def index():
    """Page d'accueil - tableau de bord"""
    servers = load_servers()
    return render_template('index.html', server_count=len(servers), app_name=APP_NAME)


@app.route('/add')
def add_page():
    """Page d'ajout d'un serveur FTP"""
    return render_template('add.html', app_name=APP_NAME)


@app.route('/list')
def list_servers():
    """Page de liste des serveurs"""
    servers = load_servers()
    return render_template('list.html', servers=servers, app_name=APP_NAME)


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
    
    # Lancement du serveur Flask
    app.run(host=args.host, port=args.port, debug=False)
