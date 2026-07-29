# SyncFTP - Corrections UI à Implémenter

> **Document de référence** pour corriger les problèmes de la refonte UI (Phase 1-5)
> **Date** : 29 juillet 2026
> **Version** : 1.0.0
> **Statut** : Partiellement implémenté (Priorité 1 et 2 terminées)

---

## 📌 Sommaire

1. [Contexte et Problématiques](#-contexte-et-problématiques)
2. [Problèmes Critiques](#-problèmes-critiques)
3. [Problèmes Mineurs](#-problèmes-mineurs)
4. [Solutions Détaillées](#-solutions-détaillées)
5. [Plan d'Action Recommandé](#-plan-daction-recommandé)
6. [Tests de Validation](#-tests-de-validation)
7. [Annexes](#-annexes)

---

## 📌 Contexte et Problématiques

### Historique
La refonte UI de SyncFTP a été implémentée en 5 phases :
- **Phase 1** : Foundation (design tokens, structure de base)
- **Phase 2** : Accessibilité (ARIA, focus states)
- **Phase 3** : Component Library (boutons, formulaires, cartes)
- **Phase 4** : Refactoring des pages (extraction CSS par page)
- **Phase 5** : Polish (loading states, validation, responsive)

**Problème principal** : Chaque phase a **ajouté des couches CSS** sans nettoyer les anciennes, créant des **conflits de styles**, des **duplications de classes** et des **comportements imprévisibles**.

### Commit Référence
- Dernier commit : `3c85541` (Phase 5)
- Commit stable : `8196e39` (Phase 4 - avant les conflits)

---

## 🔴 Problèmes Critiques

### 1. Conflits CSS (Duplications)

| Classe | Fichier 1 | Fichier 2 | Impact |
|--------|-----------|-----------|--------|
| `.btn` | `base.css:608-715` | `components.css:73-198` | Styles différents (box-shadow, padding, hover) |
| `.stat-card` | `base.css:466-495` | `components.css:255-284` | Gradient vs background simple |
| `.alert` | `base.css:787-836` | `components.css:10-42` | Bordures et couleurs différentes |
| `.form-group` | `base.css:554-556` | `components.css:308-314` | Marges et espacements |
| `.form-control` | `base.css:573-605` | `components.css:343-370` | Styles de bordure et focus |
| `.nav-btn` | `base.css:428-455` | `components.css:543-567` | Box-shadow et transitions |
| `.card` | `base.css:458-464` | `components.css:214-220` | Ombres et bordures |
| `.table` | `base.css:679-704` | `components.css:689-717` | Styles de tableau |
| `.action-btn` | `base.css:707-753` | `components.css:749-799` | Couleurs et hover |
| `.status-badge` | `base.css:756-784` | `components.css:847-869` | Styles de badge |
| `.section-title` | `base.css:395-401` | Utilisé dans templates | Incohérence |

**Conséquence** : Le navigateur applique la dernière règle chargée (`components.css`), mais certaines propriétés de `base.css` peuvent persister, créant un rendu **instable et imprévisible**.

---

### 2. Balises HTML Non Fermées

| Fichier | Ligne | Problème | Impact |
|---------|-------|----------|--------|
| `templates/list.html` | 18-45 | Balise `<article class="card card-hover">` non fermée | HTML invalide, rendu incorrect |
| `templates/config.html` | 26-70 | Balise `<div>` non fermée (section générale) | HTML invalide |

---

### 3. Problème de `d-none` avec `!important`

**Problème** :
```css
/* base.css:1011 */
.d-none { display: none; }

/* base.css:1047-1052 */
.d-sm-none { display: none; }
.d-md-none { display: none; }
.d-lg-none { display: none; }
```

**Utilisation dans les modaux** :
```javascript
// templates/list.html:107-108
modal.classList.remove('d-none');
modal.style.display = 'flex';
```

**Impact** : Même après `classList.remove('d-none')`, le style `display: none` persiste à cause du `!important` (si présent dans une autre règle).

---

### 4. `window.SyncFTP` Non Disponible

**Problème** :
- `window.SyncFTP` est défini **à la fin de `main.js`** (lignes 303-307)
- Les templates utilisent `window.SyncFTP.toggleButtonLoading()` **dans les handlers d'événements**
- Si `main.js` n'est pas encore chargé, `window.SyncFTP` est `undefined` → **erreur JavaScript**

**Exemple** :
```javascript
// templates/config.html:276
if (submitBtn && window.SyncFTP) {
    window.SyncFTP.toggleButtonLoading(submitBtn, true);
}
```

---

### 5. Fonctions de Validation Non Disponibles

**Problème** :
- Les fonctions `validateFtpPort` et `validateFtpPath` sont définies **à la fin de `main.js`** (lignes 333-352)
- L'initialisation de la validation (`initFormValidation`) s'exécute **au chargement du DOM** (ligne 230-242)
- Si un champ a `data-validate="validateFtpPort"`, la fonction n'existe pas encore → **validation échoue silencieusement**

---

### 6. Chargement des Variables CSS

**Problème** :
- `variables.css` doit être chargé **avant** `base.css` et `components.css`
- Si le chargement échoue ou est lent, toutes les variables (`--color-primary-600`, `--spacing-md`, etc.) sont **indéfinies**
- Résultat : **styles cassés** (couleurs par défaut, espacements incorrects)

---

### 7. Focus Trap dans les Modaux

**Problème** :
```javascript
// templates/list.html:144-155
const focusableElements = modal.querySelectorAll(...);
const firstElement = focusableElements[0];
const lastElement = focusableElements[focusableElements.length - 1];

if (e.shiftKey && document.activeElement === firstElement) {
    lastElement.focus(); // ❌ lastElement peut être undefined
    e.preventDefault();
}
```

**Impact** : Si `focusableElements` est vide, `firstElement` et `lastElement` sont `undefined` → **erreur JavaScript** quand on appuie sur Tab.

---

## 🟡 Problèmes Mineurs

| Problème | Fichier | Impact |
|----------|---------|--------|
| Incohérence des noms de classes (`.form-control` vs `.form-input`) | Tous les templates | Maintenance difficile |
| Couleurs en dur dans les templates (`style="color: red;"`) | Divers | Non maintainable |
| Emojis dans le HTML vs CSS | Tous les templates | Incohérence visuelle |
| Classes redondantes (`.btn.btn-primary` vs `.btn.btn--primary`) | `list.html`, `tasks.html` | Confusion |

---

## ✅ Solutions Détaillées

---

### Solution 1 : Nettoyage Complet (Recommandé)

#### Étape 1 : Fusionner `base.css` et `components.css`

**Objectif** : Créer un seul fichier `main.css` qui contient toutes les classes sans duplication.

**Actions** :
1. Créer un nouveau fichier `static/css/main.css`
2. Y intégrer le contenu de `variables.css` (via `@import` ou `<link>`)
3. Fusionner `base.css` et `components.css` en :
   - **Gardant une seule définition par classe**
   - **Priorisant les styles de la Phase 5** (plus modernes)
   - **Supprimant les doublons**
4. Structurer le fichier ainsi :
   ```css
   /* ======================================== */
   /* SyncFTP Main Stylesheet */
   /* ======================================== */
   
   /* 1. Design Tokens (from variables.css) */
   @import url('variables.css');
   
   /* 2. CSS Reset & Base Styles */
   /* (from base.css:1-207) */
   
   /* 3. Layout Utilities */
   /* (from base.css:375-402) */
   
   /* 4. Components */
   /* 4.1 Buttons (fusion base.css + components.css) */
   /* 4.2 Forms (fusion) */
   /* 4.3 Cards (fusion) */
   /* 4.4 Alerts (fusion) */
   /* 4.5 Tables (fusion) */
   /* 4.6 Modals (fusion) */
   /* 4.7 Navigation (fusion) */
   
   /* 5. Utility Classes */
   /* (from base.css:950-1138) */
   
   /* 6. Responsive Breakpoints */
   /* (from base.css:1046-1138 + components.css:1280-1306) */
   
   /* 7. Loading States */
   /* (from components.css:1056-1133) */
   
   /* 8. Form Validation */
   /* (from components.css:1136-1232) */
   ```

**Fichiers à modifier** :
- `static/css/main.css` (nouveau)
- `templates/base.html` : Remplacer le chargement de `base.css` + `components.css` par `main.css`

---

#### Étape 2 : Corriger les Templates

##### a) Corriger `templates/list.html`

**Problème** : Balise `<article>` non fermée (ligne 18).

**Correction** :
```html
<!-- Avant (ligne 18-45) -->
<article class="card card-hover" data-server-id="{{ server.id }}">
    <h3 class="card-title">{{ server.name }}</h3>
    <div class="server-info text-muted mb-sm">
        <strong>Hôte:</strong> {{ server.host }}:{{ server.port }}
    </div>
    <div class="server-info text-muted mb-sm">
        <strong>Utilisateur:</strong> {{ server.username }}
    </div>
    <div class="server-info text-muted mb-sm">
        <strong>SSL:</strong> 
        {% if server.use_ssl %}
            <span class="badge badge--success">✅ Oui</span>
        {% else %}
            <span class="badge badge--secondary">❌ Non</span>
        {% endif %}
    </div>
    {% if server.test_directory %}
        <div class="server-info text-muted mb-md">
            <strong>Répertoire:</strong> {{ server.test_directory }}
        </div>
    {% endif %}
    <div class="server-actions">
        <button class="btn btn--info btn--sm test-btn" data-server-id="{{ server.id }}">🔍 TESTER</button>
        <form action="/delete_server/{{ server.id }}" method="POST" class="d-inline">
            <button type="submit" class="btn btn--danger btn--sm" onclick="return confirm('Êtes-vous sûr de vouloir supprimer ce serveur ?')">🗑️ Supprimer</button>
        </form>
    </div>
</div>  <!-- ❌ Balise div fermée, mais article non fermée -->

<!-- Après -->
<article class="card card-hover" data-server-id="{{ server.id }}">
    <h3 class="card-title">{{ server.name }}</h3>
    <div class="server-info text-muted mb-sm">
        <strong>Hôte:</strong> {{ server.host }}:{{ server.port }}
    </div>
    <div class="server-info text-muted mb-sm">
        <strong>Utilisateur:</strong> {{ server.username }}
    </div>
    <div class="server-info text-muted mb-sm">
        <strong>SSL:</strong> 
        {% if server.use_ssl %}
            <span class="badge badge--success">✅ Oui</span>
        {% else %}
            <span class="badge badge--secondary">❌ Non</span>
        {% endif %}
    </div>
    {% if server.test_directory %}
        <div class="server-info text-muted mb-md">
            <strong>Répertoire:</strong> {{ server.test_directory }}
        </div>
    {% endif %}
    <div class="server-actions">
        <button class="btn btn--info btn--sm test-btn" data-server-id="{{ server.id }}">🔍 TESTER</button>
        <form action="/delete_server/{{ server.id }}" method="POST" class="d-inline">
            <button type="submit" class="btn btn--danger btn--sm" onclick="return confirm('Êtes-vous sûr de vouloir supprimer ce serveur ?')">🗑️ Supprimer</button>
        </form>
    </div>
</article>  <!-- ✅ Balise article fermée -->
```

##### b) Corriger `templates/config.html`

**Problème** : Balise `<div>` non fermée (ligne 26).

**Correction** :
```html
<!-- Avant (ligne 22-70) -->
<section aria-labelledby="general-config-title">
    <h3 id="general-config-title" class="config-section-title">📋 Paramètres généraux</h3>
    
    <form id="generalConfigForm" action="/save_config" method="POST" class="mt-lg" aria-label="Formulaire de configuration générale">
        ...
    </form>
</div>  <!-- ❌ Balise div fermée, mais section non fermée -->

<!-- Après -->
<section aria-labelledby="general-config-title">
    <h3 id="general-config-title" class="config-section-title">📋 Paramètres généraux</h3>
    
    <form id="generalConfigForm" action="/save_config" method="POST" class="mt-lg" aria-label="Formulaire de configuration générale">
        ...
    </form>
</section>  <!-- ✅ Balise section fermée -->
```

---

#### Étape 3 : Corriger `d-none` pour les Modaux

**Problème** : `d-none` utilise `display: none !important`, ce qui empêche l'affichage des modaux.

**Solution 1 : Modifier `d-none` dans `main.css`** :
```css
/* Remplacer dans main.css */
.d-none { display: none; } /* Sans !important */
.d-flex { display: flex; }
.d-block { display: block; }
```

**Solution 2 : Utiliser une classe dédiée pour les modaux** :
```css
/* Ajouter dans main.css */
.modal-overlay {
    display: none;
}
.modal-overlay.is-open {
    display: flex;
}
```

**Modifier dans `templates/list.html` et `templates/tasks.html`** :
```javascript
// Avant
function openModal() {
    modal.classList.remove('d-none');
    modal.style.display = 'flex';
    // ...
}

function closeModal() {
    modal.classList.add('d-none');
    modal.style.display = 'none';
    // ...
}

// Après
function openModal() {
    modal.classList.add('is-open');
    // ...
}

function closeModal() {
    modal.classList.remove('is-open');
    // ...
}
```

---

#### Étape 4 : Corriger `main.js`

##### a) Déplacer `window.SyncFTP` au début du fichier

**Avant** (lignes 303-307) :
```javascript
// À la fin du fichier
window.SyncFTP = window.SyncFTP || {};
window.SyncFTP.toggleButtonLoading = toggleButtonLoading;
window.SyncFTP.toggleLoadingOverlay = toggleLoadingOverlay;
window.SyncFTP.announce = announceToScreenReader;
window.SyncFTP.validateField = validateField;
```

**Après** (au début du fichier, après la déclaration de la IIFE) :
```javascript
(function() {
    'use strict';

    // ========================================
    // Global Namespace
    // ========================================
    window.SyncFTP = window.SyncFTP || {};

    // ========================================
    // Utility Functions
    // ========================================
    // ... (le reste du code)
```

##### b) Déplacer les fonctions de validation avant l'initialisation

**Avant** :
```javascript
// Ligne 176-243: initFormValidation()
// ...
// Ligne 333-352: validateFtpPort(), validateFtpPath()
```

**Après** :
```javascript
// Ligne 176-243: initFormValidation()

// ========================================
// Custom Validators
// ========================================
function validateFtpPort(value) {
    const port = parseInt(value, 10);
    return {
        isValid: !value || (port >= 1 && port <= 65535),
        message: 'Le port doit être compris entre 1 et 65535'
    };
}

function validateFtpPath(value) {
    if (!value) return { isValid: true };
    const invalidChars = /[<>:"|?*]/;
    return {
        isValid: !invalidChars.test(value),
        message: 'Le chemin contient des caractères non valides'
    };
}

// ========================================
// Auto-Init Features
// ========================================
```

##### c) Exporter les utilitaires dans `window.SyncFTP` au fur et à mesure

**Modifier les fonctions pour les ajouter à `window.SyncFTP` immédiatement** :
```javascript
function announceToScreenReader(message, priority = 'polite') {
    // ...
}
window.SyncFTP.announce = announceToScreenReader; // Ajouter cette ligne

function toggleButtonLoading(button, loading = true) {
    // ...
}
window.SyncFTP.toggleButtonLoading = toggleButtonLoading; // Ajouter cette ligne

function toggleLoadingOverlay(container, show = true) {
    // ...
}
window.SyncFTP.toggleLoadingOverlay = toggleLoadingOverlay; // Ajouter cette ligne

function validateField(input, validator) {
    // ...
}
window.SyncFTP.validateField = validateField; // Ajouter cette ligne
```

---

#### Étape 5 : Corriger le Chargement des CSS

**Modifier `templates/base.html`** :

**Avant** :
```html
<head>
    <!-- Design Tokens -->
    <link rel="stylesheet" href="{{ url_for('static', filename='css/variables.css') }}">
    
    <!-- Base Styles -->
    <link rel="stylesheet" href="{{ url_for('static', filename='css/base.css') }}">
    
    <!-- Components -->
    <link rel="stylesheet" href="{{ url_for('static', filename='css/components.css') }}">
    
    <!-- Page-specific title -->
    <title>{% block title %}{{ app_name }} - {{ page_title|default('') }}{% endblock %}</title>
    
    <!-- Preload critical resources -->
    <link rel="preload" href="{{ url_for('static', filename='css/variables.css') }}" as="style">
    <link rel="preload" href="{{ url_for('static', filename='css/base.css') }}" as="style">
    <link rel="preload" href="{{ url_for('static', filename='js/main.js') }}" as="script">
</head>
```

**Après** :
```html
<head>
    <!-- Design Tokens + Main Styles (fusionné) -->
    <link rel="stylesheet" href="{{ url_for('static', filename='css/main.css') }}?v={{ app_version }}">
    
    <!-- Page-specific title -->
    <title>{% block title %}{{ app_name }} - {{ page_title|default('') }}{% endblock %}</title>
    
    <!-- Preload critical resources -->
    <link rel="preload" href="{{ url_for('static', filename='css/main.css') }}?v={{ app_version }}" as="style">
    <link rel="preload" href="{{ url_for('static', filename='js/main.js') }}?v={{ app_version }}" as="script">
    
    <!-- Page-specific CSS -->
    {% block head %}{% endblock %}
</head>
<body>
    <!-- ... -->
    
    <!-- Main JavaScript -->
    <script src="{{ url_for('static', filename='js/main.js') }}?v={{ app_version }}" defer></script>
    
    <!-- Page-specific scripts -->
    {% block scripts %}{% endblock %}
</body>
```

---

#### Étape 6 : Corriger les Focus Traps

**Modifier `templates/list.html` et `templates/tasks.html`** :

**Avant** :
```javascript
// Focus trap
if (e.key === 'Tab') {
    const focusableElements = modal.querySelectorAll(...);
    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];
    
    if (e.shiftKey && document.activeElement === firstElement) {
        lastElement.focus(); // ❌ Peut être undefined
        e.preventDefault();
    } else if (!e.shiftKey && document.activeElement === lastElement) {
        firstElement.focus(); // ❌ Peut être undefined
        e.preventDefault();
    }
}
```

**Après** :
```javascript
// Focus trap
if (e.key === 'Tab') {
    const focusableElements = modal.querySelectorAll(...);
    if (focusableElements.length === 0) return; // ✅ Vérifier que le tableau n'est pas vide
    
    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];
    
    if (e.shiftKey && document.activeElement === firstElement) {
        lastElement.focus();
        e.preventDefault();
    } else if (!e.shiftKey && document.activeElement === lastElement) {
        firstElement.focus();
        e.preventDefault();
    }
}
```

---

### Solution 2 : Quick Fix (Minimal)

Si vous voulez une correction **rapide sans tout refactoriser** :

#### 1. Supprimer les doublons dans `components.css`

**Actions** :
1. Supprimer de `components.css` toutes les classes déjà dans `base.css` :
   - `.btn` (lignes 73-198)
   - `.alert` (lignes 10-42)
   - `.form-group`, `.form-control` (lignes 308-370)
   - `.card` (lignes 214-220)
   - `.table` (lignes 689-717)
   - `.action-btn` (lignes 749-799)
   - `.status-badge` (lignes 847-869)
   - `.stat-card` (lignes 255-284)
   - `.nav-menu`, `.nav-btn` (lignes 535-567)

2. **Garder uniquement les composants uniques** dans `components.css` :
   - `.btn--outline`, `.btn--info`, `.btn--warning` (nouveaux dans Phase 5)
   - `.btn--sm`, `.btn--lg`, `.btn--xl`, `.btn-icon` (tailles étendues)
   - `.btn-group` (nouveau)
   - `.form-switch` (nouveau)
   - `.form-file` (nouveau)
   - `.tooltip` (nouveau)
   - `.progress` (nouveau)
   - `.spinner` (nouveau)
   - Loading states (lignes 1056-1133)
   - Form validation (lignes 1136-1232)

#### 2. Corriger les balises HTML
- Voir **Étape 2 de la Solution 1** (correction de `list.html` et `config.html`)

#### 3. Corriger `d-none` pour les modaux
- Voir **Étape 3 de la Solution 1**

---

### Solution 3 : Rollback + Réimplémentation

**Recommandé si les problèmes persistent** :

1. **Faire un rollback à la Phase 4** (commit `8196e39`) :
   ```bash
   git checkout 8196e39
   ```

2. **Réappliquer les changements de la Phase 5 proprement** :
   - **Sans ajouter de doublons** dans `components.css`
   - **En fusionnant les styles** plutôt qu'en les ajoutant
   - **En testant chaque changement** avant de committer

---

## 🎯 Plan d'Action Recommandé

### Priorité 1 : Corrections Critiques (À faire maintenant)

| Tâche | Fichier | Difficulté | Temps Estimé |
|-------|---------|------------|---------------|
| 1. Corriger les balises HTML non fermées | `list.html`, `config.html` | ⭐ | 15 min |
| 2. Corriger `d-none` pour les modaux | `list.html`, `tasks.html`, `base.css` | ⭐⭐ | 20 min |
| 3. Déplacer `window.SyncFTP` au début de `main.js` | `main.js` | ⭐⭐ | 10 min |
| 4. Déplacer les validateurs avant l'init | `main.js` | ⭐⭐ | 10 min |
| 5. Corriger les focus traps | `list.html`, `tasks.html` | ⭐⭐ | 15 min |
| **Total** | | | **1h10** |

### Priorité 2 : Nettoyage CSS (À faire ensuite)

| Tâche | Fichier | Difficulté | Temps Estimé |
|-------|---------|------------|---------------|
| 6. Fusionner `base.css` et `components.css` | `main.css` (nouveau) | ⭐⭐⭐ | 2h |
| 7. Mettre à jour `base.html` | `base.html` | ⭐ | 5 min |
| 8. Supprimer `base.css` et `components.css` | - | ⭐ | 2 min |
| **Total** | | | **2h07** |

### Priorité 3 : Optimisations (Optionnel)

| Tâche | Fichier | Difficulté | Temps Estimé |
|-------|---------|------------|---------------|
| 9. Ajouter le cache busting | `base.html` | ⭐ | 5 min |
| 10. Minifier les CSS | `scripts/minify_css.py` | ⭐⭐ | 30 min |
| 11. Optimiser les images/emojis | Tous | ⭐ | 15 min |
| **Total** | | | **50 min** |

---

## 🧪 Tests de Validation

### 1. Tests HTML

**Outil** : [W3C Validator](https://validator.w3.org/)

**Commande** :
```bash
# Installer html5validator
pip install html5validator

# Valider tous les templates
html5validator --root templates/
```

**Attendu** : Aucun erreur HTML.

---

### 2. Tests CSS

**Outil** : [CSS Validator](https://jigsaw.w3.org/css-validator/)

**Commande** :
```bash
# Installer css-validator (via Node.js)
npm install -g css-validator

# Valider le CSS
css-validator static/css/main.css
```

**Attendu** :
- Aucune erreur de syntaxe
- Aucune classe dupliquée
- Toutes les variables CSS (`--color-*`, `--spacing-*`) sont définies

---

### 3. Tests JavaScript

**Outil** : Console navigateur (F12)

**Tests à effectuer** :

| Test | Attendu | Fichier |
|------|---------|--------|
| Ouvrir un modal | Le modal s'affiche correctement | `list.html`, `tasks.html` |
| Soumettre un formulaire | Le bouton montre un loading spinner | `add.html`, `config.html` |
| Valider un champ FTP port | Message d'erreur si invalide | `add.html` |
| Appuyer sur Tab dans un modal | Le focus reste dans le modal | `list.html`, `tasks.html` |
| Charger la page | Aucune erreur dans la console | Tous |

**Commande pour tester en local** :
```bash
# Démarrer le serveur Flask
python app.py

# Ouvrir dans le navigateur
http://localhost:5000
```

---

### 4. Tests d'Accessibilité

**Outil** : [axe DevTools](https://www.deque.com/axe/) ou [Lighthouse](https://developer.chrome.com/docs/lighthouse/overview/)

**Tests à effectuer** :
- Vérifier que tous les éléments interactifs ont un `tabindex`
- Vérifier que tous les modaux ont un focus trap
- Vérifier que les messages d'erreur sont accessibles aux lecteurs d'écran
- Vérifier que les couleurs ont un contraste suffisant (WCAG AA)

---

### 5. Tests Responsive

**Outil** : Chrome DevTools (Device Mode)

**Points de rupture à tester** :
- Mobile (320px - 480px)
- Tablette (768px - 1024px)
- Desktop (1024px+)

**Attendu** :
- Le menu de navigation s'adapte (passage en colonne sur mobile)
- Les cartes et grilles s'adaptent
- Les formulaires restent utilisables
- Les modaux s'affichent correctement

---

## 📁 Annexes

### A. Structure des Fichiers après Corrections

```
SyncFTP/
├── static/
│   ├── css/
│   │   ├── main.css          # Fusion de base.css + components.css + variables.css
│   │   └── pages/            # CSS spécifiques aux pages
│   │       ├── index.css
│   │       ├── config.css
│   │       ├── add.css
│   │       ├── list.css
│   │       ├── logs.css
│   │       └── tasks.css
│   └── js/
│       └── main.js           # JavaScript principal (corrigé)
├── templates/
│   ├── base.html            # Template de base (corrigé)
│   ├── index.html           # Page d'accueil
│   ├── add.html             # Ajouter un serveur (corrigé)
│   ├── list.html            # Liste des serveurs (corrigé)
│   ├── config.html          # Configuration (corrigé)
│   ├── logs.html            # Logs
│   └── tasks.html           # Tâches (corrigé)
└── scripts/
    └── minify_css.py        # Script de minification (optionnel)
```

---

### B. Checklist avant Déploiement

- [ ] Tous les tests HTML passent
- [ ] Tous les tests CSS passent
- [ ] Aucun erreur JavaScript dans la console
- [ ] Les modaux s'affichent correctement
- [ ] Les formulaires fonctionnent (validation, loading states)
- [ ] Le design est cohérent sur mobile, tablette et desktop
- [ ] Les tests d'accessibilité passent (axe/Lighthouse)
- [ ] Le cache busting est activé
- [ ] Les fichiers CSS/JS sont minifiés (optionnel)

---

### C. Commandes Utiles

**Valider tout le projet** :
```bash
# HTML
html5validator --root templates/

# CSS (nécessite Node.js)
npx css-validator static/css/main.css

# Python (syntaxe)
pylint app.py ftp_tools.py

# Git : Vérifier les changements
git status
git diff
```

**Démarrer le serveur en mode développement** :
```bash
python app.py --verbose
```

**Minifier les CSS** :
```bash
python scripts/minify_css.py --all
```

---

### D. Références

- [W3C HTML Validator](https://validator.w3.org/)
- [W3C CSS Validator](https://jigsaw.w3.org/css-validator/)
- [axe DevTools](https://www.deque.com/axe/)
- [Lighthouse](https://developer.chrome.com/docs/lighthouse/overview/)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [MDN CSS Variables](https://developer.mozilla.org/en-US/docs/Web/CSS/Using_CSS_custom_properties)

---

## 📝 Historique des Modifications

| Date | Auteur | Modification | Commit |
|------|--------|--------------|--------|
| 29/07/2026 | Analyse | Identification des problèmes | - |
| 29/07/2026 | Vibe | Implémentation Priorité 1 et 2 | fee0e78 |

**Modifications implémentées** :
- ✅ Correction des balises HTML (list.html, config.html)
- ✅ Fix modal display avec `.is-open` au lieu de `d-none + style.display`
- ✅ Correction des focus traps (vérification `length > 0`)
- ✅ `window.SyncFTP` déplacé au début de main.js
- ✅ Validateurs déplacés avant init dans main.js
- ✅ Export des utilitaires dans `window.SyncFTP` au fur et à mesure
- ✅ Fusion base.css + components.css + variables.css → main.css
- ✅ Mise à jour base.html pour utiliser main.css avec cache busting

**À faire** :
- [ ] Supprimer les anciens fichiers base.css, components.css, variables.css (optionnel)
- [ ] Tests de validation complets

---

> **Note** : Ce document doit être mis à jour après chaque correction appliquée.
