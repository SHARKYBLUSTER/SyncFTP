#!/usr/bin/env python3
"""
Test FTP Connection - Interface Textuelle (TUI)
==============================================

Outil en ligne de commande pour tester une connexion FTP.
Demande les informations de connexion via une interface texte simple.

Utilisation:
    python test_ftp_tui.py
"""

import os
from ftp_tools import FTPConfig, FTPConnector


def load_env_file(file_path='.env'):
    """Charge les variables d'environnement depuis un fichier .env"""
    env_vars = {}
    if not os.path.exists(file_path):
        return env_vars
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Ignorer les commentaires et lignes vides
                if not line or line.startswith('#'):
                    continue
                # Parsing de la ligne key=value
                if '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    except Exception:
        pass
    
    return env_vars


def get_input(prompt: str, default: str = "") -> str:
    """Affiche un prompt et retourne la valeur saisie ou la valeur par défaut."""
    value = input(f"{prompt} [{default}]: ").strip()
    return value if value else default


def get_int_input(prompt: str, default: int) -> int:
    """Affiche un prompt et retourne un entier ou la valeur par défaut."""
    value = input(f"{prompt} [{default}]: ").strip()
    return int(value) if value.isdigit() else default


def get_bool_input(prompt: str, default: bool) -> bool:
    """Affiche un prompt et retourne un booléen ou la valeur par défaut."""
    value = input(f"{prompt} (o/n) [{'o' if default else 'n'}]: ").strip().lower()
    if not value:
        return default
    return value.startswith('o') or value.startswith('y')


def main():
    """Point d'entrée principal de l'outil TUI."""
    # Charger les variables d'environnement depuis .env
    env_vars = load_env_file()
    
    print("\n" + "=" * 60)
    print("           FTP CONNECTION TESTER")
    print("=" * 60 + "\n")
    
    # Collecte des informations de connexion avec valeurs par défaut depuis .env
    print("FTP Connection Details\n")
    
    # Valeurs par défaut depuis .env ou valeurs par défaut standard
    default_host = env_vars.get('FTP_HOST', 'localhost')
    default_port = int(env_vars.get('FTP_PORT', '21'))
    default_username = env_vars.get('FTP_USERNAME', 'anonymous')
    default_password = env_vars.get('FTP_PASSWORD', '')
    default_use_ssl = env_vars.get('FTP_USE_SSL', 'false').lower() in ('true', '1', 'yes', 'o')
    default_timeout = int(env_vars.get('FTP_TIMEOUT', '30'))
    default_test_directory = env_vars.get('FTP_TEST_DIRECTORY_ENABLED', 'false').lower() in ('true', '1', 'yes', 'o')
    default_directory_path = env_vars.get('FTP_TEST_DIRECTORY', '')
    
    # Afficher un message si .env est chargé
    if env_vars:
        print("[Configuration chargée depuis .env]\n")
    
    host = get_input("Host", default_host)
    if not host:
        print("Error: Host is required.")
        return
    
    port = get_int_input("Port", default_port)
    username = get_input("Username", default_username)
    password = get_input("Password", default_password)
    use_ssl = get_bool_input("Use SSL (FTPS)", default_use_ssl)
    timeout = get_int_input("Timeout (seconds)", default_timeout)
    test_directory = get_bool_input("Tester un répertoire spécifique", default_test_directory)
    directory_path = "" 
    if test_directory:
        directory_path = get_input("Chemin du répertoire (laisser vide pour le répertoire racine)", default_directory_path)
    
    # Création de la configuration
    config = FTPConfig(
        host=host,
        port=port,
        username=username,
        password=password,
        use_ssl=use_ssl,
        timeout=timeout
    )
    
    # Test de la connexion et du répertoire
    print("\n" + "-" * 60)
    print("Testing connection...")
    print("-" * 60)
    
    connector = FTPConnector(config)
    
    # Tester la connexion
    connection_success = False
    connection_message = ""
    try:
        connection_success = connector.connect()
        if connection_success:
            # Vérifier que la connexion est fonctionnelle
            connector._ftp.pwd()
            connection_message = "Connexion FTP réussie !"
        else:
            connection_message = "Échec de la connexion FTP"
    except Exception as e:
        connection_success = False
        connection_message = f"Erreur: {e}"
    
    # Test du répertoire si demandé
    file_count = 0
    dir_success = False
    dir_message = ""
    
    if connection_success and test_directory:
        print("\n" + "-" * 60)
        print("Testing directory...")
        print(f"Path: {directory_path}")
        print("-" * 60)
        dir_success, dir_message, file_count = connector.list_directory(directory_path)
    
    # Déconnecter
    connector.disconnect()
    
    success = connection_success
    
    # Affichage du résultat
    print("\n" + "=" * 60)
    if success:
        print("[SUCCESS] Connection successful!")
    else:
        print("[FAILED] Connection failed")
    print("=" * 60)
    print(f"Message: {connection_message}")
    
    # Affichage du résultat du test de répertoire
    if test_directory:
        print("-" * 60)
        if dir_success:
            print(f"[SUCCESS] Directory test successful!")
            print(f"Répertoire: {directory_path or '/'}")
            print(f"Nombre de fichiers: {file_count}")
        else:
            print("[FAILED] Directory test failed")
            print(f"Chemin testé: {directory_path or '/'}")
        print(f"Message: {dir_message}")
    print("=" * 60 + "\n")
    
    # Attendre que l'utilisateur appuie sur Entrée
    input("Press Enter to exit...")


if __name__ == "__main__":
    main()
