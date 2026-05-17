

document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
});


function initializeApp() {
    
    setupHTMX();
    
    
    setupKeyboardShortcuts();
    
    
    setupAnimations();
}


function setupHTMX() {
    
    htmx.config.timeout = 30000; 
    htmx.config.refreshOnHistoryMiss = true;
    
    
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


function setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            const searchInput = document.getElementById('query-input');
            if (searchInput) searchInput.focus();
        }
        
        
        if (e.key === 'Escape') {
            closeAllModals();
        }
    });
}


function setupAnimations() {
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-fadeIn');
            }
        });
    });
    
    document.querySelectorAll('.dark-card').forEach(el => observer.observe(el));
}


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


function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'fixed top-4 right-4 space-y-2 z-50';
    document.body.appendChild(container);
    return container;
}


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


function formatDate(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}


async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        showToast('✅ Copied to clipboard!', 'success', 2000);
    } catch (err) {
        showToast('❌ Failed to copy', 'error', 2000);
    }
}


function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}


function sanitizeHTML(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}


function formatResponse(text) {
    return text
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        .replace(/`(.+?)`/g, '<code>$1</code>')
        .replace(/\n/g, '<br>');
}


async function checkHealth() {
    try {
        const response = await fetch('/health');
        return response.ok;
    } catch {
        return false;
    }
}


window.addEventListener('error', (event) => {
    console.error('Global error:', event.error);
    showToast('⚠️ An error occurred. Please refresh the page.', 'error', 5000);
});


window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled promise rejection:', event.reason);
    showToast('⚠️ An error occurred. Please refresh the page.', 'error', 5000);
});


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
