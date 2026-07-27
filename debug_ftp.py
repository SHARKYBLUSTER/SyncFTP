#!/usr/bin/env python3
"""
Script de debug pour tester l'accès au répertoire FTP
"""

from ftp_tools import FTPConfig, FTPConnector
import sys

def test_directory_access(host, port, username, password, directory_path, use_ssl=False, timeout=30):
    """Test l'accès à un répertoire FTP spécifique avec des messages détaillés"""
    
    config = FTPConfig(
        host=host,
        port=port,
        username=username,
        password=password,
        use_ssl=use_ssl,
        timeout=timeout
    )
    
    connector = FTPConnector(config)
    
    print("=" * 70)
    print("TEST DE CONNEXION ET ACCES AU REPERTOIRE")
    print("=" * 70)
    print(f"Hôte: {host}:{port}")
    print(f"Utilisateur: {username}")
    print(f"SSL: {use_ssl}")
    print(f"Timeout: {timeout}s")
    print(f"Répertoire à tester: {directory_path}")
    print("=" * 70)
    
    # Étape 1: Connexion
    print("\n[1] Tentative de connexion...")
    try:
        success = connector.connect()
        if success:
            print("   ✓ Connexion établie avec succès")
            current_dir = connector._ftp.pwd()
            print(f"   Répertoire courant: {current_dir}")
        else:
            print("   ✗ Échec de la connexion")
            return
    except Exception as e:
        print(f"   ✗ Erreur de connexion: {e}")
        return
    
    # Étape 2: Navigation vers le répertoire
    if directory_path:
        print(f"\n[2] Navigation vers '{directory_path}'...")
        original_dir = connector._ftp.pwd()
        print(f"   Répertoire de départ: {original_dir}")
        
        if directory_path.startswith('/'):
            print(f"   Chemin absolu détecté")
            parts = [p for p in directory_path.split('/') if p]
            print(f"   Parties du chemin: {parts}")
            
            # Essayer le chemin direct d'abord
            try:
                connector._ftp.cwd(directory_path)
                print(f"   ✓ Accès direct réussi à '{directory_path}'")
            except Exception as e:
                print(f"   ✗ Accès direct échoué: {e}")
                print(f"   Tentative de navigation étape par étape...")
                
                # Retour à la racine
                try:
                    connector._ftp.cwd('/')
                    current = '/'
                    print(f"   Retour à la racine: {current}")
                except Exception as e2:
                    print(f"   ✗ Impossible de retourner à la racine: {e2}")
                    return
                
                # Naviguer étape par étape
                for i, part in enumerate(parts):
                    print(f"   Étape {i+1}: cwd('{part}')...")
                    try:
                        connector._ftp.cwd(part)
                        current = current.rstrip('/') + '/' + part if current != '/' else '/' + part
                        print(f"   ✓ Succès - position: {connector._ftp.pwd()}")
                    except Exception as e3:
                        print(f"   ✗ Échec sur '{part}': {e3}")
                        print(f"   Répertoire courant avant l'erreur: {connector._ftp.pwd()}")
                        print(f"   Contenu du répertoire actuel:")
                        try:
                            files = []
                            connector._ftp.retrlines('LIST', lambda x: files.append(x.decode('utf-8', errors='ignore') if isinstance(x, bytes) else x))
                            for f in files[:10]:  # Afficher seulement les 10 premiers
                                print(f"      {f}")
                            if len(files) > 10:
                                print(f"      ... et {len(files) - 10} de plus")
                        except Exception as e4:
                            print(f"      Erreur lors du listage: {e4}")
                        return
        else:
            # Chemin relatif
            print(f"   Chemin relatif depuis '{original_dir}'")
            try:
                connector._ftp.cwd(directory_path)
                print(f"   ✓ Accès réussi")
            except Exception as e:
                print(f"   ✗ Échec: {e}")
                return
        
        final_dir = connector._ftp.pwd()
        print(f"   Répertoire final: {final_dir}")
    
    # Étape 3: Listage du répertoire
    print(f"\n[3] Listage du répertoire '{connector._ftp.pwd()}'...")
    try:
        files = []
        connector._ftp.retrlines('LIST', lambda x: files.append(x.decode('utf-8', errors='ignore') if isinstance(x, bytes) else x))
        
        file_count = 0
        dir_count = 0
        print(f"   Total lignes LIST: {len(files)}")
        
        for line in files:
            line_stripped = line.strip()
            if line_stripped.startswith('-'):
                file_count += 1
            elif line_stripped.startswith('d'):
                dir_count += 1
        
        print(f"   Fichiers: {file_count}")
        print(f"   Répertoires: {dir_count}")
        
        # Afficher les 10 premiers éléments
        print(f"\n   Contenu (10 premiers):")
        for i, line in enumerate(files[:10]):
            print(f"      {line.strip()}")
        if len(files) > 10:
            print(f"      ... et {len(files) - 10} de plus")
        
    except Exception as e:
        print(f"   ✗ Erreur lors du listage: {e}")
    
    # Étape 4: Retour au répertoire original
    try:
        connector._ftp.cwd(original_dir)
        print(f"\n[4] Retour à '{original_dir}' - ✓")
    except Exception:
        pass
    
    # Déconnexion
    connector.disconnect()
    print("\nDéconnecté")

if __name__ == "__main__":
    print("Script de debug pour FTP")
    print("Usage: python debug_ftp.py host port username password directory [--ssl] [--timeout N]")
    
    if len(sys.argv) < 6:
        print("Erreur: il faut au moins 5 arguments")
        print("  host, port, username, password, directory_path")
        sys.exit(1)
    
    host = sys.argv[1]
    port = int(sys.argv[2])
    username = sys.argv[3]
    password = sys.argv[4]
    directory_path = sys.argv[5]
    use_ssl = '--ssl' in sys.argv
    timeout = 30
    for i, arg in enumerate(sys.argv):
        if arg.startswith('--timeout='):
            timeout = int(arg.split('=')[1])
    
    test_directory_access(host, port, username, password, directory_path, use_ssl, timeout)
