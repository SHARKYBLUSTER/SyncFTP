# Optimisations de Performance pour SyncFTP

*Date: 27 juillet 2026*
*Analyse basée sur: app.log avec logs DEBUG activés*

---

## 📊 Sommaire

- [Problèmes identifiés](#-problèmes-identifiés)
- [Solutions proposées](#-solutions-proposées)
- [Recommandations par priorité](#-recommandations-par-priorité)
- [Métriques à surveiller](#-métriques-à-surveiller)

---

## 🔍 Problèmes identifiés

### 1. Reconnexions FTP extrêmement lentes (PROBLÈME CRITIQUE)

**Preuves dans les logs:**
```
[2026-07-27 23:40:10,899] DEBUG: [PERF] Reconnexion FTP tentative 1 terminée en 3193ms
[2026-07-27 23:42:13,781] DEBUG: [PERF] Reconnexion FTP tentative 2 terminée en 9983ms
[2026-07-27 23:45:23,924] DEBUG: [PERF] Reconnexion FTP tentative 2 terminée en 22151ms  ← 22 SECONDES !
[2026-07-27 23:46:14,688] DEBUG: [PERF] Reconnexion FTP tentative 1 terminée en 19731ms  ← 20 SECONDES !
```

**Fichier concerné:** `ftp_tools.py` lignes 737-746

**Code problématique:**
```python
self.connect()  # Peut prendre 20-30 secondes avec le timeout par défaut
```

**Impact:**
- Chaque échec d'upload déclenche une reconnexion complète
- Avec 4,886 fichiers à synchroniser, même 1% d'erreurs = 49 reconnexions
- Temps perdu: 8-17 minutes sur une synchronisation complète

---

### 2. Vitesse d'upload très faible

**Preuves dans les logs:**
```
[2026-07-27 23:38:32,079] DEBUG: [PERF] Début phase d'upload, 4886 fichiers à uploader
[2026-07-27 23:38:32,079] DEBUG: [PERF] Progression 1/4886 (0.0%), vitesse: 0.15 fichiers/s
[2026-07-27 23:46:37,140] DEBUG: [PERF] Progression 146/4886 (3.0%), vitesse: 0.30 fichiers/s
```

**Analyse:**
- Vitesse moyenne: 0.15-0.30 fichiers/seconde
- À cette vitesse, 4,886 fichiers prennent: **4.3 heures** (sans compter les reconnexions)
- Avec les reconnexions: peut dépasser 6-8 heures

---

### 3. Nombre de fichiers énorme

**Données des logs:**
- **Source locale:** 19,510 fichiers (listage en 173ms ✅)
- **Cible FTP:** 14,724 fichiers (listage en 636ms ✅)
- **À synchroniser:** 4,886 fichiers

**Fichier concerné:** `ftp_tools.py` ligne 5161-5166

---

### 4. Uploads séquentiels (pas de parallélisme)

**Problème:** Chaque fichier est uploadé un par un dans une boucle `for` (ligne 695-720).

**Code actuel:**
```python
for root, dirs, files in os.walk(local_dir, onerror=handle_walk_error):
    for filename in files:
        # Upload un fichier à la fois...
```

**Impact:** Pas d'utilisation des ressources réseau et CPU disponibles.

---

### 5. Absence de cache des fichiers déjà synchronisés

**Problème:** À chaque exécution, reliste TOUS les fichiers (19k locaux + 14k distants).

**Impact:** Temps perdu en listage répétitif.

---

---

## 🎯 Solutions proposées

---

### Solution #1: Réduire le timeout de reconnexion (IMPACT ÉLEVÉ)

**Fichier:** `ftp_tools.py`

**Modifications:**

1. **Ligne 25:** Réduire le timeout par défaut
```python
@dataclass
class FTPConfig:
    host: str
    port: int = 21
    username: str = "anonymous"
    password: str = ""
    use_ssl: bool = False
    timeout: int = 10  # Changé de 30 à 10
```

2. **Lignes 737-746:** Forcer un timeout court pendant les reconnexions
```python
# Avant:
reconnect_start = time.time()
self.connect()

# Après:
old_timeout = self.config.timeout
self.config.timeout = 10  # Timeout court pour les reconnexions
reconnect_start = time.time()
self.connect()
self.config.timeout = old_timeout  # Restaurer
```

**Gain estimé:** Réduction de 70-90% du temps perdu en reconnexions.

**Complexité:** ⭐⭐ (Facile)

---

### Solution #2: Implémenter des uploads parallèles (IMPACT TRÈS ÉLEVÉ)

**Fichier:** `ftp_tools.py`

**Modifications:**

1. **Ajouter l'import au début du fichier:**
```python
from concurrent.futures import ThreadPoolExecutor, as_completed
```

2. **Créer une méthode d'upload simple:**
```python
def _upload_single_file(self, local_path: str, remote_path: str, remote_dir: str) -> Tuple[bool, str, int]:
    """Upload un seul fichier, retourne (succès, message, taille)"""
    file_size = os.path.getsize(local_path)
    for attempt in range(3):
        try:
            # Créer le répertoire parent si nécessaire
            file_dir = os.path.dirname(remote_path)
            if file_dir:
                self._create_remote_directory(file_dir)
            
            with open(local_path, 'rb') as f:
                self._ftp.storbinary(f'STOR {remote_path}', f)
            return True, f"Fichier {remote_path} uploadé", file_size
        except ftplib.all_errors as e:
            if attempt < 2:
                time.sleep(1)
                try:
                    self._ftp.quit()
                except Exception:
                    pass
                try:
                    old_timeout = self.config.timeout
                    self.config.timeout = 10
                    self.connect()
                    if remote_dir:
                        try:
                            self._ftp.cwd(remote_dir)
                        except Exception:
                            pass
                    self.config.timeout = old_timeout
                except Exception:
                    pass
            else:
                return False, f"Erreur upload {remote_path}: {e}", 0
    return False, f"Échec après 3 tentatives: {remote_path}", 0
```

3. **Remplacer la boucle d'upload (lignes 688-720) par:**
```python
# Configuration du parallélisme
max_workers = 5  # 5 uploads simultanés

upload_phase_start = time.time()
logger.debug(f"[PERF] Début phase d'upload, {len(files_to_upload)} fichiers à uploader")

# Préparer les tâches d'upload
upload_tasks = []
for root, dirs, files in os.walk(local_dir, onerror=handle_walk_error):
    rel_path = os.path.relpath(root, local_dir)
    for filename in files:
        local_file_path = os.path.join(root, filename)
        if not os.path.isfile(local_file_path):
            continue
        if rel_path == '.':
            relative_path = filename
        else:
            relative_path = os.path.join(rel_path, filename).replace('\\', '/')
        if relative_path in files_to_upload:
            upload_tasks.append((local_file_path, relative_path))

# Exécuter en parallèle
with ThreadPoolExecutor(max_workers=max_workers) as executor:
    futures = []
    for local_path, relative_path in upload_tasks:
        futures.append(executor.submit(
            self._upload_single_file, 
            local_path, 
            relative_path, 
            remote_dir
        ))
    
    for future in as_completed(futures):
        success, message, file_size = future.result()
        if success:
            stats['uploaded'] += 1
            stats['uploaded_files'].append(relative_path)
            stats['total_bytes_transferred'] += file_size
            stats['files_remaining'] = stats['total_files_to_process'] - stats['uploaded']
            
            current_time = time.time()
            elapsed_time = current_time - transfer_start_time
            if elapsed_time > 0:
                stats['average_speed_bps'] = stats['total_bytes_transferred'] / elapsed_time
                stats['average_speed_fps'] = stats['uploaded'] / elapsed_time
                if stats['average_speed_fps'] > 0 and stats['files_remaining'] > 0:
                    remaining_time = stats['files_remaining'] / stats['average_speed_fps']
                    estimated_end = datetime.now() + timedelta(seconds=remaining_time)
                    stats['estimated_end_time'] = estimated_end.strftime('%Y-%m-%d %H:%M:%S')
            
            logger.info(f"Fichier écrit sur le FTP: {relative_path}")
        else:
            stats['errors'] += 1
            logger.error(message)
        
        # Callback de progression
        if progress_callback:
            try:
                import copy
                progress_callback(copy.deepcopy(stats))
            except Exception:
                pass
```

**Gain estimé:** Multiplication de la vitesse par 3-5x (de 0.3 à 1.5 fichiers/s).

**Complexité:** ⭐⭐⭐ (Moyenne)

**Note:** Cette solution nécessite une connexion FTP stable. Si le serveur FTP limite le nombre de connexions simultanées, réduire `max_workers`.

---

### Solution #3: Gestion intelligente des erreurs (IMPACT MOYEN)

**Fichier:** `ftp_tools.py` lignes 730-750

**Modifications:**
```python
except ftplib.all_errors as e:
    error_str = str(e).lower()
    
    # Ne pas reconnecter pour les timeouts - simplement réessayer
    if 'timeout' in error_str or 'timed out' in error_str:
        if attempt < 2:
            wait_time = 2 ** attempt  # Backoff exponentiel: 2s, 4s
            logger.debug(f"[PERF] Timeout sur {relative_path}, attente {wait_time}s avant retry")
            time.sleep(wait_time)
            continue  # Réessayer sans reconnexion
    
    # Pour les autres erreurs (421, 500, etc.), reconnecter
    if attempt < 2:
        time.sleep(1)
        try:
            self._ftp.quit()
        except Exception:
            pass
        try:
            old_timeout = self.config.timeout
            self.config.timeout = 10
            reconnect_start = time.time()
            self.connect()
            if remote_dir:
                try:
                    self._ftp.cwd(remote_dir)
                except Exception:
                    pass
            self.config.timeout = old_timeout
            logger.debug(f"[PERF] Reconnexion FTP tentative {attempt + 1} terminée en {(time.time() - reconnect_start)*1000:.0f}ms")
        except Exception:
            pass
```

**Gain estimé:** Réduction de 30-50% des reconnexions inutiles.

**Complexité:** ⭐⭐ (Facile)

---

### Solution #4: Cache des fichiers déjà synchronisés (IMPACT ÉLEVÉ)

**Fichier:** `ftp_tools.py` dans `sync_directory_to_ftp`

**Modifications:**

1. **Ajouter une classe de cache:**
```python
class SyncCache:
    """Cache pour éviter de relister tous les fichiers à chaque synchronisation"""
    
    CACHE_FILE = ".sync_cache.json"
    
    def __init__(self):
        self.cache = self._load_cache()
    
    def _load_cache(self):
        if os.path.exists(self.CACHE_FILE):
            try:
                with open(self.CACHE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}
    
    def save_cache(self):
        try:
            with open(self.CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=2)
        except Exception:
            pass
    
    def get_file_info(self, relative_path: str) -> dict:
        """Retourne les infos du fichier en cache ou None"""
        return self.cache.get(relative_path)
    
    def update_file_info(self, relative_path: str, file_size: int, mtime: float, hash_value: str = None):
        """Met à jour les infos du fichier en cache"""
        self.cache[relative_path] = {
            'size': file_size,
            'mtime': mtime,
            'hash': hash_value,
            'last_sync': datetime.now().isoformat()
        }
        self.save_cache()
    
    def remove_file_info(self, relative_path: str):
        """Supprime un fichier du cache"""
        if relative_path in self.cache:
            del self.cache[relative_path]
            self.save_cache()
```

2. **Utiliser le cache dans `sync_directory_to_ftp`:**
```python
def sync_directory_to_ftp(self, local_dir: str, remote_dir: str, logger=None, 
                           exclude_patterns: str = '', progress_callback=None, 
                           use_cache: bool = True) -> Tuple[bool, str, Dict[str, Any]]:
    
    # Initialiser le cache
    cache = SyncCache() if use_cache else None
    
    # ... code existant ...
    
    # Après le listage local, filtrer avec le cache
    if cache and use_cache:
        filtered_source_files = []
        for filepath in source_files:
            relative_path = os.path.relpath(filepath, local_dir).replace('\\', '/')
            cached_info = cache.get_file_info(relative_path)
            
            if cached_info:
                # Vérifier si le fichier a changé
                current_size = os.path.getsize(filepath)
                current_mtime = os.path.getmtime(filepath)
                if (cached_info['size'] == current_size and 
                    cached_info['mtime'] == current_mtime):
                    stats['skipped'] += 1
                    logger.debug(f"[CACHE] Fichier inchangé: {relative_path}")
                    continue
            
            filtered_source_files.append(filepath)
        
        source_files = filtered_source_files
    
    # ... reste du code ...
    
    # Après un upload réussi, mettre à jour le cache
    if success and cache and use_cache:
        cache.update_file_info(
            relative_path,
            file_size,
            os.path.getmtime(local_file_path)
        )
```

**Gain estimé:** Réduction de 80-95% du temps de listage pour les runs subséquents.

**Complexité:** ⭐⭐⭐ (Moyenne)

**Note:** Cette solution nécessite de gérer les cas où le cache devient obsolète (fichiers modifiés, suppressions, etc.).

---

### Solution #5: Batch upload pour les petits fichiers (IMPACT MOYEN)

**Fichier:** `ftp_tools.py`

**Idée:** Regrouper les petits fichiers (<100KB) dans une archive tar et les uploader en une seule fois.

**Modifications:**
```python
import tarfile
import tempfile
import io

def _batch_upload_small_files(self, file_list: List[Tuple[str, str]], remote_dir: str) -> Tuple[int, int]:
    """
    Upload plusieurs petits fichiers sous forme d'une archive tar.
    Retourne (nombre de fichiers, taille totale)
    """
    if not file_list:
        return 0, 0
    
    # Créer une archive tar en mémoire
    tar_buffer = io.BytesIO()
    with tarfile.open(filepath=remote_dir + '/batch.tar', mode='w:gz', fileobj=tar_buffer) as tar:
        for local_path, relative_path in file_list:
            tar.add(local_path, arcname=relative_path)
    
    # Upload l'archive
    tar_buffer.seek(0)
    with io.BytesIO(tar_buffer.read()) as data:
        self._ftp.storbinary(f'STOR {remote_dir}/batch.tar', data)
    
    # Extraire à distance (si le serveur le permet)
    # Ou extraire localement et uploader individuellement
    return len(file_list), tar_buffer.tell()
```

**Gain estimé:** Réduction de 40-60% du temps pour les petits fichiers (moins d'overhead de connexion).

**Complexité:** ⭐⭐⭐⭐ (Élevée - nécessite un serveur FTP avec support tar)

---

### Solution #6: Forcer un timeout raisonnable dans la configuration

**Fichier:** `app.py` ligne 426-433

**Modifications:**
```python
# Avant:
config = FTPConfig(
    host=server['host'],
    port=int(server.get('port', 21)),
    username=server.get('username', 'anonymous'),
    password=server.get('password', ''),
    use_ssl=server.get('use_ssl', False),
    timeout=int(server.get('timeout', 30))
)

# Après:
config = FTPConfig(
    host=server['host'],
    port=int(server.get('port', 21)),
    username=server.get('username', 'anonymous'),
    password=server.get('password', ''),
    use_ssl=server.get('use_ssl', False),
    timeout=10  # Forcer 10 secondes au lieu de 30
)
```

**Gain estimé:** Réduction de 50% du temps de reconnexion.

**Complexité:** ⭐ (Très facile)

---

---

## 📋 Recommandations par priorité

---

### Phase 1: Corrections rapides (1 jour) - Impact immédiat

| # | Solution | Gain | Complexité | Fichiers à modifier |
|---|----------|------|------------|-------------------|
| 1 | Réduire timeout de reconnexion | -70-90% temps perdu | ⭐⭐ | `ftp_tools.py` (2 endroits) |
| 6 | Forcer timeout=10 dans config | -50% reconnexions | ⭐ | `app.py` |
| 3 | Gestion intelligente des erreurs | -30-50% reconnexions | ⭐⭐ | `ftp_tools.py` |

**Résultat attendu:** Réduction de 50-70% du temps total de synchronisation.

---

### Phase 2: Optimisations moyennes (2-3 jours) - Impact élevé

| # | Solution | Gain | Complexité | Fichiers à modifier |
|---|----------|------|------------|-------------------|
| 2 | Uploads parallèles | 3-5x vitesse | ⭐⭐⭐ | `ftp_tools.py` |
| 5 | Cache des fichiers | -80-95% listage | ⭐⭐⭐ | `ftp_tools.py` |

**Résultat attendu:** Réduction de 70-85% du temps total de synchronisation.

---

### Phase 3: Optimisations avancées (Optionnelle)

| # | Solution | Gain | Complexité | Fichiers à modifier |
|---|----------|------|------------|-------------------|
| 4 | Batch upload petits fichiers | -40-60% petits fichiers | ⭐⭐⭐⭐ | `ftp_tools.py` |

---

---

## 📈 Métriques à surveiller

Avec les logs `[PERF]` maintenant activés, surveillez ces indicateurs après chaque correction :

### Métriques clés dans les logs:

1. **Temps de reconnexion:**
   ```
   [PERF] Reconnexion FTP tentative X terminée en Yms
   ```
   → **Objectif:** Y < 5000ms (5 secondes)

2. **Vitesse d'upload:**
   ```
   [PERF] Tâche XXX: Progression A/B (X%), vitesse: Y fichiers/s
   ```
   → **Objectif:** Y > 1.0 fichiers/s

3. **Phase d'upload:**
   ```
   [PERF] Phase d'upload terminée en Xs, Y fichiers uploadés
   ```
   → **Objectif:** X proportionnel à Y (ex: 4886 fichiers en ~1-2 heures au lieu de 6-8 heures)

4. **Temps de listage:**
   ```
   [PERF] Listage local terminé: X fichiers trouvés en Yms
   [PERF] Listage FTP terminé: X fichiers trouvés en Yms
   ```
   → **Objectif:** Y < 1000ms pour chaque listage

---

---

## 🛠 Actions immédiates recommandées

### Pour résoudre 80% du problème dès aujourd'hui:

1. **Appliquer la Solution #6 (app.py):**
   ```python
   timeout=10  # Lignes 426-433
   ```

2. **Appliquer la Solution #1 (ftp_tools.py):**
   - Ligne 25: `timeout: int = 10`
   - Lignes 737-746: Forcer timeout court pendant les reconnexions

3. **Redémarrer l'application** et re-sauvegarder la config via `/config`

4. **Surveiller les logs** pour vérifier l'amélioration

---

---

## 📝 Historique des changements

- **27/07/2026:** Analyse initiale basée sur app.log avec logs DEBUG activés
- **27/07/2026:** Fix du bug de logging (apply_log_level_from_config) - déjà implémenté
- **27/07/2026:** Documentation des optimisations de performance

---

## 📚 Références

- **Fichier de logs:** `app.log` (5731 lignes analysées)
- **Configuration:** `config.json` (debug_logging_enabled: true)
- **Code source:** `ftp_tools.py` et `app.py`

---

*Document généré par Mistral Vibe - Analyse de performance SyncFTP*
