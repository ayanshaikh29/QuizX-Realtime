/**
 * QuizX AI Chat - ChatGPT Style
 * Full-featured chat with history, file upload, typing animation
 */

(function () {
    'use strict';

    // ============================================================
    // STATE
    // ============================================================

    let chatSessions = JSON.parse(localStorage.getItem('quizx_chat_sessions') || '[]');
    let currentSessionId = null;
    let isTyping = false;
    let pendingFiles = [];

    // ============================================================
    // DOM ELEMENTS
    // ============================================================

    const sidebar = document.getElementById('chat-sidebar');
    const sidebarOverlay = document.getElementById('sidebar-overlay');
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const newChatBtn = document.getElementById('new-chat-btn');
    const historyList = document.getElementById('chat-history-list');
    const messagesArea = document.getElementById('chat-messages');
    const messagesContainer = document.getElementById('messages-container');
    const welcomeScreen = document.getElementById('welcome-screen');
    const chatTextarea = document.getElementById('chat-textarea');
    const sendBtn = document.getElementById('send-btn');
    const fileUploadInput = document.getElementById('file-upload-input');
    const imageUploadInput = document.getElementById('image-upload-input');
    const filePreviewArea = document.getElementById('file-preview-area');
    const scrollToBottomBtn = document.getElementById('scroll-to-bottom');
    const chatTitle = document.getElementById('chat-title');

    // ============================================================
    // INITIALIZATION
    // ============================================================

    function init() {
        renderHistory();
        setupEventListeners();
        autoResizeTextarea();

        // Load last session or show welcome
        if (chatSessions.length > 0) {
            loadSession(chatSessions[0].id);
        } else {
            showWelcome();
        }
    }

    // ============================================================
    // SESSION MANAGEMENT
    // ============================================================

    function createSession(firstMessage) {
        const id = 'session_' + Date.now();
        const title = firstMessage.slice(0, 40) + (firstMessage.length > 40 ? '...' : '');
        const session = {
            id,
            title,
            messages: [],
            createdAt: new Date().toISOString()
        };
        chatSessions.unshift(session);
        saveSessions();
        renderHistory();
        return id;
    }

    function loadSession(sessionId) {
        currentSessionId = sessionId;
        const session = getSession(sessionId);
        if (!session) return;

        // Update active state in sidebar
        document.querySelectorAll('.history-item').forEach(item => {
            item.classList.toggle('active', item.dataset.sessionId === sessionId);
        });

        // Update title
        chatTitle.textContent = session.title;

        // Render messages
        messagesContainer.innerHTML = '';
        welcomeScreen.style.display = 'none';
        messagesContainer.style.display = 'block';

        session.messages.forEach(msg => {
            renderMessage(msg.role, msg.content, msg.files, false);
        });

        scrollToBottom();
    }

    function getSession(sessionId) {
        return chatSessions.find(s => s.id === sessionId);
    }

    function addMessageToSession(sessionId, role, content, files) {
        const session = getSession(sessionId);
        if (!session) return;
        session.messages.push({
            role,
            content,
            files: files || [],
            timestamp: new Date().toISOString()
        });
        saveSessions();
    }

    function deleteSession(sessionId) {
        chatSessions = chatSessions.filter(s => s.id !== sessionId);
        saveSessions();
        renderHistory();

        if (currentSessionId === sessionId) {
            currentSessionId = null;
            if (chatSessions.length > 0) {
                loadSession(chatSessions[0].id);
            } else {
                showWelcome();
            }
        }
    }

    function saveSessions() {
        // Keep only last 50 sessions
        if (chatSessions.length > 50) {
            chatSessions = chatSessions.slice(0, 50);
        }
        localStorage.setItem('quizx_chat_sessions', JSON.stringify(chatSessions));
    }

    // ============================================================
    // RENDER FUNCTIONS
    // ============================================================

    function renderHistory() {
        historyList.innerHTML = '';

        if (chatSessions.length === 0) {
            historyList.innerHTML = '<div style="padding: 12px 16px; font-size: 0.75rem; color: var(--text-muted);">No conversations yet</div>';
            return;
        }

        chatSessions.forEach(session => {
            const item = document.createElement('div');
            item.className = 'history-item' + (session.id === currentSessionId ? ' active' : '');
            item.dataset.sessionId = session.id;
            item.innerHTML = `
                <i class="fas fa-comment history-item-icon"></i>
                <span class="history-item-text">${escapeHtml(session.title)}</span>
                <button class="history-item-delete" title="Delete">
                    <i class="fas fa-trash"></i>
                </button>
            `;

            item.addEventListener('click', (e) => {
                if (!e.target.closest('.history-item-delete')) {
                    loadSession(session.id);
                    closeSidebar();
                }
            });

            item.querySelector('.history-item-delete').addEventListener('click', (e) => {
                e.stopPropagation();
                if (confirm('Delete this conversation?')) {
                    deleteSession(session.id);
                }
            });

            historyList.appendChild(item);
        });
    }

    function showWelcome() {
        currentSessionId = null;
        chatTitle.textContent = 'QuizX AI';
        messagesContainer.innerHTML = '';
        messagesContainer.style.display = 'none';
        welcomeScreen.style.display = 'flex';

        // Update active state
        document.querySelectorAll('.history-item').forEach(item => {
            item.classList.remove('active');
        });
    }

    function renderMessage(role, content, files, animate = true) {
        const group = document.createElement('div');
        group.className = 'message-group' + (animate ? '' : ' no-animate');

        const row = document.createElement('div');
        row.className = 'message-row ' + role;

        const avatar = document.createElement('div');
        avatar.className = 'message-avatar ' + (role === 'bot' ? 'bot-avatar' : 'user-avatar');
        avatar.innerHTML = role === 'bot'
            ? '<i class="fas fa-robot"></i>'
            : '<i class="fas fa-user"></i>';

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';

        // Render files if any
        if (files && files.length > 0) {
            files.forEach(file => {
                if (file.type === 'image') {
                    const img = document.createElement('img');
                    img.src = file.data;
                    img.className = 'message-image';
                    img.alt = file.name;
                    contentDiv.appendChild(img);
                } else {
                    const fileEl = document.createElement('div');
                    fileEl.className = 'message-file';
                    fileEl.innerHTML = `<i class="fas fa-file"></i><span>${escapeHtml(file.name)}</span>`;
                    contentDiv.appendChild(fileEl);
                }
            });
        }

        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';
        bubble.innerHTML = parseMarkdown(content);

        const meta = document.createElement('div');
        meta.className = 'message-meta';

        const time = document.createElement('span');
        time.className = 'message-time';
        time.textContent = formatTime(new Date());

        const actions = document.createElement('div');
        actions.className = 'message-actions';
        actions.innerHTML = `
            <button class="msg-action-btn copy-btn" title="Copy">
                <i class="fas fa-copy"></i>
            </button>
        `;

        actions.querySelector('.copy-btn').addEventListener('click', () => {
            navigator.clipboard.writeText(content).then(() => {
                showToast('Copied!');
            });
        });

        meta.appendChild(time);
        meta.appendChild(actions);

        contentDiv.appendChild(bubble);
        contentDiv.appendChild(meta);

        row.appendChild(avatar);
        row.appendChild(contentDiv);
        group.appendChild(row);

        messagesContainer.appendChild(group);

        if (animate) {
            scrollToBottom();
        }

        return bubble;
    }

    function showTypingIndicator() {
        const indicator = document.createElement('div');
        indicator.className = 'typing-indicator';
        indicator.id = 'typing-indicator';

        const avatar = document.createElement('div');
        avatar.className = 'message-avatar bot-avatar';
        avatar.innerHTML = '<i class="fas fa-robot"></i>';

        const dots = document.createElement('div');
        dots.className = 'typing-dots';
        dots.innerHTML = '<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>';

        indicator.appendChild(avatar);
        indicator.appendChild(dots);
        messagesContainer.appendChild(indicator);
        scrollToBottom();

        return indicator;
    }

    function removeTypingIndicator() {
        const indicator = document.getElementById('typing-indicator');
        if (indicator) indicator.remove();
    }

    // ============================================================
    // TYPING ANIMATION
    // ============================================================

    function typeText(element, text, speed = 10) {
        return new Promise(resolve => {
            let i = 0;
            element.innerHTML = '';

            // Create a temporary container to hold the parsed HTML
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = parseMarkdown(text);
            const nodes = Array.from(tempDiv.childNodes);

            let nodeIndex = 0;

            function typeNode() {
                if (nodeIndex < nodes.length) {
                    const node = nodes[nodeIndex];
                    if (node.nodeType === Node.TEXT_NODE) {
                        let charIndex = 0;
                        const chars = node.textContent.split('');
                        const textNode = document.createTextNode('');
                        element.appendChild(textNode);

                        function typeChar() {
                            if (charIndex < chars.length) {
                                textNode.textContent += chars[charIndex];
                                charIndex++;
                                scrollToBottom();
                                setTimeout(typeChar, speed);
                            } else {
                                nodeIndex++;
                                typeNode();
                            }
                        }
                        typeChar();
                    } else {
                        // For non-text nodes (like <strong>, <code>, etc.), append them instantly or type their children
                        const clone = node.cloneNode(true);
                        element.appendChild(clone);
                        nodeIndex++;
                        scrollToBottom();
                        setTimeout(typeNode, speed * 2);
                    }
                } else {
                    resolve();
                }
            }

            typeNode();
        });
    }

    // ============================================================
    // SEND MESSAGE
    // ============================================================

    async function sendMessage() {
        const text = chatTextarea.value.trim();
        if ((!text && pendingFiles.length === 0) || isTyping) return;

        const files = [...pendingFiles];
        pendingFiles = [];
        clearFilePreview();

        chatTextarea.value = '';
        chatTextarea.style.height = 'auto';
        sendBtn.disabled = true;

        // Create session if needed
        if (!currentSessionId) {
            currentSessionId = createSession(text || 'File upload');
            welcomeScreen.style.display = 'none';
            messagesContainer.style.display = 'block';
        }

        // Add user message
        addMessageToSession(currentSessionId, 'user', text, files);
        renderMessage('user', text, files);

        // Show typing indicator
        isTyping = true;
        const typingEl = showTypingIndicator();

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: text,
                    session_id: currentSessionId,
                    has_files: files.length > 0
                })
            });

            const data = await response.json();
            removeTypingIndicator();

            if (!response.ok) {
                const errorMsg = "I encountered an error. Please try again.";
                addMessageToSession(currentSessionId, 'bot', errorMsg);
                renderMessage('bot', errorMsg);
            } else {
                const reply = data?.response?.reply || "I couldn't generate a response.";
                addMessageToSession(currentSessionId, 'bot', reply);

                // Render with typing animation
                const group = document.createElement('div');
                group.className = 'message-group';

                const row = document.createElement('div');
                row.className = 'message-row bot';

                const avatar = document.createElement('div');
                avatar.className = 'message-avatar bot-avatar';
                avatar.innerHTML = '<i class="fas fa-robot"></i>';

                const contentDiv = document.createElement('div');
                contentDiv.className = 'message-content';

                const bubble = document.createElement('div');
                bubble.className = 'message-bubble';

                const meta = document.createElement('div');
                meta.className = 'message-meta';
                const time = document.createElement('span');
                time.className = 'message-time';
                time.textContent = formatTime(new Date());
                const actions = document.createElement('div');
                actions.className = 'message-actions';
                actions.innerHTML = `<button class="msg-action-btn copy-btn" title="Copy"><i class="fas fa-copy"></i></button>`;
                actions.querySelector('.copy-btn').addEventListener('click', () => {
                    navigator.clipboard.writeText(reply).then(() => showToast('Copied!'));
                });
                meta.appendChild(time);
                meta.appendChild(actions);

                contentDiv.appendChild(bubble);
                contentDiv.appendChild(meta);
                row.appendChild(avatar);
                row.appendChild(contentDiv);
                group.appendChild(row);
                messagesContainer.appendChild(group);

                await typeText(bubble, reply, 12);
            }
        } catch (err) {
            removeTypingIndicator();
            const errorMsg = "Connection error. Please check your network.";
            addMessageToSession(currentSessionId, 'bot', errorMsg);
            renderMessage('bot', errorMsg);
        } finally {
            isTyping = false;
            sendBtn.disabled = !chatTextarea.value.trim() && pendingFiles.length === 0;
            chatTextarea.focus();
        }
    }

    // ============================================================
    // FILE HANDLING
    // ============================================================

    function handleFileUpload(files, isImage) {
        Array.from(files).forEach(file => {
            const reader = new FileReader();
            reader.onload = (e) => {
                const fileData = {
                    name: file.name,
                    type: isImage ? 'image' : 'file',
                    data: e.target.result,
                    size: file.size
                };
                pendingFiles.push(fileData);
                addFilePreview(fileData);
                sendBtn.disabled = false;
            };
            reader.readAsDataURL(file);
        });
    }

    function addFilePreview(fileData) {
        filePreviewArea.classList.add('has-files');

        const item = document.createElement('div');
        item.className = 'file-preview-item';

        if (fileData.type === 'image') {
            item.innerHTML = `
                <img src="${fileData.data}" alt="${escapeHtml(fileData.name)}">
                <span>${escapeHtml(fileData.name)}</span>
                <button class="file-preview-remove"><i class="fas fa-times"></i></button>
            `;
        } else {
            item.innerHTML = `
                <i class="fas fa-file"></i>
                <span>${escapeHtml(fileData.name)}</span>
                <button class="file-preview-remove"><i class="fas fa-times"></i></button>
            `;
        }

        item.querySelector('.file-preview-remove').addEventListener('click', () => {
            const idx = pendingFiles.indexOf(fileData);
            if (idx > -1) pendingFiles.splice(idx, 1);
            item.remove();
            if (pendingFiles.length === 0) {
                filePreviewArea.classList.remove('has-files');
                if (!chatTextarea.value.trim()) sendBtn.disabled = true;
            }
        });

        filePreviewArea.appendChild(item);
    }

    function clearFilePreview() {
        filePreviewArea.innerHTML = '';
        filePreviewArea.classList.remove('has-files');
    }

    // ============================================================
    // UTILITY FUNCTIONS
    // ============================================================

    function parseMarkdown(text) {
        if (!text) return '';

        let html = text
            // Code blocks
            .replace(/```(\w*)\n([\s\S]*?)```/g, '<div class="code-block-wrapper"><div class="code-header"><span>$1</span><button class="copy-code-btn"><i class="fas fa-copy"></i></button></div><pre><code class="language-$1">$2</code></pre></div>')
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            // Bold & Italic
            .replace(/\*\*\*(.*?)\*\*\*/g, '<strong><em>$1</em></strong>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            // Headers
            .replace(/^### (.*$)/gm, '<h3>$1</h3>')
            .replace(/^## (.*$)/gm, '<h2>$1</h2>')
            .replace(/^# (.*$)/gm, '<h1>$1</h1>')
            // Lists - improved
            .replace(/^\- (.*$)/gm, '<li>$1</li>')
            .replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>')
            // Paragraphs
            .split('\n\n').map(p => p.trim() ? `<p>${p}</p>` : '').join('')
            .replace(/\n/g, '<br>');

        return html;
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.appendChild(document.createTextNode(text));
        return div.innerHTML;
    }

    function formatTime(date) {
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    function scrollToBottom() {
        messagesArea.scrollTo({ top: messagesArea.scrollHeight, behavior: 'smooth' });
    }

    function showToast(message) {
        const toast = document.createElement('div');
        toast.style.cssText = `
            position: fixed; bottom: 80px; left: 50%; transform: translateX(-50%);
            background: #333; color: #fff; padding: 8px 16px; border-radius: 8px;
            font-size: 0.8rem; z-index: 9999; animation: fadeIn 0.2s ease;
        `;
        toast.textContent = message;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 2000);
    }

    function autoResizeTextarea() {
        chatTextarea.addEventListener('input', () => {
            chatTextarea.style.height = 'auto';
            chatTextarea.style.height = Math.min(chatTextarea.scrollHeight, 200) + 'px';
        });
    }

    function openSidebar() {
        sidebar.classList.add('open');
        sidebarOverlay.classList.add('visible');
    }

    function closeSidebar() {
        sidebar.classList.remove('open');
        sidebarOverlay.classList.remove('visible');
    }

    // ============================================================
    // EVENT LISTENERS
    // ============================================================

    function setupEventListeners() {
        // New chat
        newChatBtn.addEventListener('click', () => {
            showWelcome();
            closeSidebar();
        });

        // Send message
        sendBtn.addEventListener('click', sendMessage);

        // Textarea
        chatTextarea.addEventListener('input', () => {
            sendBtn.disabled = !chatTextarea.value.trim() && pendingFiles.length === 0;
        });

        chatTextarea.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        // File upload
        document.getElementById('attach-file-btn').addEventListener('click', () => {
            fileUploadInput.click();
        });

        document.getElementById('attach-image-btn').addEventListener('click', () => {
            imageUploadInput.click();
        });

        fileUploadInput.addEventListener('change', (e) => {
            handleFileUpload(e.target.files, false);
            e.target.value = '';
        });

        imageUploadInput.addEventListener('change', (e) => {
            handleFileUpload(e.target.files, true);
            e.target.value = '';
        });

        // Sidebar toggle (mobile)
        if (sidebarToggle) {
            sidebarToggle.addEventListener('click', () => {
                if (sidebar.classList.contains('open')) {
                    closeSidebar();
                } else {
                    openSidebar();
                }
            });
        }

        sidebarOverlay.addEventListener('click', closeSidebar);

        // Scroll to bottom button
        messagesArea.addEventListener('scroll', () => {
            const atBottom = messagesArea.scrollHeight - messagesArea.scrollTop - messagesArea.clientHeight < 100;
            scrollToBottomBtn.classList.toggle('visible', !atBottom);
        });

        scrollToBottomBtn.addEventListener('click', scrollToBottom);

        // Welcome suggestions with stagger
        document.querySelectorAll('.suggestion-card').forEach((card, index) => {
            card.style.opacity = '0';
            card.style.transform = 'translateY(10px)';
            setTimeout(() => {
                card.style.transition = 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)';
                card.style.opacity = '1';
                card.style.transform = 'translateY(0)';
            }, 100 * index);

            card.addEventListener('click', () => {
                const prompt = card.dataset.prompt;
                chatTextarea.value = prompt;
                sendBtn.disabled = false;
                chatTextarea.focus();
                sendMessage();
            });
        });
    }

    // ============================================================
    // START
    // ============================================================

    init();

})();
