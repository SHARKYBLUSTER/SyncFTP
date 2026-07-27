# Roadmap - FTP Server Manager

## 📌 Projet en cours

### Objectif
Améliorer la robustesse et les fonctionnalités de l'application de synchronisation FTP.

---

## ✅ Déjà implémenté

- [x] Affichage des logs du plus récent au plus ancien
- [x] Filtrage des logs API 200 depuis la vue INFO
- [x] Correction de l'erreur Windows lors de la suppression des logs
- [x] Gestion appropriée du FileHandler pour les logs

---

## 🚀 Prochaines Étapes (Prioritaires)

### 1. Verrouillage par Serveur FTP (Solution B)
**Priorité** : Moyenne  
**Complexité** : Moyenne  
**Description** : 
Actuellement, la Solution A (verrouillage séquentiel global) est implémentée. Pour améliorer les performances avec plusieurs serveurs FTP, implémenter un verrouillage par serveur plutôt que global.

**Bénéfices** :
- Permettre l'exécution parallèle des tâches sur des serveurs différents
- Meilleure utilisation des ressources
- Maintenir la sécurité et éviter les interférences

**Tâches** :
- [ ] Créer un dictionnaire de verrous par server_id
- [ ] Modifier `execute_sync_task()` pour utiliser le verrou spécifique au serveur
- [ ] Mettre à jour la gestion des états des tâches
- [ ] Tests de concurrence entre plusieurs serveurs

---

### 2. File d'attente avec Priorité (Solution C)
**Priorité** : Basse  
**Complexité** : Élevée  
**Description** : 
Implémenter une file d'attente explicite pour les tâches de synchronisation avec visualisation dans l'interface.

**Bénéfices** :
- Meilleure visibilité sur l'ordre d'exécution
- Possibilité de réorganiser les tâches
- Gestion plus fine des priorités

**Tâches** :
- [ ] Créer une structure de file d'attente
- [ ] Ajouter un champ `queue_position` aux tâches
- [ ] Implémenter une page de visualisation de la file
- [ ] Ajouter des boutons pour réorganiser les tâches
- [ ] Gérer les priorités (haute, normale, basse)

---

## 📝 Améliorations Futures

### Fonctionnalités
- [ ] Historique des synchronisations (journal des exécutions)
- [ ] Statistiques détaillées par serveur et par tâche
- [ ] Notifications par email en cas d'échec
- [ ] Synchronisation bidirectionnelle (optionnelle)
- [ ] Compression des fichiers avant upload
- [ ] Vérification de l'intégrité des fichiers (checksum)
- [ ] Support SFTP/SCP en plus de FTP

### Interface
- [ ] Dashboard avec graphiques (nombre de fichiers synchronisés par jour)
- [ ] Export des logs en fichier
- [ ] Configuration avancée par tâche (exclusions, filtres)
- [ ] Thème sombre/clair
- [ ] Internationalisation (i18n)

### Performance
- [ ] Synchronisation incrémentale (seulement les fichiers modifiés)
- [ ] Parallélisation des uploads de fichiers
- [ ] Cache des listes de fichiers distants
- [ ] Optimization de la mémoire pour les grands répertoires

### Sécurité
- [ ] Chiffrement des mots de passe dans le fichier JSON
- [ ] Authentification pour l'interface web
- [ ] HTTPS support
- [ ] Audit des accès

---

## 🔄 Version Actuelle

**Dernière version** : 1.0.0  
**Dernière mise à jour** : 27 Juillet 2026  
**Statut** : Solution A implémentée (verrouillage séquentiel + correction bug FTP)

---

## 📊 Légende

- ✅ **Terminé**
- 🚀 **En développement**
- 📝 **Planifié**
- ⏳ **En attente**
