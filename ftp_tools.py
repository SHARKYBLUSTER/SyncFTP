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
                        # Retourner au répertoire original avant de retourner False
                        try:
                            self._ftp.cwd(current_dir)
                        except Exception:
                            pass
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
    
    def _list_local_files(self, local_dir: str) -> List[str]:
        """
        Liste tous les fichiers dans un répertoire local de manière récursive.
        
        Args:
            local_dir: Répertoire local à explorer
            
        Returns:
            List[str]: Liste des chemins relatifs des fichiers
        """
        files_list = []
        local_dir = local_dir.rstrip('/\\')
        
        for root, dirs, files in os.walk(local_dir):
            rel_path = os.path.relpath(root, local_dir)
            for filename in files:
                local_file_path = os.path.join(root, filename)
                if os.path.isfile(local_file_path):
                    if rel_path == '.':
                        files_list.append(filename)
                    else:
                        files_list.append(os.path.join(rel_path, filename))
        
        return files_list

    def _list_remote_files_recursive(self, remote_dir: str = "") -> List[str]:
        """
        Liste tous les fichiers dans un répertoire FTP de manière récursive.
        
        Args:
            remote_dir: Répertoire FTP à explorer
            
        Returns:
            List[str]: Liste des chemins relatifs des fichiers
        """
        files_list = []
        
        if not self.is_connected():
            try:
                self.connect()
            except Exception:
                return files_list
        
        # Sauvegarder le répertoire courant
        try:
            original_dir = self._ftp.pwd()
        except Exception:
            return files_list
        
        # Naviguer vers le répertoire de départ
        if remote_dir:
            try:
                self._ftp.cwd(remote_dir)
            except ftplib.error_perm as e:
                return files_list
        
        try:
            # Fonction récursive pour explorer
            def explore_directory(current_path=""):
                try:
                    file_list = []
                    try:
                        self._ftp.retrlines('LIST', lambda x: file_list.append(
                            x.decode('utf-8', errors='ignore') if isinstance(x, bytes) else x
                        ))
                    except ftplib.all_errors:
                        # Essayer avec MLSD si LIST échoue
                        try:
                            self._ftp.retrlines('MLSD', lambda x: file_list.append(
                                x.decode('utf-8', errors='ignore') if isinstance(x, bytes) else x
                            ))
                        except:
                            pass
                    
                    for line in file_list:
                        line_stripped = line.strip()
                        if not line_stripped:
                            continue
                        
                        # Analyser la ligne LIST ou MLSD
                        # Format LIST: "-rw-r--r-- 1 user group size date time filename"
                        # Format MLSD: "Type=file;Size=123;Modify=date; filename"
                        if line_stripped.startswith('-') or 'Type=file' in line_stripped or line_stripped.startswith('d') or 'Type=dir' in line_stripped:
                            # Extraire le nom du fichier/répertoire
                            # Pour LIST format
                            parts = line_stripped.split()
                            if len(parts) >= 9 and (line_stripped.startswith('-') or line_stripped.startswith('d')):
                                item_name = ' '.join(parts[8:])
                            elif '; ' in line_stripped:  # Format MLSD
                                # Extraire après le dernier "; "
                                item_name = line_stripped.split('; ')[-1].strip()
                            elif line_stripped.startswith('d') or line_stripped.startswith('-'):
                                # Format LIST simplifié
                                item_name = parts[-1] if parts else line_stripped
                            else:
                                continue
                            
                            # Vérifier si c'est un répertoire ou un fichier
                            is_dir = line_stripped.startswith('d') or 'Type=dir' in line_stripped
                            is_file = line_stripped.startswith('-') or 'Type=file' in line_stripped
                            
                            if is_dir and item_name not in ('.', '..'):
                                # C'est un répertoire, explorer récursivement
                                try:
                                    self._ftp.cwd(item_name)
                                    explore_directory(current_path + '/' + item_name if current_path else item_name)
                                    self._ftp.cwd('..')
                                except ftplib.error_perm:
                                    # Ignorer les répertoires inaccessibles
                                    pass
                            elif is_file:
                                # C'est un fichier
                                if current_path:
                                    files_list.append(current_path + '/' + item_name)
                                else:
                                    files_list.append(item_name)
                            
                except Exception:
                    pass
            
            explore_directory()
            
        finally:
            # Toujours retourner au répertoire original
            try:
                self._ftp.cwd(original_dir)
            except Exception:
                try:
                    self._ftp.cwd('/')
                except Exception:
                    pass
        
        return files_list

    def _delete_remote_file(self, remote_path: str) -> Tuple[bool, str]:
        """
        Supprime un fichier du serveur FTP.
        
        Args:
            remote_path: Chemin du fichier distant à supprimer
            
        Returns:
            Tuple[bool, str]: (succès, message)
        """
        try:
            if not self.is_connected():
                self.connect()
            
            # Extraire le nom de fichier et le répertoire
            remote_dir = os.path.dirname(remote_path)
            filename = os.path.basename(remote_path)
            
            # Naviguer vers le répertoire du fichier
            if remote_dir:
                try:
                    self._ftp.cwd(remote_dir)
                except ftplib.error_perm:
                    return False, f"Impossible d'accéder au répertoire: {remote_dir}"
            
            # Supprimer le fichier
            self._ftp.delete(filename)
            return True, f"Fichier {filename} supprimé avec succès"
            
        except ftplib.all_errors as e:
            return False, f"Erreur FTP lors de la suppression: {e}"
        except Exception as e:
            return False, f"Erreur lors de la suppression: {e}"

    def sync_directory_to_ftp(self, local_dir: str, remote_dir: str, logger=None) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Synchronise un répertoire local vers un répertoire FTP.
        Upload les fichiers manquants et supprime les fichiers orphelins de la cible.
        
        Args:
            local_dir: Répertoire local source
            remote_dir: Répertoire FTP cible
            logger: Logger optionnel pour les logs
        
        Returns:
            Tuple[bool, str, Dict]: (succès, message, statistiques)
            Statistiques: {
                'uploaded': int, 'deleted': int, 'skipped': int, 'errors': int,
                'source_file_count': int, 'target_file_count': int,
                'uploaded_files': List[str], 'deleted_files': List[str]
            }
        """
        import time
        import logging
        
        # Utiliser le logger fourni ou un logger par défaut
        if logger is None:
            logger = logging.getLogger(__name__)
        
        stats = {
            'uploaded': 0, 'deleted': 0, 'skipped': 0, 'errors': 0,
            'source_file_count': 0, 'target_file_count': 0,
            'uploaded_files': [], 'deleted_files': []
        }
        
        try:
            if not self.is_connected():
                self.connect()
            
            # Normaliser les chemins
            local_dir = local_dir.rstrip('/\\')
            remote_dir = remote_dir.rstrip('/')
            
            # Se connecter au répertoire distant (créer si nécessaire)
            try:
                self._ftp.cwd(remote_dir)
            except ftplib.error_perm:
                self._create_remote_directory(remote_dir)
                self._ftp.cwd(remote_dir)
            
            # Lister les fichiers source et cible
            logger.info(f"Connexion au serveur FTP établie. Répertoire cible: {self._ftp.pwd()}")
            
            source_files = self._list_local_files(local_dir)
            stats['source_file_count'] = len(source_files)
            logger.info(f"Nombre de fichiers dans la source: {stats['source_file_count']}")
            
            remote_files = self._list_remote_files_recursive()
            stats['target_file_count'] = len(remote_files)
            logger.info(f"Nombre de fichiers dans le FTP cible: {stats['target_file_count']}")
            
            # Convertir les listes en sets pour comparaison
            source_set = set(source_files)
            remote_set = set(remote_files)
            
            # Fichiers à uploader (présents dans source mais pas dans remote)
            files_to_upload = source_set - remote_set
            # Fichiers à supprimer (présents dans remote mais pas dans source)
            files_to_delete = remote_set - source_set
            
            # D'abord, uploader tous les fichiers de la source (comme avant)
            for root, dirs, files in os.walk(local_dir):
                # Calculer le chemin relatif
                rel_path = os.path.relpath(root, local_dir)
                
                # Naviguer vers le répertoire distant correspondant
                if rel_path != '.':
                    # Normaliser le chemin pour FTP (remplacer les backslashes)
                    rel_path_normalized = rel_path.replace('\\', '/')
                    
                    try:
                        self._ftp.cwd(rel_path_normalized)
                    except ftplib.error_perm:
                        # Retourner au répertoire de base et naviguer étape par étape
                        try:
                            self._ftp.cwd(remote_dir)
                        except Exception:
                            pass
                        
                        # Créer et naviguer vers le répertoire étape par étape
                        parts = [p for p in rel_path_normalized.split('/') if p]
                        for part in parts:
                            try:
                                self._ftp.cwd(part)
                            except ftplib.error_perm:
                                try:
                                    self._ftp.mkd(part)
                                    self._ftp.cwd(part)
                                except ftplib.error_perm:
                                    # Si on ne peut pas créer, essayer de continuer
                                    pass
                
                # Traiter chaque fichier
                for filename in files:
                    local_file_path = os.path.join(root, filename)
                    
                    # Skip directories (already handled by os.walk)
                    if not os.path.isfile(local_file_path):
                        continue
                    
                    # Chemin relatif du fichier
                    if rel_path == '.':
                        relative_path = filename
                    else:
                        relative_path = os.path.join(rel_path, filename)
                    
                    # Upload le fichier avec retry (UNIQUEMENT s'il est dans files_to_upload)
                    if relative_path in files_to_upload:
                        success = False
                        for attempt in range(3):
                            try:
                                with open(local_file_path, 'rb') as f:
                                    self._ftp.storbinary(f'STOR {filename}', f)
                                success = True
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
                                        # Naviguer à nouveau vers le répertoire de base
                                        if remote_dir:
                                            self._ftp.cwd(remote_dir)
                                        # Naviguer vers rel_path étape par étape
                                        if rel_path != '.':
                                            rel_path_normalized = rel_path.replace('\\', '/')
                                            parts = [p for p in rel_path_normalized.split('/') if p]
                                            for part in parts:
                                                try:
                                                    self._ftp.cwd(part)
                                                except ftplib.error_perm:
                                                    try:
                                                        self._ftp.mkd(part)
                                                        self._ftp.cwd(part)
                                                    except ftplib.error_perm:
                                                        pass
                                    except Exception:
                                        pass
                                else:
                                    stats['errors'] += 1
                            except Exception as e:
                                stats['errors'] += 1
                                break
                        
                        if success:
                            stats['uploaded'] += 1
                            stats['uploaded_files'].append(relative_path)
                            logger.info(f"Fichier écrit sur le FTP: {relative_path}")
                    else:
                        stats['skipped'] += 1
            
            # Retourner au répertoire de base pour la suppression
            try:
                self._ftp.cwd(remote_dir)
            except Exception:
                pass
            
            # Ensuite, supprimer les fichiers orphelins
            for relative_path in sorted(files_to_delete):
                try:
                    # Extraire le répertoire et le nom de fichier
                    file_dir = os.path.dirname(relative_path)
                    filename = os.path.basename(relative_path)
                    
                    # Naviguer vers le répertoire distant
                    if file_dir:
                        try:
                            self._ftp.cwd(file_dir)
                        except ftplib.error_perm:
                            # Ne pas supprimer si on ne peut pas accéder au répertoire
                            stats['errors'] += 1
                            logger.error(f"Impossible d'accéder au répertoire pour suppression: {relative_path}")
                            continue
                    
                    # Supprimer le fichier
                    self._ftp.delete(filename)
                    stats['deleted'] += 1
                    stats['deleted_files'].append(relative_path)
                    logger.warning(f"Fichier supprimé du FTP: {relative_path}")
                    
                    # Retourner au répertoire de base
                    try:
                        self._ftp.cwd(remote_dir)
                    except Exception:
                        pass
                        
                except ftplib.all_errors as e:
                    stats['errors'] += 1
                    logger.error(f"Erreur lors de la suppression de {relative_path}: {e}")
                except Exception as e:
                    stats['errors'] += 1
                    logger.error(f"Erreur inattendue lors de la suppression de {relative_path}: {e}")
            
            success = stats['errors'] == 0
            message = (f"Synchronisation terminée: {stats['uploaded']} fichiers uploadés, "
                      f"{stats['deleted']} fichiers supprimés, {stats['errors']} erreurs")
            
            logger.info(message)
            
            return success, message, stats
            
        except Exception as e:
            logger.error(f"Erreur lors de la synchronisation: {e}")
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
