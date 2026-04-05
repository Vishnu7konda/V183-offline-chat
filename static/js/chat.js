/**
 * V-OFFLINE CHAT - Chat JavaScript
 * WebSocket messaging with JWT auth, presence system, typing indicators,
 * emoji picker, media upload with progress
 */

(function () {
    'use strict';

    const app = document.getElementById('chatApp');
    if (!app) return;

    const username = app.dataset.user;
    const userId = app.dataset.userId;
    const conversationId = app.dataset.conversationId;
    const messagesArea = document.getElementById('messagesArea');
    const messageInput = document.getElementById('messageInput');
    const sendBtn = document.getElementById('sendBtn');

    let chatSocket = null;  // kept for legacy references, not used for send/recv
    let typingTimeout = null;
    let jwtToken = null;
    let currentUploadXHR = null;
    let heartbeatInterval = null;
    let refreshInProgress = false;
    let lastMessageId = 0;  // tracks highest message id seen, for polling
    let pollInterval = null;

    // ──── JWT Token Fetch ────────────────────────────────────────────
    async function fetchJWT() {
        try {
            const resp = await fetch('/accounts/token/');
            if (resp.ok) {
                const data = await resp.json();
                jwtToken = data.token;
            }
        } catch (e) {
            console.warn('[Nexus] JWT fetch failed, using session auth');
        }
    }

    // ──── HTTP Chat (replaces WebSocket on Vercel) ─────────────────────────
    // WebSockets are not supported on Vercel serverless. We use:
    // - POST /chat/<id>/send/ to send messages
    // - GET  /chat/<id>/poll/?after=<id> every 3s to get new messages
    function connectWebSocket() {
        if (!conversationId) return;
        // Seed lastMessageId from existing DOM messages so we don't re-render history
        document.querySelectorAll('[data-msg-id]').forEach(el => {
            const id = parseInt(el.dataset.msgId, 10);
            if (id > lastMessageId) lastMessageId = id;
        });
        startMessagePolling();
    }

    async function startMessagePolling() {
        if (!conversationId) return;
        await fetchNewMessages();  // immediate first fetch
        pollInterval = setInterval(fetchNewMessages, 3000);
    }

    async function fetchNewMessages() {
        try {
            const resp = await fetch(`/chat/${conversationId}/poll/?after=${lastMessageId}`, {
                credentials: 'same-origin'
            });
            if (!resp.ok) return;
            const data = await resp.json();
            (data.messages || []).forEach(msg => {
                if (msg.id > lastMessageId) lastMessageId = msg.id;
                // Only append messages from others (own messages shown immediately on send)
                if (msg.sender !== username) {
                    appendMessage(msg);
                    scrollToBottom();
                    showNotification(msg.sender, msg.content);
                }
            });
        } catch (e) {
            // Silent - likely offline
        }
    }

    function handleSocketMessage(data) {
        switch (data.type) {
            case 'message':
                appendMessage(data.message);
                scrollToBottom();
                if (data.message.sender !== username) {
                    showNotification(data.message.sender, data.message.content);
                    // Automatically send delivery receipt
                    sendDeliveryReceipt(data.message.id);
                    // Automatically send read receipt if tab is focused
                    if (document.hasFocus()) {
                        sendReadReceipt();
                    }
                }
                break;
            case 'typing':
                showTyping(data.username);
                break;
            case 'read_receipt':
                markMessagesRead(data);
                break;
            case 'delivery_receipt':
                markMessagesDelivered(data);
                break;
            case 'reaction':
                updateReaction(data);
                break;
            case 'edited':
                editMessageDOM(data);
                break;
            case 'deleted':
                deleteMessageDOM(data);
                break;
            case 'status':
                updateUserStatus(data);
                break;
        }
    }

    // ──── HTTP Presence Polling (replaces WebSocket presence) ────────
    // Vercel serverless doesn't support persistent WebSockets, so we
    // poll /discovery/heartbeat/ via HTTP every 30 seconds instead.
    async function pollHeartbeat(isManual) {
        const btn = document.getElementById('nearbyRefreshBtn');
        const icon = btn ? btn.querySelector('.material-icons-round') : null;
        const stamp = document.getElementById('nearbyLastUpdated');

        if (isManual) {
            if (refreshInProgress) return;
            refreshInProgress = true;
            if (icon) icon.style.animation = 'spin 0.7s linear infinite';
        }

        try {
            const resp = await fetch('/discovery/heartbeat/', {
                method: 'GET',
                credentials: 'same-origin',
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });
            if (resp.ok) {
                const data = await resp.json();
                renderNearbyDevices(data.devices || []);
                updateActiveNodeStatus(data.devices || []);
                if (stamp) {
                    const now = new Date();
                    stamp.textContent = 'Updated ' + now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                    stamp.style.display = 'block';
                }
            }
        } catch (e) {
            console.warn('[Nexus] Heartbeat poll failed:', e);
        } finally {
            refreshInProgress = false;
            if (icon) icon.style.animation = '';
        }
    }

    function startHeartbeatPolling() {
        pollHeartbeat(false); // immediate first poll
        heartbeatInterval = setInterval(() => pollHeartbeat(false), 30000);
    }

    // Exposed so the HTML refresh button can call it
    window.refreshNearbyDevices = function() { pollHeartbeat(true); };

    // ──── Nearby Devices Rendering ───────────────────────────────────
    function renderNearbyDevices(users) {
        const list = document.getElementById('nearbyDeviceList');
        const badge = document.getElementById('nearbyCountBadge');
        if (!list) return;

        if (users && users.length > 0) {
            list.innerHTML = '';
            users.forEach(d => {
                const card = document.createElement('a');
                card.href = `/chat/start/${d.user_id}/`;
                card.className = 'nearby-device-card clickable-node';
                card.style.textDecoration = 'none';
                card.style.display = 'flex';
                card.style.alignItems = 'center';
                card.style.gap = '12px';
                card.style.padding = '12px';
                card.style.borderRadius = 'var(--r-md)';
                card.style.transition = 'background 0.2s ease';
                
                card.innerHTML = `
                    <img src="${d.avatar}" class="nearby-avatar" alt="" style="width:40px; height:40px; border-radius:50%;">
                    <div class="nearby-device-info" style="flex:1;">
                        <h4 style="margin:0; font-size:0.95rem; color:var(--text-primary); font-weight:600;">${escapeHtml(d.username)}</h4>
                        <span class="nearby-ip" style="font-size:0.8rem; color:var(--text-muted); font-family:monospace;">${d.ip}</span>
                    </div>
                    <div class="nearby-chat-btn" style="color:var(--accent);">
                        <span class="material-icons-round">chat</span>
                    </div>
                `;
                list.appendChild(card);
            });

            if (badge) {
                badge.textContent = users.length;
                badge.style.display = 'inline-flex';
            }
        } else {
            list.innerHTML = `
                <div class="empty-state nearby-empty">
                    <span class="material-icons-round">radar</span>
                    <p>No nearby devices found</p>
                </div>
            `;
            if (badge) badge.style.display = 'none';
        }
    }

    window.toggleNearbyPanel = function () {
        const body = document.getElementById('nearbyPanelBody');
        const icon = document.getElementById('nearbyToggleIcon');
        if (!body) return;
        const isOpen = body.style.display !== 'none';
        body.style.display = isOpen ? 'none' : 'block';
        if (icon) icon.textContent = isOpen ? 'expand_more' : 'expand_less';
    };

    // ──── Message Display ────────────────────────────────────────────
    function appendMessage(data) {
        if (!messagesArea) return;
        const emptyState = messagesArea.querySelector('.empty-state');
        if (emptyState) emptyState.remove();

        // Check for duplicate message (from upload broadcast)
        if (messagesArea.querySelector(`[data-msg-id="${data.id}"]`)) return;

        const isSent = data.sender === username;
        const div = document.createElement('div');
        div.className = `message ${isSent ? 'sent' : 'received'}`;
        div.dataset.msgId = data.id;
        div.dataset.sender = data.sender;

        let contentHtml = '';
        if (data.message_type === 'image' && data.media_url) {
            contentHtml = `<div class="msg-media"><img src="${data.media_url}" alt="Image" loading="lazy" onclick="openMediaViewer(this.src)"></div>`;
        } else if (data.message_type === 'video' && data.media_url) {
            contentHtml = `<div class="msg-media"><video src="${data.media_url}" controls></video></div>`;
        } else if (data.message_type === 'document' && data.media_url) {
            contentHtml = `<a href="${data.media_url}" class="msg-document" target="_blank"><span class="material-icons-round">description</span> ${escapeHtml(data.content || 'Document')}</a>`;
        } else if (data.message_type === 'system') {
            contentHtml = `<p class="msg-system">${escapeHtml(data.content)}</p>`;
        } else {
            contentHtml = `<p class="msg-text">${escapeHtml(data.content)}</p>`;
        }

        const time = new Date(data.timestamp).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
        const statusHtml = isSent
            ? `<span class="msg-status"><span class="material-icons-round">done</span></span>`
            : '';

        div.innerHTML = `
            ${!isSent && data.sender_avatar ? `<img src="${data.sender_avatar}" alt="" class="msg-avatar">` : ''}
            <div class="msg-bubble">
                ${contentHtml}
                <div class="msg-meta">
                    <span class="msg-time">${time}</span>
                    ${statusHtml}
                </div>
            </div>
        `;

        messagesArea.appendChild(div);
    }

    // ──── Send Message (HTTP POST) ───────────────────────────────
    window.sendMessage = async function () {
        if (!messageInput || !conversationId) return;
        const content = messageInput.value.trim();
        if (!content) return;

        // Optimistic UI — show message immediately
        const tempId = 'tmp_' + Date.now();
        const optimistic = {
            id: tempId, sender: username, content: content,
            message_type: 'text', timestamp: new Date().toISOString()
        };
        appendMessage(optimistic);
        scrollToBottom();
        messageInput.value = '';
        messageInput.style.height = 'auto';
        messageInput.focus();

        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value
            || document.cookie.match(/csrftoken=([^;]+)/)?.[1] || '';

        try {
            const resp = await fetch(`/chat/${conversationId}/send/`, {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({ content })
            });
            if (resp.ok) {
                const data = await resp.json();
                // Replace temp element with real message id
                const tempEl = document.querySelector(`[data-msg-id="${tempId}"]`);
                if (tempEl && data.message?.id) {
                    tempEl.dataset.msgId = data.message.id;
                    if (data.message.id > lastMessageId) lastMessageId = data.message.id;
                }
            } else {
                // Remove optimistic on failure
                document.querySelector(`[data-msg-id="${tempId}"]`)?.remove();
                showNotification('System', 'Message failed to send');
            }
        } catch (e) {
            document.querySelector(`[data-msg-id="${tempId}"]`)?.remove();
            showNotification('System', 'Network error — message not sent');
        }
    };

    window.handleKeyDown = function (e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    };

    // ──── Typing Indicator ───────────────────────────────────────────
    window.handleTyping = function () {
        if (!chatSocket) return;
        chatSocket.send(JSON.stringify({ type: 'typing' }));

        if (typingTimeout) clearTimeout(typingTimeout);
        typingTimeout = setTimeout(() => { }, 3000);
    };

    function showTyping(sender) {
        if (sender === username) return;
        const indicator = document.getElementById('typingIndicator');
        const nameEl = document.getElementById('typingUser');
        if (indicator && nameEl) {
            nameEl.textContent = sender;
            indicator.style.display = 'flex';
            setTimeout(() => { if (indicator) indicator.style.display = 'none'; }, 3000);
        }
    }

    // ──── Read Receipts ──────────────────────────────────────────────
    function sendReadReceipt() {
        if (!chatSocket || chatSocket.readyState !== WebSocket.OPEN) return;
        chatSocket.send(JSON.stringify({
            type: 'read_receipt'
        }));
    }

    function sendDeliveryReceipt(msgId) {
        if (!chatSocket || chatSocket.readyState !== WebSocket.OPEN) return;
        chatSocket.send(JSON.stringify({
            type: 'delivery_receipt',
            message_id: msgId
        }));
    }

    function updateActiveNodeStatus(users) {
        if (!conversationId) return;
        const otherUserId = document.getElementById('chatApp').dataset.activeOtherUserId;
        if (!otherUserId) return;
        
        const isOnline = users.some(u => u.user_id.toString() === otherUserId);
        const dot = document.getElementById('headerStatusDot');
        const status = document.getElementById('chatHeaderStatus');
        if (dot) dot.className = `status-dot ${isOnline ? 'online' : ''}`;
        if (status) status.textContent = isOnline ? 'Active Node' : 'Offline';
    }

    // Send read receipt on focus
    window.addEventListener('focus', () => {
        if (conversationId) sendReadReceipt();
    });

    // ──── Message Actions ────────────────────────────────────────────
    window.reactToMessage = function (msgId, emoji) {
        if (!chatSocket) return;
        emoji = emoji || prompt('Enter an emoji:');
        if (!emoji) return;
        chatSocket.send(JSON.stringify({
            type: 'reaction',
            message_id: msgId,
            emoji: emoji,
        }));
    };

    window.editMessage = function (msgId) {
        if (!chatSocket) return;
        const msgEl = document.querySelector(`[data-msg-id="${msgId}"] .msg-text`);
        if (!msgEl) return;
        const newContent = prompt('Edit message:', msgEl.textContent);
        if (newContent !== null && newContent.trim()) {
            chatSocket.send(JSON.stringify({
                type: 'edit',
                message_id: msgId,
                content: newContent.trim(),
            }));
        }
    };

    window.deleteMessage = function (msgId) {
        if (!chatSocket) return;
        if (confirm('Delete this message?')) {
            chatSocket.send(JSON.stringify({
                type: 'delete',
                message_id: msgId,
            }));
        }
    };

    // ──── DOM Updates ────────────────────────────────────────────────
    function markMessagesRead(data) {
        // Turn all ticks blue
        const selector = data.message_id ? `[data-msg-id="${data.message_id}"]` : '.message.sent';
        const messages = document.querySelectorAll(selector);
        messages.forEach(msg => {
            const tick = msg.querySelector('.msg-status .material-icons-round');
            if (tick) {
                tick.textContent = 'done_all';
                tick.style.color = 'var(--accent)';
                tick.classList.add('read');
            }
        });
    }

    function markMessagesDelivered(data) {
        // Turn ticks to double grey if not already blue
        const selector = data.message_id ? `[data-msg-id="${data.message_id}"]` : '.message.sent';
        const messages = document.querySelectorAll(selector);
        messages.forEach(msg => {
            const tick = msg.querySelector('.msg-status .material-icons-round');
            if (tick && !tick.classList.contains('read')) {
                tick.textContent = 'done_all';
                tick.style.color = 'var(--text-muted)';
            }
        });
    }

    function updateReaction(data) {
        const msgEl = document.querySelector(`[data-msg-id="${data.message_id}"]`);
        if (!msgEl) return;
        let reactionsDiv = msgEl.querySelector('.msg-reactions');
        if (!reactionsDiv) {
            reactionsDiv = document.createElement('div');
            reactionsDiv.className = 'msg-reactions';
            msgEl.querySelector('.msg-bubble').appendChild(reactionsDiv);
        }
        reactionsDiv.innerHTML = '';
        if (data.reactions) {
            for (const [emoji, users] of Object.entries(data.reactions)) {
                const chip = document.createElement('span');
                chip.className = 'reaction-chip';
                chip.textContent = `${emoji} ${users.length}`;
                chip.onclick = () => reactToMessage(data.message_id, emoji);
                reactionsDiv.appendChild(chip);
            }
        }
    }

    function editMessageDOM(data) {
        const msgEl = document.querySelector(`[data-msg-id="${data.message_id}"] .msg-text`);
        if (msgEl) {
            msgEl.textContent = data.content;
            const bubble = msgEl.closest('.msg-bubble');
            if (!bubble.querySelector('.msg-edited-tag')) {
                const tag = document.createElement('span');
                tag.className = 'msg-edited-tag';
                tag.textContent = 'edited';
                bubble.appendChild(tag);
            }
        }
    }

    function deleteMessageDOM(data) {
        const msgEl = document.querySelector(`[data-msg-id="${data.message_id}"]`);
        if (msgEl) {
            msgEl.classList.add('deleted');
            const bubble = msgEl.querySelector('.msg-bubble');
            bubble.innerHTML = '<p class="msg-deleted"><span class="material-icons-round">block</span> This message was deleted</p>';
        }
    }

    function updateUserStatus(data) {
        const dot = document.getElementById('headerStatusDot');
        const status = document.getElementById('chatHeaderStatus');
        if (dot) dot.className = `status-dot ${data.is_online ? 'online' : ''}`;
        if (status) status.textContent = data.is_online ? 'Online' : 'Offline';
    }

    // ──── Group Management ───────────────────────────────────────────
    window.openNewGroupModal = function() {
        const modal = document.getElementById('groupModal');
        if (modal) modal.style.display = 'flex';
    };

    window.closeGroupModal = function() {
        const modal = document.getElementById('groupModal');
        if (modal) modal.style.display = 'none';
    };

    window.createGroup = async function() {
        const nameInput = document.getElementById('groupNameInput');
        const checkboxes = document.querySelectorAll('.participant-checkbox:checked');
        
        if (!nameInput.value.trim()) {
            alert('Please specify a Team Node identifier (Group Name)');
            return;
        }
        
        if (checkboxes.length < 1) {
            alert('Select at least one participant to form a collective node');
            return;
        }

        const participants = Array.from(checkboxes).map(cb => cb.value);
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value 
            || document.cookie.match(/csrftoken=([^;]+)/)?.[1] || '';

        try {
            const resp = await fetch('/chat/group/create/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    name: nameInput.value.trim(),
                    participants: participants
                })
            });

            if (resp.ok) {
                const data = await resp.json();
                location.href = `/chat/${data.id}/`;
            } else {
                alert('Initialization failed. Check network integrity.');
            }
        } catch (e) {
            alert('Communication error during initialization.');
        }
    };

    // ──── Notifications ──────────────────────────────────────────────
    function getNotificationStatus() {
        return localStorage.getItem('v-offline-notifications') !== 'false';
    }

    window.toggleNotifications = function() {
        const current = getNotificationStatus();
        localStorage.setItem('v-offline-notifications', !current);
        updateNotifToggleIcon();
        
        // Show a quick status toast
        showNotification('System', `Notifications ${!current ? 'Enabled' : 'Disabled'}`);
    };

    function updateNotifToggleIcon() {
        const btn = document.getElementById('notifToggleBtn');
        if (btn) {
            const icon = btn.querySelector('.material-icons-round');
            icon.textContent = getNotificationStatus() ? 'notifications' : 'notifications_off';
            btn.style.color = getNotificationStatus() ? 'var(--accent)' : 'var(--text-muted)';
        }
    }

    function showNotification(sender, content) {
        if (!getNotificationStatus() && sender !== 'System') return;

        const stack = document.getElementById('chatNotificationsStack');
        if (!stack) return;

        const alert = document.createElement('div');
        alert.className = 'alert animate-fade-in-up';
        alert.style.cursor = 'pointer';
        alert.onclick = () => alert.remove();
        
        alert.innerHTML = `
            <span class="material-icons-round">${sender === 'System' ? 'info' : 'chat_bubble'}</span>
            <p><strong>${sender}:</strong> ${content || 'New transmission detected'}</p>
        `;

        stack.appendChild(alert);

        // Auto-hide after 2 seconds
        setTimeout(() => {
            alert.classList.add('animate-fade-out');
            setTimeout(() => alert.remove(), 500);
        }, 2000);

        // Also trigger native if permission granted
        if ('Notification' in window && Notification.permission === 'granted' && sender !== 'System') {
            new Notification(`${sender}`, { body: content || 'New message', icon: '/static/img/default-avatar.svg' });
        }
    }

    // Initial icon state
    updateNotifToggleIcon();

    // Request notification permission
    if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission();
    }

    // ──── Emoji Picker ───────────────────────────────────────────────
    const emojis = ['😀', '😂', '😍', '🥰', '😎', '🤔', '👍', '👎', '❤️', '🔥', '🎉', '😢', '😡', '🤣', '✨', '💯', '🙏', '👋', '💪', '🤝', '😊', '🥺', '😤', '🤩', '😴', '🤮', '👀', '💀', '🫡', '🎶'];

    window.toggleEmojiPicker = function () {
        const picker = document.getElementById('emojiPicker');
        if (!picker) return;
        picker.style.display = picker.style.display === 'none' ? 'flex' : 'none';
        if (picker.style.display === 'flex' && !picker.dataset.loaded) {
            const grid = document.getElementById('emojiGrid');
            emojis.forEach(e => {
                const btn = document.createElement('button');
                btn.className = 'emoji-item';
                btn.textContent = e;
                btn.onclick = () => {
                    messageInput.value += e;
                    messageInput.focus();
                };
                grid.appendChild(btn);
            });
            picker.dataset.loaded = 'true';
        }
    };

    // ──── Message Search ─────────────────────────────────────────────
    window.toggleMessageSearch = function () {
        const bar = document.getElementById('messageSearchBar');
        if (bar) {
            bar.style.display = bar.style.display === 'none' ? 'flex' : 'none';
            if (bar.style.display === 'flex') bar.querySelector('input').focus();
        }
    };

    // ──── Media Upload with Progress ─────────────────────────────────
    window.uploadMedia = function (input) {
        if (!input.files.length || !conversationId) return;

        const file = input.files[0];
        const maxSize = 10 * 1024 * 1024; // 10 MB
        if (file.size > maxSize) {
            alert('File too large. Maximum size is 10 MB.');
            input.value = '';
            return;
        }

        const formData = new FormData();
        formData.append('media', file);

        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value
            || document.cookie.match(/csrftoken=([^;]+)/)?.[1] || '';

        // Show progress bar
        const progressBar = document.getElementById('uploadProgressBar');
        const progressFill = document.getElementById('uploadProgressFill');
        const progressPercent = document.getElementById('uploadProgressPercent');
        const fileName = document.getElementById('uploadFileName');

        if (progressBar) progressBar.style.display = 'flex';
        if (fileName) fileName.textContent = `Uploading: ${file.name}`;
        if (progressFill) progressFill.style.width = '0%';
        if (progressPercent) progressPercent.textContent = '0%';

        const xhr = new XMLHttpRequest();
        currentUploadXHR = xhr;

        xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable) {
                const pct = Math.round((e.loaded / e.total) * 100);
                if (progressFill) progressFill.style.width = pct + '%';
                if (progressPercent) progressPercent.textContent = pct + '%';
            }
        });

        xhr.addEventListener('load', () => {
            currentUploadXHR = null;
            if (progressBar) progressBar.style.display = 'none';

            if (xhr.status >= 200 && xhr.status < 300) {
                // Message will arrive via WebSocket broadcast — no need to append here
                console.log('[Nexus] File uploaded successfully');
            } else {
                try {
                    const errData = JSON.parse(xhr.responseText);
                    alert(errData.error || 'Upload failed');
                } catch (_) {
                    alert('Upload failed');
                }
            }
        });

        xhr.addEventListener('error', () => {
            currentUploadXHR = null;
            if (progressBar) progressBar.style.display = 'none';
            alert('Upload failed. Please try again.');
        });

        xhr.open('POST', `/chat/${conversationId}/upload/`);
        xhr.setRequestHeader('X-CSRFToken', csrfToken);
        xhr.send(formData);

        input.value = '';
    };

    window.cancelUpload = function () {
        if (currentUploadXHR) {
            currentUploadXHR.abort();
            currentUploadXHR = null;
        }
        const progressBar = document.getElementById('uploadProgressBar');
        if (progressBar) progressBar.style.display = 'none';
    };

    // ──── Utilities ──────────────────────────────────────────────────
    function scrollToBottom() {
        if (messagesArea) {
            messagesArea.scrollTop = messagesArea.scrollHeight;
        }
    }

    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // ──── Media Viewer ───────────────────────────────────────────────
    window.openMediaViewer = function (src) {
        const viewer = document.getElementById('mediaViewer');
        const img = document.getElementById('mediaViewerImg');
        if (viewer && img) {
            img.src = src;
            viewer.style.display = 'flex';
        }
    };

    window.closeMediaViewer = function () {
        const viewer = document.getElementById('mediaViewer');
        if (viewer) viewer.style.display = 'none';
    };

    // ──── Mobile helpers ─────────────────────────────────────────────
    window.closeChatMobile = function () {
        const sidebar = document.getElementById('sidebar');
        const main = document.getElementById('chatMain');
        if (sidebar) sidebar.style.display = 'flex';
        if (main) main.style.display = 'none';
    };

    window.toggleDropdown = function (btn) {
        const menu = btn.nextElementSibling;
        if (menu) menu.classList.toggle('show');
    };

    // Close dropdowns on outside click
    document.addEventListener('click', (e) => {
        document.querySelectorAll('.dropdown-menu.show').forEach(menu => {
            if (!menu.parentElement.contains(e.target)) {
                menu.classList.remove('show');
            }
        });
    });

    // ──── Init ───────────────────────────────────────────────────────
    async function init() {
        scrollToBottom();
        await fetchJWT();
        connectWebSocket();
        startHeartbeatPolling();
        
        // Auto-hide any server-rendered messages
        const existingAlerts = document.querySelectorAll('#chatNotificationsStack .alert');
        existingAlerts.forEach(alert => {
            setTimeout(() => {
                alert.classList.add('animate-fade-out');
                setTimeout(() => alert.remove(), 500);
            }, 2000);
        });
    }

    init();

})();

// ──── Global Feature Handlers ─────────────────────────────────────
window.openNewGroupModal = function() {
    const modal = document.getElementById('groupModal');
    if (modal) modal.style.display = 'flex';
};

window.closeGroupModal = function() {
    const modal = document.getElementById('groupModal');
    if (modal) modal.style.display = 'none';
};

window.createGroup = async function() {
    const nameInput = document.getElementById('groupNameInput');
    const checkboxes = document.querySelectorAll('.participant-checkbox:checked');
    
    if (!nameInput.value.trim()) {
        alert('Please specify a Team Node identifier (Group Name)');
        return;
    }
    
    if (checkboxes.length < 1) {
        alert('Select at least one participant to form a collective node');
        return;
    }

    const participants = Array.from(checkboxes).map(cb => cb.value);
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value 
        || document.cookie.match(/csrftoken=([^;]+)/)?.[1] || '';

    try {
        const resp = await fetch('/chat/group/create/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                name: nameInput.value.trim(),
                participants: participants
            })
        });

        if (resp.ok) {
            const data = await resp.json();
            location.href = `/chat/${data.id}/`;
        } else {
            alert('Initialization failed. Check network integrity.');
        }
    } catch (e) {
        alert('Communication error during initialization.');
    }
};

