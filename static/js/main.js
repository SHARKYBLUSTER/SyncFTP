/**
 * SyncFTP - Main JavaScript
 * Handles loading states, form validation, and accessibility features
 */

(function() {
    'use strict';

    // ========================================
    // Utility Functions
    // ========================================

    /**
     * Announce message to screen readers
     * @param {string} message - Message to announce
     * @param {string} [priority='polite'] - 'polite' or 'assertive'
     */
    function announceToScreenReader(message, priority = 'polite') {
        const announcer = document.getElementById('announcements');
        if (!announcer) return;
        
        announcer.setAttribute('aria-live', priority);
        announcer.textContent = message;
        
        // Clear after announcement to allow repeated announcements
        setTimeout(() => {
            announcer.textContent = '';
        }, 1000);
    }

    /**
     * Toggle loading state for a button
     * @param {HTMLElement|string} button - Button element or selector
     * @param {boolean} [loading=true] - Whether to show loading state
     */
    function toggleButtonLoading(button, loading = true) {
        const btn = typeof button === 'string' ? document.querySelector(button) : button;
        if (!btn) return;
        
        if (loading) {
            btn.classList.add('is-loading');
            btn.setAttribute('aria-busy', 'true');
            btn.setAttribute('disabled', 'disabled');
        } else {
            btn.classList.remove('is-loading');
            btn.removeAttribute('aria-busy');
            btn.removeAttribute('disabled');
        }
    }

    /**
     * Show loading overlay on a form or container
     * @param {HTMLElement|string} container - Container element or selector
     * @param {boolean} [show=true] - Whether to show overlay
     */
    function toggleLoadingOverlay(container, show = true) {
        const cont = typeof container === 'string' ? document.querySelector(container) : container;
        if (!cont) return;
        
        let overlay = cont.querySelector('.loading-overlay');
        if (show && !overlay) {
            overlay = document.createElement('div');
            overlay.className = 'loading-overlay';
            overlay.innerHTML = '<div class="spinner spinner-sm"></div>';
            cont.style.position = 'relative';
            cont.appendChild(overlay);
            cont.setAttribute('aria-busy', 'true');
        } else if (!show && overlay) {
            overlay.remove();
            cont.removeAttribute('aria-busy');
        }
    }

    /**
     * Validate form field and show feedback
     * @param {HTMLElement} input - Input element
     * @param {Function} validator - Validation function that returns { isValid: boolean, message: string }
     */
    function validateField(input, validator) {
        const formGroup = input.closest('.form-group') || input.parentElement;
        let feedback = formGroup.querySelector('.form-error, .form-success');
        
        // Remove existing feedback
        if (feedback) {
            feedback.remove();
        }
        
        // Remove validation classes
        input.classList.remove('form-control--error', 'form-control--success', 'form-control--warning');
        formGroup.classList.remove('has-error', 'has-success');
        
        const result = validator(input.value);
        const fieldName = input.getAttribute('name') || input.getAttribute('id') || 'ce champ';
        
        if (!result.isValid && input.required) {
            // Required field validation
            input.classList.add('form-control--error');
            formGroup.classList.add('has-error');
            feedback = document.createElement('div');
            feedback.className = 'form-error';
            feedback.setAttribute('role', 'alert');
            feedback.setAttribute('id', `${input.id || fieldName}-error`);
            input.setAttribute('aria-invalid', 'true');
            input.setAttribute('aria-describedby', feedback.id);
            feedback.textContent = result.message || `Veuillez remplir ${fieldName}`;
            formGroup.appendChild(feedback);
            return false;
        } else if (!result.isValid) {
            // Custom validation failed
            input.classList.add('form-control--warning');
            formGroup.classList.add('has-error');
            feedback = document.createElement('div');
            feedback.className = 'form-error';
            feedback.setAttribute('role', 'alert');
            feedback.setAttribute('id', `${input.id || fieldName}-error`);
            input.setAttribute('aria-invalid', 'true');
            input.setAttribute('aria-describedby', feedback.id);
            feedback.textContent = result.message || `Format de ${fieldName} invalide`;
            formGroup.appendChild(feedback);
            return false;
        } else {
            // Validation passed
            input.classList.add('form-control--success');
            formGroup.classList.add('has-success');
            feedback = document.createElement('div');
            feedback.className = 'form-success';
            feedback.setAttribute('id', `${input.id || fieldName}-success`);
            input.removeAttribute('aria-invalid');
            input.setAttribute('aria-describedby', feedback.id);
            feedback.textContent = result.message || `Format de ${fieldName} valide`;
            formGroup.appendChild(feedback);
            return true;
        }
    }

    /**
     * Debounce function for performance
     */
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    // ========================================
    // Auto-Init Features
    // ========================================

    /**
     * Auto-init loading states for forms
     */
    function initFormLoadingStates() {
        document.querySelectorAll('form[data-loading="true"]').forEach(form => {
            form.addEventListener('submit', function(e) {
                const submitBtn = this.querySelector('button[type="submit"], input[type="submit"]');
                if (submitBtn) {
                    toggleButtonLoading(submitBtn, true);
                    // Re-enable button if form submission is prevented
                    setTimeout(() => {
                        toggleButtonLoading(submitBtn, false);
                    }, 5000);
                }
            });
        });
    }

    /**
     * Auto-init validation for forms with data-validate attribute
     */
    function initFormValidation() {
        document.querySelectorAll('input[data-validate]').forEach(input => {
            const validateType = input.getAttribute('data-validate');
            let validator;
            
            switch(validateType) {
                case 'email':
                    validator = (value) => {
                        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
                        return {
                            isValid: emailRegex.test(value) || !value,
                            message: 'Veuillez entrer une adresse email valide'
                        };
                    };
                    break;
                case 'url':
                    validator = (value) => {
                        try {
                            new URL(value);
                            return { isValid: true };
                        } catch {
                            return {
                                isValid: !value,
                                message: 'Veuillez entrer une URL valide'
                            };
                        }
                    };
                    break;
                case 'number':
                    validator = (value) => {
                        return {
                            isValid: !value || !isNaN(parseFloat(value)) && isFinite(value),
                            message: 'Veuillez entrer un nombre valide'
                        };
                    };
                    break;
                case 'required':
                    validator = (value) => {
                        return {
                            isValid: !!value || !input.required,
                            message: 'Ce champ est obligatoire'
                        };
                    };
                    break;
                default:
                    // Custom validation function (if provided in data-validate)
                    try {
                        validator = window[validateType] || (() => ({ isValid: true }));
                    } catch {
                        validator = () => ({ isValid: true });
                    }
            }
            
            if (validator) {
                // Validate on blur
                input.addEventListener('blur', () => {
                    validateField(input, validator);
                });
                
                // Validate on change (debounced)
                input.addEventListener('input', debounce(() => {
                    if (input.value) {
                        validateField(input, validator);
                    }
                }, 300));
            }
        });
    }

    /**
     * Auto-init accessibility features
     */
    function initAccessibility() {
        // Ensure all interactive elements are keyboard accessible
        document.querySelectorAll('button, [role="button"], a, [tabindex]:not([tabindex="-1"])).forEach(el => {
            if (!el.hasAttribute('tabindex')) {
                el.setAttribute('tabindex', '0');
            }
        });
        
        // Add aria-labels to icon-only buttons
        document.querySelectorAll('button.icon-only, .btn-icon').forEach(btn => {
            if (!btn.getAttribute('aria-label') && btn.textContent.trim() === '') {
                const icon = btn.querySelector('.icon, i');
                if (icon) {
                    const iconName = icon.getAttribute('aria-hidden') || 
                                   icon.getAttribute('aria-label') || 
                                   icon.textContent || 
                                   'bouton';
                    btn.setAttribute('aria-label', iconName);
                }
            }
        });
    }

    /**
     * Handle page load announcements
     */
    function announcePageLoaded() {
        const pageTitle = document.title;
        const mainContent = document.getElementById('main-content');
        if (mainContent) {
            const heading = mainContent.querySelector('h1, h2, h3');
            if (heading) {
                announceToScreenReader(`Page ${heading.textContent} chargée. ${pageTitle}`);
            }
        }
    }

    // ========================================
    // Initialize on DOM Ready
    // ========================================

    function init() {
        // Initialize accessibility features first
        initAccessibility();
        
        // Initialize form validation
        initFormValidation();
        
        // Initialize loading states
        initFormLoadingStates();
        
        // Announce page load (delayed to allow content to render)
        setTimeout(announcePageLoaded, 500);
        
        // Add global loading state utilities
        window.SyncFTP = window.SyncFTP || {};
        window.SyncFTP.toggleButtonLoading = toggleButtonLoading;
        window.SyncFTP.toggleLoadingOverlay = toggleLoadingOverlay;
        window.SyncFTP.announce = announceToScreenReader;
        window.SyncFTP.validateField = validateField;
    }

    // Run initialization
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Also run on Turbo/HTMX navigation if present
    if (window.Turbo) {
        document.addEventListener('turbo:load', init);
    }
    if (window.htmx) {
        document.body.addEventListener('htmx:afterSettle', init);
    }
})();

// ========================================
// Custom Validators (can be extended)
// ========================================

/**
 * Validate FTP port number
 */
function validateFtpPort(value) {
    const port = parseInt(value, 10);
    return {
        isValid: !value || (port >= 1 && port <= 65535),
        message: 'Le port doit être compris entre 1 et 65535'
    };
}

/**
 * Validate FTP path
 */
function validateFtpPath(value) {
    if (!value) return { isValid: true };
    // Basic check for valid path characters
    const invalidChars = /[<>:"|?*]/;
    return {
        isValid: !invalidChars.test(value),
        message: 'Le chemin contient des caractères non valides'
    };
}
