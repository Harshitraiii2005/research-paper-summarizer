/**
 * PaperIntel AI - Frontend JavaScript
 * Handles interactions, animations, and HTMX integrations
 */

document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
});

/**
 * Initialize the application
 */
function initializeApp() {
    // Setup HTMX configurations
    setupHTMX();
    
    // Setup keyboard shortcuts
    setupKeyboardShortcuts();
    
    // Setup animations
    setupAnimations();
}

/**
 * Setup HTMX default configurations
 */
function setupHTMX() {
    // HTMX configuration
    htmx.config.timeout = 30000; // 30 second timeout
    htmx.config.refreshOnHistoryMiss = true;
    
    // Add loading class for animations
    document.body.addEventListener('htmx:xhr:loadstart', (e) => {
        e.detail.xhr.addEventListener('loadstart', () => {
            if (e.detail.xhr.method === 'GET') {
                e.detail.target.classList.add('opacity-50');
            }
        });
    });
    
    document.body.addEventListener('htmx:xhr:loadend', (e) => {
        if (e.detail.xhr.method === 'GET') {
            e.detail.target.classList.remove('opacity-50');
        }
    });
}

/**
 * Setup keyboard shortcuts
 */
function setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        // Ctrl+K or Cmd+K - Focus search
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            const searchInput = document.getElementById('query-input');
            if (searchInput) searchInput.focus();
        }
        
        // Escape - Close modals
        if (e.key === 'Escape') {
            closeAllModals();
        }
    });
}

/**
 * Setup animations
 */
function setupAnimations() {
    // Observe elements for fade-in animation
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-fadeIn');
            }
        });
    });
    
    document.querySelectorAll('.dark-card').forEach(el => observer.observe(el));
}

/**
 * Show toast notification
 */
function showToast(message, type = 'info', duration = 3000) {
    const toastContainer = document.getElementById('toast-container') || createToastContainer();
    
    const toast = document.createElement('div');
    toast.className = `alert alert-${type} animate-slideIn`;
    toast.textContent = message;
    
    toastContainer.appendChild(toast);
    
    setTimeout(() => {
        toast.classList.remove('animate-slideIn');
        toast.classList.add('opacity-0');
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

/**
 * Create toast container if it doesn't exist
 */
function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'fixed top-4 right-4 space-y-2 z-50';
    document.body.appendChild(container);
    return container;
}

/**
 * Close all modals
 */
function closeAllModals() {
    document.querySelectorAll('[role="dialog"]').forEach(modal => {
        if (modal.classList.contains('show')) {
            modal.classList.remove('show');
        }
    });
    
    document.querySelectorAll('#loading-modal, #error-modal').forEach(modal => {
        if (!modal.classList.contains('hidden')) {
            modal.classList.add('hidden');
        }
    });
}

/**
 * Debounce function for search
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

/**
 * Throttle function for scroll events
 */
function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

/**
 * Format date
 */
function formatDate(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

/**
 * Copy to clipboard
 */
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        showToast('✅ Copied to clipboard!', 'success', 2000);
    } catch (err) {
        showToast('❌ Failed to copy', 'error', 2000);
    }
}

/**
 * Format file size
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

/**
 * Sanitize HTML
 */
function sanitizeHTML(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

/**
 * Format text with markdown-like syntax
 */
function formatResponse(text) {
    return text
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        .replace(/`(.+?)`/g, '<code>$1</code>')
        .replace(/\n/g, '<br>');
}

/**
 * Check API health
 */
async function checkHealth() {
    try {
        const response = await fetch('/health');
        return response.ok;
    } catch {
        return false;
    }
}

/**
 * Setup error boundary
 */
window.addEventListener('error', (event) => {
    console.error('Global error:', event.error);
    showToast('⚠️ An error occurred. Please refresh the page.', 'error', 5000);
});

/**
 * Setup unhandled promise rejection handler
 */
window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled promise rejection:', event.reason);
    showToast('⚠️ An error occurred. Please refresh the page.', 'error', 5000);
});

// Export for use in templates
window.PaperIntel = {
    showToast,
    copyToClipboard,
    formatDate,
    formatFileSize,
    formatResponse,
    checkHealth,
    debounce,
    throttle
};
