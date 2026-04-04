/**
 * ═══════════════════════════════════════════════════════════
 *  V-OFFLINE CHAT — App JavaScript
 *  Theme toggle, notifications, global interactions
 * ═══════════════════════════════════════════════════════════
 */

// ── Theme Management ────────────────────────────────────────
function getTheme() {
    return localStorage.getItem('v-offline-theme') || 'dark';
}

function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('v-offline-theme', theme);
    const btn = document.getElementById('themeToggleBtn');
    if (btn) {
        const icon = btn.querySelector('.material-icons-round');
        icon.textContent = theme === 'dark' ? 'light_mode' : 'dark_mode';
    }
}

function toggleTheme() {
    const current = getTheme();
    setTheme(current === 'dark' ? 'light' : 'dark');
}

// Initialize theme on load
document.addEventListener('DOMContentLoaded', () => {
    setTheme(getTheme());
});


// ── Dropdown Toggle ─────────────────────────────────────────
function toggleDropdown(btn) {
    const menu = btn.closest('.dropdown').querySelector('.dropdown-menu');
    menu.classList.toggle('show');

    // Close on outside click
    const closeHandler = (e) => {
        if (!btn.closest('.dropdown').contains(e.target)) {
            menu.classList.remove('show');
            document.removeEventListener('click', closeHandler);
        }
    };
    setTimeout(() => document.addEventListener('click', closeHandler), 0);
}


// ── Browser Notifications ───────────────────────────────────
function requestNotificationPermission() {
    if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission();
    }
}

function showNotification(title, body, icon) {
    if ('Notification' in window && Notification.permission === 'granted') {
        new Notification(title, {
            body: body,
            icon: icon || '/static/img/default-avatar.svg',
            badge: '/static/img/default-avatar.svg',
        });
    }
}

document.addEventListener('DOMContentLoaded', requestNotificationPermission);


// ── Mobile Chat Toggle ──────────────────────────────────────
function closeChatMobile() {
    const app = document.getElementById('chatApp');
    if (app) {
        app.classList.remove('chat-open');
    }
}

// Auto-open chat on mobile if conversation is active
document.addEventListener('DOMContentLoaded', () => {
    const app = document.getElementById('chatApp');
    if (app && app.dataset.conversationId) {
        app.classList.add('chat-open');
    }
});


// ── Media Viewer ────────────────────────────────────────────
function openMediaViewer(src) {
    const viewer = document.getElementById('mediaViewer');
    const img = document.getElementById('mediaViewerImg');
    if (viewer && img) {
        img.src = src;
        viewer.style.display = 'flex';
    }
}

function closeMediaViewer() {
    const viewer = document.getElementById('mediaViewer');
    if (viewer) viewer.style.display = 'none';
}

// Close on Escape
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeMediaViewer();
    }
});


// ── Sidebar Chat Search ─────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('chatSearchInput');
    if (!searchInput) return;

    searchInput.addEventListener('input', () => {
        const query = searchInput.value.toLowerCase();
        const items = document.querySelectorAll('.conversation-item');
        items.forEach(item => {
            const name = item.querySelector('.conv-name')?.textContent.toLowerCase() || '';
            const preview = item.querySelector('.conv-preview')?.textContent.toLowerCase() || '';
            item.style.display = (name.includes(query) || preview.includes(query)) ? '' : 'none';
        });
    });
});


// ── Textarea Auto-resize ────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    const textarea = document.getElementById('messageInput');
    if (!textarea) return;

    textarea.addEventListener('input', () => {
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
    });
});

// ── Onboarding & Demo Experience ────────────────────────────
let currentOnboardingSlide = 0;

function showOnboardingSlide(index) {
    const slides = document.querySelectorAll('.onboarding-slide');
    const dots = document.querySelectorAll('.onboarding-dots .dot');

    if (!slides.length) return;

    slides.forEach(s => s.classList.remove('active'));
    dots.forEach(d => d.classList.remove('active'));

    slides[index].classList.add('active');
    dots[index].classList.add('active');
    currentOnboardingSlide = index;
}

window.nextOnboardingSlide = function () {
    const slides = document.querySelectorAll('.onboarding-slide');
    if (currentOnboardingSlide < slides.length - 1) {
        showOnboardingSlide(currentOnboardingSlide + 1);
    }
};

window.prevOnboardingSlide = function () {
    if (currentOnboardingSlide > 0) {
        showOnboardingSlide(currentOnboardingSlide - 1);
    }
};

window.goToSlide = function (index) {
    showOnboardingSlide(index);
};

window.closeOnboarding = function () {
    const modal = document.getElementById('onboardingModal');
    if (modal) modal.style.display = 'none';
    localStorage.setItem('v-offline_onboarded', 'true');
};

window.playDemoVideo = function () {
    const container = document.querySelector('.demo-video-container');
    if (container) {
        container.innerHTML = `
            <div style="padding: 2rem; text-align: center; color: var(--text-dim); display:flex; flex-direction:column; justify-content:center; height:100%;">
                <span class="material-icons-round" style="font-size: 3rem; margin-bottom: 1rem; color: var(--primary-color);">videocam</span>
                <p>Record your demo using the provided script and place it at</p>
                <code style="background: rgba(0,0,0,0.3); padding: 0.5rem; border-radius: 5px; margin-top: 0.5rem; color: #fff;">/media/demo/nexus_demo.mp4</code>
                <p style="margin-top: 1rem; font-size: 0.85rem;">Update app.js once recorded to play the local file!</p>
            </div>
        `;
    }
};

document.addEventListener('DOMContentLoaded', () => {
    // Check if user has seen onboarding before
    const hasSeenOnboarding = localStorage.getItem('v-offline_onboarded');
    const modal = document.getElementById('onboardingModal');

    // Only show automatically if we are on the main chat interface
    const isChatRoute = window.location.pathname.startsWith('/chat');

    if (!hasSeenOnboarding && modal && isChatRoute) {
        // Slight delay for smooth loading experience
        setTimeout(() => {
            modal.style.display = 'flex';
        }, 1000);
    }
});
