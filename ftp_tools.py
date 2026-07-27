"""
FTP Tools - Module réutilisable pour gérer les connexions FTP
=============================================================

Ce module fournit des outils pour tester et gérer les connexions FTP.
Il peut être importé et utilisé par l'application principale SyncFTP.
"""

import ftplib
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class FTPConfig:
    """Configuration pour une connexion FTP."""
    host: str
    port: int = 21
    username: str = "anonymous"
    password: str = ""
    use_ssl: bool = False
    timeout: int = 30


class FTPConnectionError(Exception):
    """Exception levée en cas d'échec de connexion FTP."""
    pass


class FTPConnector:
    """
    Classe pour gérer les connexions FTP et tester leur validité.
    
    Utilisation:
        config = FTPConfig(host="ftp.example.com", username="user", password="pass")
        connector = FTPConnector(config)
        success, message = connector.test_connection()
        if success:
            print("Connexion réussie!")
    """
    
    def __init__(self, config: FTPConfig):
        self.config = config
        self._ftp: Optional[ftplib.FTP] = None
    
    def _create_client(self) -> ftplib.FTP:
        """Crée un client FTP ou FTP_TLS selon la configuration."""
        if self.config.use_ssl:
            return ftplib.FTP_TLS()
        return ftplib.FTP()
    
    def connect(self) -> bool:
        """
        Établit une connexion au serveur FTP.
        
        Returns:
            True si la connexion a réussi.
        
        Raises:
            FTPConnectionError: Si la connexion échoue.
        """
        try:
            self._ftp = self._create_client()
            self._ftp.connect(
                host=self.config.host,
                port=self.config.port,
                timeout=self.config.timeout
            )
            self._ftp.login(user=self.config.username, passwd=self.config.password)
            return True
        except ftplib.all_errors as e:
            raise FTPConnectionError(f"Erreur FTP: {e}")
        except Exception as e:
            raise FTPConnectionError(f"Erreur de connexion: {e}")
    
    def test_connection(self) -> Tuple[bool, str]:
        """
        Teste la connexion FTP.
        
        Returns:
            Tuple[bool, str]: (succès, message)
        """
        try:
            if self.connect():
                # Vérifie que la connexion est fonctionnelle
                self._ftp.pwd()
                self.disconnect()
                return True, "Connexion FTP réussie !"
        except FTPConnectionError as e:
            return False, str(e)
        except Exception as e:
            return False, f"Erreur inattendue: {e}"
        finally:
            self.disconnect()
        
        return False, "Échec de la connexion"
    
    def disconnect(self) -> None:
        """Ferme la connexion FTP si elle est ouverte."""
        if self._ftp:
            try:
                self._ftp.quit()
            except Exception:
                pass
            self._ftp = None
    
    def is_connected(self) -> bool:
        """Vérifie si une connexion est active."""
        return self._ftp is not None
    
    def list_directory(self, path: str = "") -> Tuple[bool, str, int]:
        """
        Liste le contenu d'un répertoire FTP et compte les fichiers.
        
        Args:
            path: Chemin du répertoire à lister (relatif ou absolu).
                   Si vide, utilise le répertoire courant.
        
        Returns:
            Tuple[bool, str, int]: (succès, message, nombre_de_fichiers)
        """
        try:
            if not self.is_connected():
                self.connect()
            
            # Changer de répertoire si un chemin est spécifié
            original_dir = self._ftp.pwd()
            current_path = original_dir
            
            if path:
                # Normaliser le chemin : gérer les chemins absolus et relatifs
                target_path = path
                if path.startswith('/'):
                    # Chemin absolu : essayer de naviguer depuis la racine
                    try:
                        # Essayer le chemin absolu directement
                        self._ftp.cwd(path)
                        current_path = path
                    except ftplib.error_perm:
                        # Si échec, essayer de naviguer étape par étape
                        self._ftp.cwd('/')
                        current_path = '/'
                        parts = [p for p in path.split('/') if p]
                        for part in parts:
                            try:
                                self._ftp.cwd(part)
                                current_path = current_path.rstrip('/') + '/' + part if current_path != '/' else '/' + part
                            except ftplib.error_perm as e:
                                return False, f"Impossible d'accéder au sous-répertoire '{part}' dans '{current_path}': {e}", 0
                else:
                    # Chemin relatif
                    try:
                        self._ftp.cwd(path)
                        current_path = path
                    except ftplib.error_perm as e:
                        return False, f"Impossible d'accéder au répertoire '{path}' depuis '{original_dir}': {e}", 0
            
            # Vérifier que nous sommes bien dans le bon répertoire
            final_dir = self._ftp.pwd()
            
            # Lister le contenu du répertoire
            files = []
            try:
                self._ftp.retrlines('LIST', lambda x: files.append(x.decode('utf-8', errors='ignore') if isinstance(x, bytes) else x))
            except UnicodeDecodeError:
                # Si décodage échoue, essayer sans décodage
                files = []
                self._ftp.retrlines('LIST', lambda x: files.append(x.decode('latin-1', errors='ignore') if isinstance(x, bytes) else x))
            
            # Compter les fichiers (exclure les répertoires)
            file_count = 0
            dir_count = 0
            for line in files:
                line_stripped = line.strip()
                if not line_stripped:
                    continue
                # Analyser la ligne LIST (format Unix)
                if line_stripped.startswith('-'):
                    file_count += 1
                elif line_stripped.startswith('d'):
                    dir_count += 1
            
            # Retourner au répertoire original
            try:
                self._ftp.cwd(original_dir)
            except Exception:
                pass
            
            return True, f"Répertoire '{final_dir}' listé avec succès ({file_count} fichiers, {dir_count} dossiers)", file_count
            
        except ftplib.all_errors as e:
            return False, f"Erreur FTP lors du listage du répertoire '{path}': {e}", 0
        except Exception as e:
            return False, f"Erreur inattendue lors du listage: {e}", 0
