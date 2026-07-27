"""
FTP Tools - Module réutilisable pour gérer les connexions FTP
=============================================================

Ce module fournit des outils pour tester et gérer les connexions FTP.
Il peut être importé et utilisé par l'application principale SyncFTP.
"""

import ftplib
import os
import io
import fnmatch
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


def should_exclude_file(filename: str, exclude_patterns: str) -> bool:
    """
    Vérifie si un fichier doit être exclu de la synchronisation.
    
    Args:
        filename: Nom du fichier à vérifier
        exclude_patterns: Chaîne de patterns séparés par des virgules (ex: "*.tmp,*.part,Thumbs.db")
    
    Returns:
        bool: True si le fichier doit être exclu, False sinon
    """
    if not exclude_patterns:
        return False
    
    patterns = [p.strip() for p in exclude_patterns.split(',') if p.strip()]
    for pattern in patterns:
        if fnmatch.fnmatch(filename, pattern):
            return True
        # También verificar si el patrón coincide con la parte final del nombre (para casos como .tmp)
        if pattern.startswith('*') and filename.endswith(pattern[1:]):
            return True
    return False


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
    
    def _get_local_files_with_sizes(self, local_dir: str) -> Dict[str, int]:
        """
        Liste tous les fichiers dans un répertoire local avec leurs tailles.
        
        Args:
            local_dir: Répertoire local à explorer
            
        Returns:
            Dict[str, int]: Dictionnaire {chemin_relatif: taille_en_octets}
        """
        files_dict = {}
        local_dir = local_dir.rstrip('/\\')
        
        for root, dirs, files in os.walk(local_dir):
            rel_path = os.path.relpath(root, local_dir)
            for filename in files:
                local_file_path = os.path.join(root, filename)
                if os.path.isfile(local_file_path):
                    # Normaliser le chemin avec des / pour la comparaison
                    if rel_path == '.':
                        relative_path = filename
                    else:
                        relative_path = os.path.join(rel_path, filename).replace('\\', '/')
                    files_dict[relative_path] = os.path.getsize(local_file_path)
        
        return files_dict

    def _list_remote_files_recursive(self, remote_dir: str = "") -> Dict[str, int]:
        """
        Liste tous les fichiers dans un répertoire FTP de manière récursive avec leurs tailles.
        
        Args:
            remote_dir: Répertoire FTP à explorer
            
        Returns:
            Dict[str, int]: Dictionnaire {chemin_relatif: taille_en_octets}
        """
        files_dict = {}
        
        if not self.is_connected():
            try:
                self.connect()
            except Exception:
                return files_dict
        
        # Sauvegarder le répertoire courant
        try:
            original_dir = self._ftp.pwd()
        except Exception:
            return files_dict
        
        # Naviguer vers le répertoire de départ
        if remote_dir:
            try:
                self._ftp.cwd(remote_dir)
            except ftplib.error_perm as e:
                return files_dict
        
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
                        file_size = 0
                        item_name = ""
                        is_dir = line_stripped.startswith('d') or 'Type=dir' in line_stripped
                        is_file = line_stripped.startswith('-') or 'Type=file' in line_stripped
                        
                        # Extraire le nom et la taille
                        if line_stripped.startswith('-') or line_stripped.startswith('d'):
                            # Format LIST standard
                            parts = line_stripped.split()
                            if len(parts) >= 9:
                                item_name = ' '.join(parts[8:])
                                if is_file and len(parts) >= 5:
                                    try:
                                        file_size = int(parts[4])
                                    except (ValueError, IndexError):
                                        file_size = 0
                        elif '; ' in line_stripped:  # Format MLSD
                            # Extraire la taille
                            for part in line_stripped.split(';'):
                                part = part.strip()
                                if part.startswith('Size='):
                                    try:
                                        file_size = int(part.split('=')[1])
                                    except (ValueError, IndexError):
                                        file_size = 0
                            # Extraire le nom (dernière partie après "; ")
                            item_name = line_stripped.split('; ')[-1].strip()
                        
                        if not item_name:
                            continue
                        
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
                            # C'est un fichier - enregistrer avec sa taille
                            if current_path:
                                full_path = current_path + '/' + item_name
                            else:
                                full_path = item_name
                            files_dict[full_path] = file_size
                
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
        
        return files_dict

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

    def sync_directory_to_ftp(self, local_dir: str, remote_dir: str, logger=None, exclude_patterns: str = '') -> Tuple[bool, str, Dict[str, Any]]:
        """
        Synchronise un répertoire local vers un répertoire FTP.
        Upload les fichiers manquants et supprime les fichiers orphelins de la cible.
        
        Args:
            local_dir: Répertoire local source
            remote_dir: Répertoire FTP cible
            logger: Logger optionnel pour les logs
            exclude_patterns: Patterns de fichiers à exclure (séparés par des virgules, ex: "*.tmp,*.part")
        
        Returns:
            Tuple[bool, str, Dict]: (succès, message, statistiques)
            Statistiques: {
                'uploaded': int, 'deleted': int, 'skipped': int, 'errors': int,
                'source_file_count': int, 'target_file_count': int,
                'uploaded_files': List[str], 'deleted_files': List[str],
                'excluded': int, 'excluded_files': List[str]
            }
        """
        import time
        import logging
        
        # Utiliser le logger fourni ou un logger par défaut
        if logger is None:
            logger = logging.getLogger(__name__)
        
        stats = {
            'uploaded': 0, 'deleted': 0, 'skipped': 0, 'errors': 0,
            'excluded': 0,
            'source_file_count': 0, 'target_file_count': 0,
            'uploaded_files': [], 'deleted_files': [], 'excluded_files': []
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
            
            # Filtrer les fichiers exclus
            if exclude_patterns:
                filtered_source_files = []
                for filepath in source_files:
                    filename = os.path.basename(filepath)
                    if not should_exclude_file(filename, exclude_patterns):
                        filtered_source_files.append(filepath)
                    else:
                        stats['excluded'] += 1
                        stats['excluded_files'].append(filepath)
                        logger.info(f"Fichier exclu de la synchronisation: {filepath}")
                source_files = filtered_source_files
            
            stats['source_file_count'] = len(source_files)
            logger.info(f"Nombre de fichiers dans la source: {stats['source_file_count']}")
            
            remote_files = self._list_remote_files_recursive(remote_dir)
            stats['target_file_count'] = len(remote_files)
            logger.info(f"Nombre de fichiers dans le FTP cible: {stats['target_file_count']}")
            
            # Convertir en sets pour comparaison
            source_set = set(source_files)
            remote_set = set(remote_files.keys())
            
            # Fichiers à uploader : présents dans source mais pas dans remote
            files_to_upload = source_set - remote_set
            
            # Fichiers à supprimer (présents dans remote mais pas dans source)
            files_to_delete = remote_set - source_set
            
            # D'abord, uploader tous les fichiers de la source (comme avant)
            def handle_walk_error(error):
                logger.warning(f"Accès refusé à un fichier/dossier lors du parcours: {error}")
            
            for root, dirs, files in os.walk(local_dir, onerror=handle_walk_error):
                # Calculer le chemin relatif
                rel_path = os.path.relpath(root, local_dir)
                
                # Traiter chaque fichier
                for filename in files:
                    local_file_path = os.path.join(root, filename)
                    
                    # Skip directories (already handled by os.walk)
                    if not os.path.isfile(local_file_path):
                        continue
                    
                    # Chemin relatif du fichier (normalisé avec /)
                    if rel_path == '.':
                        relative_path = filename
                    else:
                        relative_path = os.path.join(rel_path, filename).replace('\\', '/')
                    
                    # Upload le fichier avec retry (UNIQUEMENT s'il est dans files_to_upload)
                    if relative_path in files_to_upload:
                        # Créer le répertoire parent si nécessaire
                        file_dir = os.path.dirname(relative_path)
                        if file_dir:
                            self._create_remote_directory(file_dir)
                        
                        success = False
                        for attempt in range(3):
                            try:
                                with open(local_file_path, 'rb') as f:
                                    self._ftp.storbinary(f'STOR {relative_path}', f)
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
                                        # Retourner au répertoire de base
                                        if remote_dir:
                                            try:
                                                self._ftp.cwd(remote_dir)
                                            except Exception:
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
                    # Supprimer directement avec le chemin relatif complet
                    self._ftp.delete(relative_path)
                    stats['deleted'] += 1
                    stats['deleted_files'].append(relative_path)
                    logger.warning(f"Fichier supprimé du FTP: {relative_path}")

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
    
    def check_and_delete_corrupted_files(self, tasks: List[Dict], servers: List[Dict], logger=None) -> Dict[str, Any]:
        """
        Vérifie et supprime les fichiers corrompus (taille différente) sur les serveurs FTP cibles.
        Cette fonction se lance uniquement quand toutes les tâches de synchronisation sont terminées.
        
        Args:
            tasks: Liste des tâches de synchronisation
            servers: Liste des serveurs FTP
            logger: Logger optionnel pour les logs
        
        Returns:
            Dict: Statistiques des fichiers corrompus trouvés et supprimés
        """
        import logging
        import os
        
        if logger is None:
            logger = logging.getLogger(__name__)
        
        stats = {
            'total_checked': 0,
            'corrupted_found': 0,
            'deleted': 0,
            'errors': 0,
            'details': []
        }
        
        # Vérifier si toutes les tâches sont terminées (pas en cours d'exécution)
        all_tasks_completed = all(
            task.get('status') in ['completed', 'idle', 'failed'] 
            for task in tasks
        )
        
        if not all_tasks_completed:
            logger.info("Vérification des fichiers corrompus reportée: des tâches de synchronisation sont en cours")
            stats['message'] = "Des tâches de synchronisation sont encore en cours, vérification reportée"
            return stats
        
        logger.info("Début de la vérification des fichiers corrompus...")
        
        # Pour chaque tâche activée, vérifier les fichiers corrompus
        for task in tasks:
            if not task.get('enabled', True):
                continue
            
            try:
                server_id = task.get('server_id')
                source_dir = task.get('source_directory', '')
                target_dir = task.get('target_directory', '')
                
                if not server_id or not source_dir or not target_dir:
                    continue
                
                # Trouver le serveur correspondant
                server = next((s for s in servers if s['id'] == server_id), None)
                if not server:
                    logger.warning(f"Serveur non trouvé pour la tâche {task.get('name', 'Inconnue')}")
                    continue
                
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
                
                logger.info(f"Vérification des fichiers corrompus pour la tâche: {task.get('name', 'Inconnue')}")
                logger.info(f"Source: {source_dir}, Cible: {target_dir}")
                
                # Se connecter
                if not connector.connect():
                    logger.error(f"Impossible de se connecter au serveur pour la tâche {task.get('name', 'Inconnue')}")
                    stats['errors'] += 1
                    continue
                
                # Naviguer vers le répertoire cible
                try:
                    connector._ftp.cwd(target_dir)
                except ftplib.error_perm as e:
                    logger.error(f"Impossible d'accéder au répertoire cible {target_dir}: {e}")
                    connector.disconnect()
                    stats['errors'] += 1
                    continue
                
                # Lister les fichiers source avec leurs tailles
                source_files_dict = connector._get_local_files_with_sizes(source_dir)
                stats['total_checked'] += len(source_files_dict)
                
                # Lister les fichiers distants avec leurs tailles
                remote_files_dict = connector._list_remote_files_recursive(target_dir)
                
                # Trouver les fichiers corrompus (présents dans les deux mais avec des tailles différentes)
                corrupted_files = []
                for file_path, local_size in source_files_dict.items():
                    remote_size = remote_files_dict.get(file_path)
                    if file_path in remote_files_dict and local_size != remote_size:
                        corrupted_files.append(file_path)
                
                logger.info(f"Tâche {task.get('name', 'Inconnue')}: {len(corrupted_files)} fichiers corrompus trouvés")
                stats['corrupted_found'] += len(corrupted_files)
                
                # Supprimer les fichiers corrompus
                # On reste dans target_dir et on supprime directement avec le chemin relatif
                for file_path in corrupted_files:
                    try:
                        connector._ftp.delete(file_path)
                        stats['deleted'] += 1
                        stats['details'].append(file_path)
                        logger.warning(f"Fichier corrompu supprimé du FTP: {file_path} (taille source: {source_files_dict[file_path]}, taille FTP: {remote_files_dict[file_path]})")
                    except ftplib.all_errors as e:
                        stats['errors'] += 1
                        logger.error(f"Erreur lors de la suppression du fichier corrompu {file_path}: {e}")
                    except Exception as e:
                        stats['errors'] += 1
                        logger.error(f"Erreur inattendue lors de la suppression de {file_path}: {e}")
                
                connector.disconnect()
                
            except Exception as e:
                logger.error(f"Erreur lors de la vérification pour la tâche {task.get('id', 'inconnue')}: {e}")
                stats['errors'] += 1
        
        stats['message'] = f"Vérification terminée: {stats['corrupted_found']} fichiers corrompus trouvés, {stats['deleted']} supprimés, {stats['errors']} erreurs"
        logger.info(stats['message'])
        
        return stats
