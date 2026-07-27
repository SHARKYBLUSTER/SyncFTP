"""
FTP Tools - Module réutilisable pour gérer les connexions FTP
=============================================================

Ce module fournit des outils pour tester et gérer les connexions FTP.
Il peut être importé et utilisé par l'application principale SyncFTP.
"""

import ftplib
import os
import io
from dataclasses import dataclass
from typing import Optional, Tuple, List, Dict, Any


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
    
    def upload_file(self, local_path: str, remote_path: str) -> Tuple[bool, str]:
        """
        Upload un fichier local vers le serveur FTP.
        
        Args:
            local_path: Chemin du fichier local à uploader
            remote_path: Chemin du fichier distant (répertoire + nom de fichier)
        
        Returns:
            Tuple[bool, str]: (succès, message)
        """
        try:
            if not self.is_connected():
                self.connect()
            
            # Extraire le répertoire distant et le nom de fichier
            remote_dir = os.path.dirname(remote_path)
            filename = os.path.basename(remote_path)
            
            # Changer de répertoire distant si nécessaire
            if remote_dir:
                try:
                    self._ftp.cwd(remote_dir)
                except ftplib.error_perm as e:
                    # Essayer de créer le répertoire
                    self._create_remote_directory(remote_dir)
                    self._ftp.cwd(remote_dir)
            
            # Lire et uploader le fichier
            with open(local_path, 'rb') as f:
                self._ftp.storbinary(f'STOR {filename}', f)
            
            return True, f"Fichier {filename} uploadé avec succès vers {remote_path}"
            
        except ftplib.all_errors as e:
            return False, f"Erreur FTP lors de l'upload: {e}"
        except Exception as e:
            return False, f"Erreur lors de l'upload: {e}"
        finally:
            self.disconnect()
    
    def _create_remote_directory(self, remote_path: str) -> bool:
        """
        Crée un répertoire distant sur le serveur FTP (récursivement).
        
        Args:
            remote_path: Chemin du répertoire à créer
            
        Returns:
            bool: True si créé avec succès
        """
        try:
            # Normaliser le chemin (enlever les / de fin)
            remote_path = remote_path.rstrip('/')
            
            # Sauvegarder le répertoire courant
            current_dir = self._ftp.pwd()
            
            # Si c'est un chemin absolu, commencer depuis la racine
            if remote_path.startswith('/'):
                self._ftp.cwd('/')
                parts = [p for p in remote_path.split('/') if p]
            else:
                parts = [p for p in remote_path.split('/') if p]
            
            # Créer chaque partie du chemin
            for part in parts:
                try:
                    self._ftp.cwd(part)
                except ftplib.error_perm:
                    # Le répertoire n'existe pas, le créer
                    try:
                        self._ftp.mkd(part)
                        self._ftp.cwd(part)
                    except ftplib.error_perm as e:
                        return False
            
            # Retourner au répertoire original
            try:
                self._ftp.cwd(current_dir)
            except Exception:
                pass
            
            return True
            
        except Exception:
            return False
    
    def download_file(self, remote_path: str, local_path: str) -> Tuple[bool, str]:
        """
        Télécharge un fichier depuis le serveur FTP vers un chemin local.
        
        Args:
            remote_path: Chemin du fichier distant
            local_path: Chemin local où enregistrer le fichier
        
        Returns:
            Tuple[bool, str]: (succès, message)
        """
        try:
            if not self.is_connected():
                self.connect()
            
            # Extraire le nom de fichier distant
            filename = os.path.basename(remote_path)
            remote_dir = os.path.dirname(remote_path)
            
            # Changer de répertoire distant si nécessaire
            if remote_dir:
                try:
                    self._ftp.cwd(remote_dir)
                except ftplib.error_perm as e:
                    return False, f"Impossible d'accéder au répertoire distant: {e}"
            
            # Assurer que le répertoire local existe
            local_dir = os.path.dirname(local_path)
            if local_dir and not os.path.exists(local_dir):
                os.makedirs(local_dir, exist_ok=True)
            
            # Télécharger le fichier
            with open(local_path, 'wb') as f:
                self._ftp.retrbinary(f'RETR {filename}', f.write)
            
            return True, f"Fichier {filename} téléchargé avec succès vers {local_path}"
            
        except ftplib.all_errors as e:
            return False, f"Erreur FTP lors du téléchargement: {e}"
        except Exception as e:
            return False, f"Erreur lors du téléchargement: {e}"
        finally:
            self.disconnect()
    
    def sync_directory_to_ftp(self, local_dir: str, remote_dir: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Synchronise un répertoire local vers un répertoire FTP.
        Upload tous les fichiers trouvés.
        
        Args:
            local_dir: Répertoire local source
            remote_dir: Répertoire FTP cible
        
        Returns:
            Tuple[bool, str, Dict]: (succès, message, statistiques)
            Statistiques: {'uploaded': int, 'skipped': int, 'errors': int, 'total_files': int}
        """
        import time
        stats = {'uploaded': 0, 'skipped': 0, 'errors': 0, 'total_files': 0}
        
        try:
            if not self.is_connected():
                self.connect()
            
            # Normaliser les chemins
            local_dir = local_dir.rstrip('/\\')
            remote_dir = remote_dir.rstrip('/')
            
            # Changer de répertoire distant
            try:
                self._ftp.cwd(remote_dir)
            except ftplib.error_perm:
                # Créer le répertoire s'il n'existe pas
                self._create_remote_directory(remote_dir)
                self._ftp.cwd(remote_dir)
            
            # Parcourir le répertoire local
            for root, dirs, files in os.walk(local_dir):
                # Calculer le chemin relatif
                rel_path = os.path.relpath(root, local_dir)
                
                # Si ce n'est pas le répertoire racine, changer de répertoire distant
                if rel_path != '.':
                    try:
                        self._ftp.cwd(rel_path)
                    except ftplib.error_perm:
                        self._create_remote_directory(rel_path)
                        self._ftp.cwd(rel_path)
                
                # Traiter chaque fichier
                for filename in files:
                    stats['total_files'] += 1
                    local_file_path = os.path.join(root, filename)
                    
                    # Skip directories (already handled by os.walk)
                    if not os.path.isfile(local_file_path):
                        continue
                    
                    # Upload le fichier avec retry
                    for attempt in range(3):
                        try:
                            with open(local_file_path, 'rb') as f:
                                self._ftp.storbinary(f'STOR {filename}', f)
                            stats['uploaded'] += 1
                            break
                        except ftplib.all_errors as e:
                            if attempt < 2:
                                time.sleep(1)
                                try:
                                    self._ftp.quit()
                                except Exception:
                                    pass
                                try:
                                    self.connect()
                                    # Naviguer à nouveau
                                    if remote_dir:
                                        self._ftp.cwd(remote_dir)
                                    if rel_path != '.':
                                        self._ftp.cwd(rel_path)
                                except Exception:
                                    pass
                            else:
                                stats['errors'] += 1
                        except Exception as e:
                            stats['errors'] += 1
                            break
            
            success = stats['errors'] == 0
            message = f"Synchronisation terminée: {stats['uploaded']} fichiers uploadés, {stats['errors']} erreurs"
            
            return success, message, stats
            
        except Exception as e:
            return False, f"Erreur lors de la synchronisation: {e}", stats
        finally:
            try:
                self._ftp.cwd('/')
            except Exception:
                pass
            self.disconnect()
    
    def list_remote_directory_files(self, remote_path: str = "") -> Tuple[bool, str, List[str]]:
        """
        Liste tous les fichiers (pas les dossiers) dans un répertoire FTP.
        
        Args:
            remote_path: Chemin du répertoire à lister
        
        Returns:
            Tuple[bool, str, List[str]]: (succès, message, liste des fichiers)
        """
        files_list = []
        
        try:
            if not self.is_connected():
                self.connect()
            
            # Naviguer vers le répertoire
            if remote_path:
                try:
                    self._ftp.cwd(remote_path)
                except ftplib.error_perm as e:
                    return False, f"Impossible d'accéder au répertoire: {e}", files_list
            
            # Lister le contenu
            try:
                file_list = []
                self._ftp.retrlines('LIST', lambda x: file_list.append(x.decode('utf-8', errors='ignore') if isinstance(x, bytes) else x))
                
                # Filtrer uniquement les fichiers (pas les dossiers)
                for line in file_list:
                    line_stripped = line.strip()
                    if not line_stripped:
                        continue
                    # Format Unix: commence par '-' pour un fichier
                    if line_stripped.startswith('-'):
                        # Extraire le nom du fichier (dernière colonne)
                        parts = line_stripped.split()
                        if len(parts) >= 9:
                            filename = ' '.join(parts[8:])
                            files_list.append(filename)
                
                return True, f"Liste des fichiers dans {self._ftp.pwd()}", files_list
                
            except ftplib.all_errors as e:
                return False, f"Erreur lors de la liste: {e}", files_list
            
        except Exception as e:
            return False, f"Erreur inattendue: {e}", files_list
        finally:
            self.disconnect()
