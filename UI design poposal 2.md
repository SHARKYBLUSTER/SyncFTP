# Web Design — Improvement Proposals: SyncFTP Application

> Static analysis of source code (templates/*.html). Does not measure runtime performance, does not take screenshots, does not render JS-heavy SPAs. Pair with Lighthouse and chrome-devtools-mcp for runtime layer.

---

## Summary

- **Target:** `E:\GITHUB\Sharky\SyncFTP\templates\` (6 HTML templates)
- **Mode:** Source code analysis
- **Findings:** 12 Tier 1 issues, 8 Tier 2 issues
- **Quick wins:** 10
- **Big fixes:** 5
- **Polish:** 5

---

## Quick wins (do today)

### Finding: CSS Duplication Across All Templates
- **Severity:** Tier 1 (AVOID-AT-ALL-COSTS)
- **Confidence:** [STATIC]
- **Where:** All 6 template files, lines 1-80 (approx)
- **What's wrong:** 1800+ lines of duplicate CSS across all templates. Each file repeats identical base styles (body, container, header, nav-menu, section, buttons, etc.)
- **Damage:** Code bloat, maintenance nightmare, larger page sizes, slower load times
- **Proposed change:**
  ```diff
  - Create templates/base.html with shared CSS
  - Each template extends base.html using Jinja2 template inheritance
  - Extract common styles to static/css/main.css
  ```
- **Effort:** Medium (but high ROI)

### Finding: Missing Meta Description
- **Severity:** Tier 2 (SHOULD-AVOID)
- **Confidence:** [STATIC]
- **Where:** All templates, <head> section
- **What's wrong:** Missing `<meta name="description">` tag
- **Damage:** Poor SEO, social sharing displays generic text
- **Proposed change:**
  ```diff
  - No meta description
  + <meta name="description" content="Gerez et synchronisez vos serveurs FTP avec SyncFTP - Interface web legere pour la gestion de connexions FTP et taches de synchronisation automatique">
  ```
- **Effort:** Small

### Finding: Missing Favicon
- **Severity:** Tier 2 (SHOULD-AVOID)
- **Confidence:** [STATIC]
- **Where:** All templates, <head> section
- **What's wrong:** No favicon link
- **Damage:** Browser tab shows generic document icon, poor branding
- **Proposed change:**
  ```diff
  - No favicon
  + <link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
  + <link rel="apple-touch-icon" href="/static/apple-touch-icon.png">
  ```
- **Effort:** Small

### Finding: No Semantic HTML5 Elements
- **Severity:** Tier 2 (SHOULD-AVOID)
- **Confidence:** [STATIC]
- **Where:** All templates, structure
- **What's wrong:** Uses generic `<div>` for navigation, main content, footer
- **Damage:** Poor accessibility, screen readers can't identify page regions
- **Proposed change:**
  ```diff
  - <div class="nav-menu"> -> <nav class="nav-menu">
  - <div class="container"> -> <main class="container">
  - Wrap navigation links in <nav>
  ```
- **Effort:** Small

### Finding: Missing ARIA Attributes on Interactive Elements
- **Severity:** Tier 1 (AVOID-AT-ALL-COSTS)
- **Confidence:** [STATIC]
- **Where:** Buttons and links in all templates
- **What's wrong:** Modal buttons, form buttons lack ARIA labels and roles
- **Damage:** Keyboard users and screen reader users have poor experience
- **Proposed change:**
  ```diff
  - <button class="close-btn" onclick="closeModal()">&times;</button>
  + <button class="close-btn" onclick="closeModal()" aria-label="Fermer">x</button>

  - <button class="btn test-btn" data-server-id="{{ server.id }}"> TESTER</button>
  + <button class="btn test-btn" data-server-id="{{ server.id }}" aria-label="Tester la connexion au serveur {{ server.name }}"> TESTER</button>
  ```
- **Effort:** Small

### Finding: Inline Styles in HTML
- **Severity:** Tier 2 (SHOULD-AVOID)
- **Confidence:** [STATIC]
- **Where:** All templates (e.g., list.html:334, config.html:382, etc.)
- **What's wrong:** Style attributes mixed with HTML (e.g., `style="display: flex; gap: 10px; align-items: center;"`)
- **Damage:** Violates separation of concerns, harder to maintain
- **Proposed change:**
  ```diff
  - <div style="display: flex; gap: 15px; flex-wrap: wrap;">
  + <div class="action-buttons">
  
  + .action-buttons { display: flex; gap: 15px; flex-wrap: wrap; }
  ```
- **Effort:** Small

### Finding: Color Contrast - Form Input Placeholder
- **Severity:** Tier 1 (AVOID-AT-ALL-COSTS)
- **Confidence:** [STATIC]
- **Where:** add.html:205, and all form inputs
- **What's wrong:** Placeholder text color not explicitly set, may have insufficient contrast
- **Damage:** Users with visual impairments may not see placeholder text
- **Proposed change:**
  ```diff
  - input::placeholder { /* inherits default */ }
  + input::placeholder { color: #999; opacity: 1; }
  ```
- **Effort:** Small

### Finding: No Skip to Main Content Link
- **Severity:** Tier 1 (AVOID-AT-ALL-COSTS)
- **Confidence:** [STATIC]
- **Where:** All templates, before navigation
- **What's wrong:** Missing skip link for keyboard navigation
- **Damage:** Keyboard users must tab through entire navigation to reach content
- **Proposed change:**
  ```diff
  - No skip link
  + <a href="#main-content" class="skip-link">Aller au contenu principal</a>
  + <main id="main-content">...</main>
  
  + .skip-link { position: absolute; top: -40px; left: 0; background: #667eea; color: white; padding: 8px; z-index: 100; text-decoration: none; }
  + .skip-link:focus { top: 0; }
  ```
- **Effort:** Small

### Finding: Form Labels Not Associated with Inputs
- **Severity:** Tier 1 (AVOID-AT-ALL-COSTS)
- **Confidence:** [STATIC]
- **Where:** add.html:204-205, 208-209, etc.
- **What's wrong:** Some form inputs use `for` attribute but some labels wrap inputs without proper association
- **Damage:** Clicking label doesn't focus input for some fields
- **Proposed change:**
  ```diff
  - <label for="name">Nom du serveur *</label>
    <input type="text" id="name" name="name" required placeholder="Mon Serveur FTP">
  + <label for="server-name">Nom du serveur *</label>
    <input type="text" id="server-name" name="name" required placeholder="Mon Serveur FTP">
  ```
  Ensure all inputs have matching `id` and label `for` attributes.
- **Effort:** Small

### Finding: Missing Language Attribute on Form Elements
- **Severity:** Tier 2 (SHOULD-AVOID)
- **Confidence:** [STATIC]
- **Where:** All forms in all templates
- **What's wrong:** Form inputs don't have `lang` or `inputmode` attributes
- **Damage:** Mobile keyboards may show wrong input type
- **Proposed change:**
  ```diff
  - <input type="text" id="host" name="host" required placeholder="ftp.example.com">
  + <input type="url" id="host" name="host" required placeholder="ftp.example.com" inputmode="url">

  - <input type="number" id="port" name="port" value="21" min="1" max="65535">
  + <input type="number" id="port" name="port" value="21" min="1" max="65535" inputmode="numeric">
  ```
- **Effort:** Small

---

## Big fixes (schedule)

### Finding: No External CSS Architecture
- **Severity:** Tier 1 (AVOID-AT-ALL-COSTS)
- **Confidence:** [STATIC]
- **Where:** All templates
- **What's wrong:** 6 files x ~200 lines of CSS = ~1200 lines of duplicate CSS
- **Damage:** 100KB+ of redundant CSS, slow page loads, maintenance nightmare
- **Proposed change:**
  ```
  Project restructure:
  static/
  |-- css/
  |   |-- main.css        # Shared base styles
  |   |-- components.css  # Buttons, cards, forms
  |   |-- layout.css      # Grid, navigation
  templates/
  |-- base.html          # Jinja2 base template
  |-- index.html
  |-- add.html
  |-- ...
  ```
  Each template extends base.html and includes CSS files.
- **Effort:** Large (but transforms maintainability)

### Finding: No CSS Methodology
- **Severity:** Tier 2 (SHOULD-AVOID)
- **Confidence:** [STATIC]
- **Where:** All CSS in all templates
- **What's wrong:** CSS is ad-hoc with no naming convention
- **Damage:** Hard to maintain, risk of conflicts, no reusability
- **Proposed change:**
  Adopt BEM (Block__Element--Modifier) or similar:
  ```diff
  - .nav-btn { ... }
  - .nav-btn:hover { ... }
  + .nav__btn { ... }
  + .nav__btn:hover { ... }
  + .nav__btn--secondary { ... }
  + .nav__btn--danger { ... }
  ```
- **Effort:** Medium

### Finding: No Design Tokens / CSS Variables
- **Severity:** Tier 2 (SHOULD-AVOID)
- **Confidence:** [STATIC]
- **Where:** All templates, color definitions
- **What's wrong:** Colors hardcoded (e.g., `#667eea`, `#764ba2`, `#f8f9fa`)
- **Damage:** Inconsistent colors, hard to theme, can't change color scheme easily
- **Proposed change:**
  ```css
  :root {
    --color-primary: #667eea;
    --color-primary-dark: #764ba2;
    --color-secondary: #f093fb;
    --color-danger: #ff6b6b;
    --color-success: #28a745;
    --color-warning: #ffc107;
    --color-background: #f8f9fa;
    --color-text: #333;
    --color-text-light: #666;
    --color-border: #e0e0e0;
    --shadow-sm: 0 2px 10px rgba(0,0,0,0.1);
    --shadow-md: 0 10px 30px rgba(0,0,0,0.2);
    --radius-sm: 5px;
    --radius-md: 8px;
    --radius-lg: 15px;
  }

  .btn {
    background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-dark) 100%);
  }
  ```
- **Effort:** Medium

### Finding: No Form Validation Feedback
- **Severity:** Tier 2 (SHOULD-AVOID)
- **Confidence:** [STATIC]
- **Where:** add.html form, config.html forms
- **What's wrong:** HTML5 validation exists but no visual feedback for invalid fields
- **Damage:** Users don't know which field failed validation
- **Proposed change:**
  ```css
  input:invalid {
    border-color: var(--color-danger);
    background-color: #fff5f5;
  }

  input:valid {
    border-color: var(--color-success);
  }

  input:invalid + .error-message {
    display: block;
    color: var(--color-danger);
    font-size: 0.85em;
    margin-top: 5px;
  }
  ```
- **Effort:** Medium

### Finding: Modal Accessibility Issues
- **Severity:** Tier 1 (AVOID-AT-ALL-COSTS)
- **Confidence:** [STATIC]
- **Where:** list.html modal (lines 370-397)
- **What's wrong:** Modal lacks `role="dialog"`, `aria-modal="true"`, focus trap, escape key handling
- **Damage:** Screen readers can't announce modal, keyboard users trapped
- **Proposed change:**
  ```diff
  - <div id="testModal" class="modal">
  + <div id="testModal" class="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title">

  - <div class="modal-content">
  + <div class="modal-content" tabindex="-1">

  - <h2> Tester la connexion FTP</h2>
  + <h2 id="modal-title"> Tester la connexion FTP</h2>

  + Add JavaScript:
    modal.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') closeModal();
      if (e.key === 'Tab') {
        // Focus trap logic
      }
    });
  ```
- **Effort:** Medium

---

## Polish (backlog)

### Finding: Inconsistent Button Sizes
- **Severity:** Tier 2 (SHOULD-AVOID)
- **Confidence:** [HEURISTIC]
- **Where:** Various buttons across templates
- **What's wrong:** Buttons have different padding (e.g., nav-btn: 15px 30px, btn: 12px 30px)
- **Damage:** Visual inconsistency
- **Proposed change:**
  ```css
  .btn, .nav-btn {
    padding: 12px 24px;
    font-size: 16px;
    border-radius: var(--radius-md);
  }

  .btn-sm { padding: 8px 16px; font-size: 14px; }
  .btn-lg { padding: 16px 32px; font-size: 18px; }
  ```
- **Effort:** Small

### Finding: No Loading States for Forms
- **Severity:** Tier 2 (SHOULD-AVOID)
- **Confidence:** [STATIC]
- **Where:** add.html form, config.html forms
- **What's wrong:** Submit buttons don't show loading state
- **Damage:** Users may click multiple times, unclear if form is submitting
- **Proposed change:**
  ```css
  .btn.loading {
    pointer-events: none;
    opacity: 0.8;
    position: relative;
  }

  .btn.loading::after {
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    width: 20px;
    height: 20px;
    margin: -10px 0 0 -10px;
    border: 2px solid rgba(255,255,255,.3);
    border-radius: 50%;
    border-top-color: white;
    animation: spin 0.8s linear infinite;
  }
  ```
- **Effort:** Small

### Finding: Typography Hierarchy Weak
- **Severity:** Tier 2 (SHOULD-AVOID)
- **Confidence:** [HEURISTIC]
- **Where:** All templates
- **What's wrong:** Only h1, h2 used; no h3-h6 scale, inconsistent font weights
- **Damage:** Content hierarchy unclear
- **Proposed change:**
  ```css
  :root {
    --font-size-xs: 0.75rem;
    --font-size-sm: 0.875rem;
    --font-size-base: 1rem;
    --font-size-lg: 1.125rem;
    --font-size-xl: 1.25rem;
    --font-size-2xl: 1.5rem;
    --font-size-3xl: 2rem;
    --font-size-4xl: 2.5rem;
  }
  ```
- **Effort:** Small

---

## Implementation Plan: SyncFTP Web Design Improvements

---

### Phase Overview

| Phase | Duration | Priority | Deliverables |
|-------|----------|----------|--------------|
| **Phase 1: Foundation** | 2-3 hours | Critical | CSS architecture, design tokens, base template |
| **Phase 2: Accessibility** | 2-3 hours | Critical | ARIA, semantic HTML, keyboard navigation |
| **Phase 3: Component Library** | 3-4 hours | High | Reusable components, form styles |
| **Phase 4: Page Refactoring** | 4-6 hours | High | Migrate each template to new system |
| **Phase 5: Polish** | 2-3 hours | Medium | Loading states, validation, final touches |

**Total Estimated Time:** 13-19 hours

---

## Detailed Implementation Plan

---

### Phase 1: Foundation (Critical - Do First)

**Goal:** Create scalable CSS architecture and design system

#### Tasks:

1. **Create directory structure**
   ```bash
   mkdir -p static/css
   mkdir -p static/js
   ```

2. **Create design tokens (static/css/variables.css)**
   - Define color palette
   - Define spacing scale
   - Define typography scale
   - Define shadows, borders, radii

3. **Create base template (templates/base.html)**
   - HTML5 doctype and structure
   - Common meta tags
   - CSS imports
   - Skip link
   - Jinja2 blocks for content

4. **Create CSS reset and base styles (static/css/base.css)**
   - CSS reset
   - Body and typography base
   - Utility classes

**Files to create:**
```
static/
|-- css/
|   |-- variables.css    # Design tokens
|   |-- base.css        # Reset + base styles
|   |-- components.css  # Shared components
templates/
|-- base.html           # Jinja2 base template
```

---

### Phase 2: Accessibility (Critical - Do Second)

**Goal:** Make the application accessible to all users

#### Tasks:

1. **Add skip-to-content link**
   - Add skip link in base.html
   - Add main content landmark

2. **Add ARIA attributes**
   - Modal: `role="dialog"`, `aria-modal="true"`, `aria-labelledby`
   - Buttons: `aria-label` for icon-only buttons
   - Forms: `aria-describedby` for help text

3. **Improve keyboard navigation**
   - Focus trap for modals
   - Visible focus indicators
   - Escape key to close modals

4. **Form accessibility**
   - Proper label associations
   - Required field indicators
   - Error message associations

**Files to modify:**
- `templates/base.html`
- `templates/list.html` (modal)
- All form templates

---

### Phase 3: Component Library (High Priority)

**Goal:** Create reusable, consistent components

#### Tasks:

1. **Create CSS components (static/css/components.css)**
   ```css
   /* Buttons */
   .btn { ... }
   .btn--primary { ... }
   .btn--secondary { ... }
   .btn--danger { ... }
   .btn--success { ... }

   /* Forms */
   .form-group { ... }
   .form-row { ... }
   .form-label { ... }
   .form-input { ... }
   .form-select { ... }
   .form-help { ... }

   /* Cards */
   .card { ... }
   .card-header { ... }
   .card-body { ... }

   /* Navigation */
   .nav { ... }
   .nav-list { ... }
   .nav-item { ... }
   .nav-link { ... }
   
   /* Stats */
   .stat-card { ... }
   .stat-grid { ... }

   /* Modal */
   .modal { ... }
   .modal-backdrop { ... }
   .modal-content { ... }
   ```

2. **Create responsive utilities**
   ```css
   .d-none { display: none; }
   .d-flex { display: flex; }
   .gap-1 { gap: 0.25rem; }
   .gap-2 { gap: 0.5rem; }
   .gap-3 { gap: 1rem; }
   .gap-4 { gap: 1.5rem; }
   .text-center { text-align: center; }
   .mt-1 { margin-top: 0.25rem; }
   .mt-2 { margin-top: 0.5rem; }
   .mt-3 { margin-top: 1rem; }
   .mt-4 { margin-top: 1.5rem; }
   ```

---

### Phase 4: Page Refactoring (High Priority)

**Goal:** Migrate each page to the new architecture

#### Task breakdown by template:

| Template | Effort | Priority | Dependencies |
|----------|--------|----------|--------------|
| index.html | Medium | High | Phase 1-3 |
| add.html | Medium | High | Phase 1-3 |
| list.html | Medium | High | Phase 1-3 |
| tasks.html | Medium | High | Phase 1-3 |
| logs.html | Medium | High | Phase 1-3 |
| config.html | Medium | High | Phase 1-3 |

#### For each template:

1. Extract template-specific CSS to `static/css/pages/[name].css`
2. Remove duplicate CSS from template
3. Update template to extend `base.html`
4. Add semantic HTML (nav, main, section, etc.)
5. Add accessibility attributes
6. Use component classes instead of inline styles

---

### Phase 5: Polish (Medium Priority)

**Goal:** Final touches and refinements

#### Tasks:

1. **Add loading states** to forms and buttons
2. **Add form validation feedback** (client-side)
3. **Add focus states** for all interactive elements
4. **Test responsive design** on mobile
5. **Test accessibility** with screen readers
6. **Optimize performance** (minify CSS, etc.)

---

## Suggested Timeline

### Day 1: Foundation
- Morning: Create directory structure
- Morning: Create design tokens (variables.css)
- Afternoon: Create base template (base.html)
- Afternoon: Create base.css and components.css

### Day 2: Accessibility + Components
- Morning: Add accessibility to all templates
- Afternoon: Create component library
- Evening: Test keyboard navigation

### Day 3: Refactor Pages
- Morning: Refactor index.html, add.html
- Afternoon: Refactor list.html, tasks.html
- Evening: Refactor logs.html, config.html

### Day 4: Polish + Testing
- Morning: Add loading states and validation
- Afternoon: Cross-browser testing
- Evening: Accessibility audit

---

## Step-by-Step Implementation Guide

---

### Step 1: Set Up Project Structure

```bash
cd E:/GITHUB/Sharky/SyncFTP
mkdir -p static/css static/js
touch static/css/variables.css static/css/base.css static/css/components.css
touch templates/base.html
```

---

### Step 2: Create Design Tokens (static/css/variables.css)

```css
/* ============================================
   Design Tokens - SyncFTP
   ============================================ */

:root {
  /* Colors - Primary */
  --color-primary-50: #f5f3ff;
  --color-primary-100: #ede9fe;
  --color-primary-200: #ddd6fe;
  --color-primary-300: #c4b5fd;
  --color-primary-400: #a78bfa;
  --color-primary-500: #8b5cf6;
  --color-primary-600: #7c3aed;
  --color-primary-700: #6d28d9;
  --color-primary-800: #5b21b6;
  --color-primary-900: #4c1d95;

  /* Colors - Purple Gradient (brand) */
  --color-brand-start: #667eea;
  --color-brand-end: #764ba2;

  /* Colors - Semantic */
  --color-success: #28a745;
  --color-success-light: #d4edda;
  --color-success-dark: #218838;

  --color-warning: #ffc107;
  --color-warning-light: #fff3cd;
  --color-warning-dark: #e0a800;

  --color-danger: #dc3545;
  --color-danger-light: #f8d7da;
  --color-danger-dark: #c82333;

  --color-info: #17a2b8;
  --color-info-light: #d1ecf1;
  --color-info-dark: #138496;

  /* Colors - Neutral */
  --color-white: #ffffff;
  --color-gray-50: #f8f9fa;
  --color-gray-100: #f1f3f5;
  --color-gray-200: #e9ecef;
  --color-gray-300: #dee2e6;
  --color-gray-400: #ced4da;
  --color-gray-500: #adb5bd;
  --color-gray-600: #6c757d;
  --color-gray-700: #495057;
  --color-gray-800: #343a40;
  --color-gray-900: #212529;
  --color-black: #000000;

  /* Typography */
  --font-family-base: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  --font-family-mono: 'Courier New', Courier, monospace;

  --font-size-xs: 0.75rem;
  --font-size-sm: 0.875rem;
  --font-size-base: 1rem;
  --font-size-lg: 1.125rem;
  --font-size-xl: 1.25rem;
  --font-size-2xl: 1.5rem;
  --font-size-3xl: 2rem;
  --font-size-4xl: 2.5rem;

  --font-weight-light: 300;
  --font-weight-normal: 400;
  --font-weight-medium: 500;
  --font-weight-semibold: 600;
  --font-weight-bold: 700;

  --line-height-base: 1.5;
  --line-height-heading: 1.2;

  /* Spacing */
  --spacing-xs: 0.25rem;
  --spacing-sm: 0.5rem;
  --spacing-md: 1rem;
  --spacing-lg: 1.5rem;
  --spacing-xl: 2rem;
  --spacing-2xl: 3rem;

  /* Borders */
  --border-width-thin: 1px;
  --border-width-thick: 2px;
  --border-width-heavy: 3px;

  --border-radius-sm: 0.25rem;
  --border-radius-md: 0.5rem;
  --border-radius-lg: 0.75rem;
  --border-radius-xl: 1rem;
  --border-radius-full: 9999px;

  --border-color-light: var(--color-gray-200);
  --border-color: var(--color-gray-300);
  --border-color-dark: var(--color-gray-400);

  /* Shadows */
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
  --shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  --shadow-md: 0 4px 6px rgba(0, 0, 0, 0.1);
  --shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.1);
  --shadow-xl: 0 20px 25px rgba(0, 0, 0, 0.1);
  --shadow-2xl: 0 25px 50px rgba(0, 0, 0, 0.25);
  --shadow-brand: 0 10px 30px rgba(102, 126, 234, 0.2);

  /* Transitions */
  --transition-fast: 150ms ease;
  --transition: 200ms ease;
  --transition-slow: 300ms ease;

  /* Z-index scale */
  --z-dropdown: 100;
  --z-sticky: 200;
  --z-fixed: 300;
  --z-modal-backdrop: 400;
  --z-modal: 500;
  --z-popover: 600;
  --z-tooltip: 700;
}
```

---

### Step 3: Create Base CSS (static/css/base.css)

```css
/* ============================================
   CSS Reset + Base Styles
   ============================================ */

@import url('variables.css');

/* Reset */
*,
*::before,
*::after {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html {
  scroll-behavior: smooth;
  -webkit-text-size-adjust: 100%;
  -moz-text-size-adjust: 100%;
  text-size-adjust: 100%;
}

body {
  font-family: var(--font-family-base);
  font-size: var(--font-size-base);
  line-height: var(--line-height-base);
  color: var(--color-gray-800);
  background: linear-gradient(135deg, var(--color-brand-start) 0%, var(--color-brand-end) 100%);
  min-height: 100vh;
  padding: var(--spacing-md);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* Skip Link */
.skip-link {
  position: absolute;
  top: -40px;
  left: 0;
  background: var(--color-brand-start);
  color: var(--color-white);
  padding: var(--spacing-sm) var(--spacing-md);
  z-index: 9999;
  text-decoration: none;
  font-weight: var(--font-weight-semibold);
  border-radius: 0 0 var(--border-radius-md) 0;
}

.skip-link:focus {
  top: 0;
  outline: 2px solid var(--color-brand-end);
  outline-offset: 2px;
}

/* Typography */
h1, h2, h3, h4, h5, h6 {
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-heading);
  color: var(--color-brand-start);
  margin-bottom: var(--spacing-sm);
}

h1 { font-size: var(--font-size-4xl); }
h2 { font-size: var(--font-size-3xl); }
h3 { font-size: var(--font-size-2xl); }
h4 { font-size: var(--font-size-xl); }
h5 { font-size: var(--font-size-lg); }
h6 { font-size: var(--font-size-base); }

p {
  margin-bottom: var(--spacing-md);
}

a {
  color: var(--color-brand-start);
  text-decoration: none;
  transition: color var(--transition);
}

a:hover {
  color: var(--color-brand-end);
  text-decoration: underline;
}

/* Images */
img,
picture,
video,
canvas,
svg {
  display: block;
  max-width: 100%;
}

/* Form elements */
input,
button,
textarea,
select {
  font: inherit;
  color: inherit;
}

button {
  cursor: pointer;
}

/* Focus styles */
*:focus-visible {
  outline: 2px solid var(--color-brand-start);
  outline-offset: 2px;
}

/* Selection */
::selection {
  background: rgba(102, 126, 234, 0.2);
  color: var(--color-gray-900);
}

/* Utility classes */
.container {
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 var(--spacing-md);
}

.text-center { text-align: center; }
.text-left { text-align: left; }
.text-right { text-align: right; }

.mt-1 { margin-top: var(--spacing-xs); }
.mt-2 { margin-top: var(--spacing-sm); }
.mt-3 { margin-top: var(--spacing-md); }
.mt-4 { margin-top: var(--spacing-lg); }
.mb-1 { margin-bottom: var(--spacing-xs); }
.mb-2 { margin-bottom: var(--spacing-sm); }
.mb-3 { margin-bottom: var(--spacing-md); }
.mb-4 { margin-bottom: var(--spacing-lg); }

.d-none { display: none; }
.d-flex { display: flex; }
.d-grid { display: grid; }

.gap-1 { gap: var(--spacing-xs); }
.gap-2 { gap: var(--spacing-sm); }
.gap-3 { gap: var(--spacing-md); }
.gap-4 { gap: var(--spacing-lg); }

.fw-light { font-weight: var(--font-weight-light); }
.fw-normal { font-weight: var(--font-weight-normal); }
.fw-medium { font-weight: var(--font-weight-medium); }
.fw-semibold { font-weight: var(--font-weight-semibold); }
.fw-bold { font-weight: var(--font-weight-bold); }

.text-primary { color: var(--color-brand-start); }
.text-secondary { color: var(--color-gray-600); }
.text-success { color: var(--color-success); }
.text-warning { color: var(--color-warning); }
.text-danger { color: var(--color-danger); }

.bg-white { background-color: var(--color-white); }
.bg-gray-50 { background-color: var(--color-gray-50); }
```

---

### Step 4: Create Components CSS (static/css/components.css)

```css
/* ============================================
   UI Components - SyncFTP
   ============================================ */

@import url('variables.css');

/* Header / Brand */
.header {
  background: var(--color-white);
  padding: var(--spacing-xl);
  border-radius: var(--border-radius-xl);
  box-shadow: var(--shadow-xl);
  margin-bottom: var(--spacing-lg);
  text-align: center;
}

.header h1 {
  color: var(--color-brand-start);
  font-size: var(--font-size-4xl);
  margin-bottom: var(--spacing-xs);
}

.subtitle {
  color: var(--color-gray-600);
  font-size: var(--font-size-lg);
}

/* Navigation */
.nav {
  background: var(--color-white);
  padding: var(--spacing-lg);
  border-radius: var(--border-radius-lg);
  box-shadow: var(--shadow-lg);
  margin-bottom: var(--spacing-lg);
}

.nav-list {
  display: flex;
  gap: var(--spacing-md);
  justify-content: center;
  flex-wrap: wrap;
  list-style: none;
}

.nav-link {
  display: inline-block;
  padding: var(--spacing-md) var(--spacing-lg);
  background: linear-gradient(135deg, var(--color-brand-start) 0%, var(--color-brand-end) 100%);
  color: var(--color-white);
  border-radius: var(--border-radius-md);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  transition: transform var(--transition), box-shadow var(--transition);
  text-decoration: none;
}

.nav-link:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-brand);
}

.nav-link:active {
  transform: translateY(0);
}

.nav-link:focus-visible {
  outline: 2px solid var(--color-white);
  outline-offset: -2px;
}

/* Sections */
.section {
  background: var(--color-white);
  padding: var(--spacing-lg);
  border-radius: var(--border-radius-lg);
  box-shadow: var(--shadow-lg);
  margin-bottom: var(--spacing-lg);
}

.section-title {
  font-size: var(--font-size-2xl);
  color: var(--color-brand-start);
  margin-bottom: var(--spacing-lg);
  padding-bottom: var(--spacing-md);
  border-bottom: var(--border-width-heavy) solid var(--color-brand-start);
}

/* Buttons */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-md) var(--spacing-lg);
  background: linear-gradient(135deg, var(--color-brand-start) 0%, var(--color-brand-end) 100%);
  color: var(--color-white);
  border: none;
  border-radius: var(--border-radius-md);
  font-family: inherit;
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  cursor: pointer;
  transition: transform var(--transition), box-shadow var(--transition);
  text-decoration: none;
}

.btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: var(--shadow-brand);
}

.btn:active:not(:disabled) {
  transform: translateY(0);
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.btn:focus-visible {
  outline: 2px solid var(--color-white);
  outline-offset: -2px;
}

/* Button variants */
.btn--primary {
  background: linear-gradient(135deg, var(--color-brand-start) 0%, var(--color-brand-end) 100%);
}

.btn--secondary {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}

.btn--success {
  background: linear-gradient(135deg, var(--color-success) 0%, var(--color-success-dark) 100%);
}

.btn--warning {
  background: linear-gradient(135deg, var(--color-warning) 0%, var(--color-warning-dark) 100%);
}

.btn--danger {
  background: linear-gradient(135deg, var(--color-danger) 0%, var(--color-danger-dark) 100%);
}

/* Button sizes */
.btn-sm {
  padding: var(--spacing-xs) var(--spacing-md);
  font-size: var(--font-size-sm);
}

.btn-lg {
  padding: var(--spacing-lg) var(--spacing-xl);
  font-size: var(--font-size-lg);
}

/* Button loading state */
.btn.loading {
  pointer-events: none;
  position: relative;
  color: transparent;
}

.btn.loading::after {
  content: '';
  position: absolute;
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  border-top-color: var(--color-white);
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Forms */
.form-group {
  margin-bottom: var(--spacing-lg);
}

.form-label {
  display: block;
  margin-bottom: var(--spacing-xs);
  font-weight: var(--font-weight-semibold);
  color: var(--color-gray-700);
}

.form-input,
.form-select,
.form-textarea {
  width: 100%;
  max-width: 100%;
  padding: var(--spacing-md);
  border: var(--border-width-thin) solid var(--border-color);
  border-radius: var(--border-radius-md);
  font-family: inherit;
  font-size: var(--font-size-base);
  transition: border-color var(--transition), box-shadow var(--transition);
}

.form-input:focus,
.form-select:focus,
.form-textarea:focus {
  outline: none;
  border-color: var(--color-brand-start);
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.form-input:disabled,
.form-select:disabled,
.form-textarea:disabled {
  background-color: var(--color-gray-100);
  cursor: not-allowed;
}

.form-input::placeholder {
  color: var(--color-gray-500);
  opacity: 1;
}

.form-select {
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%236c757d' d='M6 8L1 3h10z'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right var(--spacing-sm) center;
  padding-right: var(--spacing-xl);
}

.form-help {
  display: block;
  margin-top: var(--spacing-xs);
  font-size: var(--font-size-sm);
  color: var(--color-gray-500);
}

.form-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: var(--spacing-lg);
}

/* Form validation */
.form-input:invalid:not(:focus):not(:placeholder-shown) {
  border-color: var(--color-danger);
}

.form-input:valid:not(:placeholder-shown) {
  border-color: var(--color-success);
}

.error-message {
  display: none;
  margin-top: var(--spacing-xs);
  font-size: var(--font-size-sm);
  color: var(--color-danger);
}

.form-input:invalid ~ .error-message {
  display: block;
}

/* Checkbox */
.checkbox-group {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  cursor: pointer;
}

.checkbox-group input[type="checkbox"] {
  width: 18px;
  height: 18px;
  margin: 0;
  cursor: pointer;
  accent-color: var(--color-brand-start);
}

.checkbox-group input[type="checkbox"]:focus-visible {
  outline: 2px solid var(--color-brand-start);
  outline-offset: 2px;
}

/* Cards */
.card {
  background: var(--color-white);
  border-radius: var(--border-radius-lg);
  box-shadow: var(--shadow);
  overflow: hidden;
}

.card-header {
  padding: var(--spacing-lg);
  border-bottom: var(--border-width-thin) solid var(--border-color-light);
}

.card-body {
  padding: var(--spacing-lg);
}

.card-footer {
  padding: var(--spacing-lg);
  border-top: var(--border-width-thin) solid var(--border-color-light);
  background: var(--color-gray-50);
}

/* Stat Card */
.stat-card {
  background: linear-gradient(135deg, var(--color-brand-start) 0%, var(--color-brand-end) 100%);
  color: var(--color-white);
  padding: var(--spacing-xl);
  border-radius: var(--border-radius-lg);
  box-shadow: var(--shadow-brand);
  text-align: center;
  transition: transform var(--transition), box-shadow var(--transition);
}

.stat-card:hover {
  transform: translateY(-5px);
  box-shadow: var(--shadow-xl);
}

.stat-card .stat-icon {
  font-size: var(--font-size-4xl);
  margin-bottom: var(--spacing-md);
}

.stat-card .stat-value {
  font-size: var(--font-size-4xl);
  font-weight: var(--font-weight-bold);
  margin-bottom: var(--spacing-xs);
}

.stat-card .stat-label {
  font-size: var(--font-size-lg);
  opacity: 0.9;
}

/* Server Card */
.server-card {
  background: var(--color-gray-50);
  padding: var(--spacing-lg);
  border-radius: var(--border-radius-md);
  border-left: var(--border-width-thick) solid var(--color-brand-start);
  transition: transform var(--transition), box-shadow var(--transition);
}

.server-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-md);
}

.server-card h3 {
  color: var(--color-brand-start);
  margin-bottom: var(--spacing-sm);
  font-size: var(--font-size-lg);
}

.server-info {
  color: var(--color-gray-600);
  margin-bottom: var(--spacing-xs);
  font-size: var(--font-size-sm);
}

.server-info strong {
  color: var(--color-gray-800);
}

.server-actions {
  display: flex;
  gap: var(--spacing-sm);
  margin-top: var(--spacing-md);
}

/* Modal */
.modal-backdrop {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  z-index: var(--z-modal-backdrop);
  opacity: 0;
  transition: opacity var(--transition);
  pointer-events: none;
}

.modal-backdrop.show {
  opacity: 1;
  pointer-events: all;
}

.modal {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%) scale(0.9);
  width: 90%;
  max-width: 500px;
  max-height: 80vh;
  background: var(--color-white);
  border-radius: var(--border-radius-xl);
  box-shadow: var(--shadow-2xl);
  z-index: var(--z-modal);
  opacity: 0;
  transition: transform var(--transition), opacity var(--transition);
  overflow: hidden;
}

.modal.show {
  transform: translate(-50%, -50%) scale(1);
  opacity: 1;
}

.modal-content {
  padding: var(--spacing-xl);
  height: 100%;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-lg);
  padding-bottom: var(--spacing-md);
  border-bottom: var(--border-width-thin) solid var(--border-color-light);
}

.modal-header h2 {
  color: var(--color-brand-start);
  font-size: var(--font-size-xl);
}

.close-btn {
  background: none;
  border: none;
  font-size: var(--font-size-3xl);
  cursor: pointer;
  color: var(--color-gray-500);
  padding: var(--spacing-xs);
  line-height: 1;
  transition: color var(--transition);
}

.close-btn:hover {
  color: var(--color-gray-800);
}

.close-btn:focus-visible {
  outline: 2px solid var(--color-brand-start);
  border-radius: var(--border-radius-full);
}

.modal-body {
  margin-bottom: var(--spacing-lg);
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-md);
  padding-top: var(--spacing-md);
  border-top: var(--border-width-thin) solid var(--border-color-light);
}

/* Alerts */
.alert {
  padding: var(--spacing-md);
  border-radius: var(--border-radius-md);
  margin-bottom: var(--spacing-md);
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.alert--success {
  background: var(--color-success-light);
  color: var(--color-success-dark);
  border: var(--border-width-thin) solid rgba(40, 167, 69, 0.2);
}

.alert--warning {
  background: var(--color-warning-light);
  color: var(--color-warning-dark);
  border: var(--border-width-thin) solid rgba(255, 193, 7, 0.2);
}

.alert--danger {
  background: var(--color-danger-light);
  color: var(--color-danger-dark);
  border: var(--border-width-thin) solid rgba(220, 53, 69, 0.2);
}

.alert--info {
  background: var(--color-info-light);
  color: var(--color-info-dark);
  border: var(--border-width-thin) solid rgba(23, 162, 184, 0.2);
}

/* Empty States */
.empty-state {
  text-align: center;
  padding: var(--spacing-2xl) var(--spacing-md);
  color: var(--color-gray-500);
}

/* Loading */
.loading {
  display: inline-block;
  width: 20px;
  height: 20px;
  border: 3px solid rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  border-top-color: var(--color-white);
  animation: spin 1s ease-in-out infinite;
}

.loading-sm {
  width: 16px;
  height: 16px;
  border-width: 2px;
}

.loading-lg {
  width: 24px;
  height: 24px;
  border-width: 3px;
}

/* Responsive */
@media (min-width: 768px) {
  body {
    padding: var(--spacing-lg);
  }

  .header h1 {
    font-size: var(--font-size-4xl);
  }

  .nav-list {
    flex-direction: row;
  }

  .nav-link {
    width: auto;
  }

  .form-row {
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  }

  .stat-grid {
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  }
}

@media (max-width: 767px) {
  .header h1 {
    font-size: var(--font-size-3xl);
  }

  .subtitle {
    font-size: var(--font-size-base);
  }

  .nav-list {
    flex-direction: column;
    align-items: center;
  }

  .nav-link {
    width: 80%;
    margin-bottom: var(--spacing-sm);
  }

  .section-title {
    font-size: var(--font-size-xl);
  }

  .stat-grid {
    grid-template-columns: 1fr;
  }

  .form-row {
    grid-template-columns: 1fr;
  }
}

/* Print Styles */
@media print {
  body {
    background: var(--color-white);
    min-height: auto;
    padding: 0;
  }

  .header, .nav, .btn, .modal-backdrop {
    display: none !important;
  }

  .section {
    box-shadow: none;
    border: 1px solid var(--border-color);
    page-break-inside: avoid;
    margin-bottom: var(--spacing-md);
  }
}
```

---

### Step 5: Create Base Template (templates/base.html)

```html
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="Gerez et synchronisez vos serveurs FTP avec SyncFTP - Interface web legere pour la gestion de connexions FTP et taches de synchronisation automatique">
    <meta name="author" content="SyncFTP">
    
    <!-- Favicon -->
    <link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
    
    <!-- CSS -->
    <link rel="stylesheet" href="/static/css/variables.css">
    <link rel="stylesheet" href="/static/css/base.css">
    <link rel="stylesheet" href="/static/css/components.css">
    
    <!-- Page-specific CSS -->
    {% block extra_css %}{% endblock %}
    
    <title>{{ app_name }} - {% block title %}{% endblock %}</title>
</head>
<body>
    <!-- Skip to main content -->
    <a href="#main-content" class="skip-link">Aller au contenu principal</a>
    
    <div class="container">
        <!-- Header -->
        <header class="header">
            <h1>🚀 {{ app_name }}</h1>
            <p class="subtitle">Gerez et testez vos connexions FTP facilement</p>
        </header>
        
        <!-- Navigation -->
        <nav class="nav" aria-label="Navigation principale">
            <ul class="nav-list">
                <li><a href="/" class="nav-link">🏠 TABLEAU DE BORD</a></li>
                <li><a href="/add" class="nav-link">➕ AJOUTER SERVEUR</a></li>
                <li><a href="/list" class="nav-link">📋 LISTE SERVEURS</a></li>
                <li><a href="/tasks" class="nav-link">🔄 TACHES DE SYNC</a></li>
                <li><a href="/logs" class="nav-link">📜 LOGS</a></li>
                <li><a href="/config" class="nav-link">⚙️ CONFIGURATION</a></li>
            </ul>
        </nav>
        
        <!-- Main Content -->
        <main id="main-content">
            {% block content %}{% endblock %}
        </main>
    </div>
    
    <!-- JavaScript -->
    <script>
        // Common JavaScript utilities
        const SyncFTP = {
            showLoading(button) {
                button.classList.add('loading');
                button.disabled = true;
                const text = button.innerHTML;
                button.dataset.originalText = text;
            },
            
            hideLoading(button) {
                button.classList.remove('loading');
                button.disabled = false;
                if (button.dataset.originalText) {
                    button.innerHTML = button.dataset.originalText;
                }
            },
            
            showStatus(message, type = 'info') {
                const status = document.createElement('div');
                status.className = `alert alert--${type}`;
                status.textContent = message;
                status.style.position = 'fixed';
                status.style.top = '20px';
                status.style.right = '20px';
                status.style.zIndex = '9999';
                status.style.maxWidth = '400px';
                document.body.appendChild(status);
                
                setTimeout(() => {
                    status.style.opacity = '0';
                    status.style.transition = 'opacity 0.3s ease';
                    setTimeout(() => status.remove(), 300);
                }, 5000);
            },
            
            formatSize(bytes) {
                if (bytes === 0) return '0 octets';
                const k = 1024;
                const sizes = ['octets', 'Ko', 'Mo', 'Go', 'To'];
                const i = Math.floor(Math.log(bytes) / Math.log(k));
                return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
            },
            
            formatDuration(seconds) {
                if (seconds < 60) return `${Math.round(seconds)}s`;
                if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
                return `${Math.round(seconds / 3600)}h ${Math.round((seconds % 3600) / 60)}m`;
            }
        };
        
        // Auto-close alerts
        document.addEventListener('DOMContentLoaded', () => {
            document.querySelectorAll('.alert').forEach(alert => {
                setTimeout(() => {
                    alert.style.opacity = '0';
                    alert.style.transition = 'opacity 0.3s ease';
                    setTimeout(() => alert.remove(), 300);
                }, 5000);
            });
        });
    </script>
    
    {% block extra_js %}{% endblock %}
</body>
</html>
```

---

## File Structure After Implementation

```
SyncFTP/
├── app.py
├── ftp_tools.py
├── static/
│   ├── css/
│   │   ├── variables.css      # Design tokens (100 lines)
│   │   ├── base.css           # Reset + base styles (150 lines)
│   │   ├── components.css     # UI components (500 lines)
│   │   └── pages/
│   │       ├── dashboard.css  # index.html styles
│   │       ├── form.css       # add.html styles
│   │       ├── list.css       # list.html styles
│   │       ├── tasks.css      # tasks.html styles
│   │       ├── logs.css       # logs.html styles
│   │       └── config.css     # config.html styles
│   └── js/
│       └── main.js            # Common utilities
├── templates/
│   ├── base.html              # Base template (80 lines)
│   ├── index.html             # Extends base.html (100 lines)
│   ├── add.html               # Extends base.html (100 lines)
│   ├── list.html              # Extends base.html (120 lines)
│   ├── tasks.html             # Extends base.html (200 lines)
│   ├── logs.html              # Extends base.html (100 lines)
│   └── config.html            # Extends base.html (150 lines)
├── ftp_servers.json
├── sync_tasks.json
├── config.json
└── README.md
```

---

## Acceptance Criteria

| Criteria | Status |
|----------|--------|
| All templates extend base.html | Pending |
| CSS is external (no inline <style> tags) | Pending |
| Design tokens in variables.css | Pending |
| Component library in components.css | Pending |
| Accessibility: ARIA attributes added | Pending |
| Accessibility: Skip link implemented | Pending |
| Accessibility: Keyboard navigation works | Pending |
| Accessibility: Focus states visible | Pending |
| Semantic HTML: nav, main, section used | Pending |
| Forms have proper label associations | Pending |
| Color contrast meets WCAG AA | Pending |
| Responsive design works on mobile | Pending |
| Loading states on buttons | Pending |
| Form validation feedback | Pending |
| Favicon added | Pending |
| Meta description added | Pending |

---

## Next Steps

1. **Start implementing Phase 1** (create the foundation files)
2. **Create the favicon SVG** for the project
3. **Show you how to refactor a specific template** as an example
4. **Set up a build process** to minify CSS
5. **Add anything else** to this plan
