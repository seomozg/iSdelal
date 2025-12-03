(function(){
  'use strict';

  // Configuration with defaults
  const config = {
    // Our FastAPI backend is mounted at the origin, so default apiBase is just location.origin
    apiBase: window.AIWidgetConfig?.apiBase || location.origin,
    theme: window.AIWidgetConfig?.theme || 'default',
    language: window.AIWidgetConfig?.language || 'en',
    welcomeMessage: window.AIWidgetConfig?.welcomeMessage || null,
    maxMessages: window.AIWidgetConfig?.maxMessages || 50
  };

  // Translations
  const translations = {
    en: {
      title: 'AI Assistant',
      placeholder: 'Ask me anything...',
      send: 'Send',
      typing: 'AI is typing...',
      error: 'Sorry, something went wrong. Please try again.',
      networkError: 'Network error. Please check your connection.'
    },
    ru: {
      title: 'ИИ Помощник',
      placeholder: 'Задайте вопрос...',
      send: 'Отправить',
      typing: 'ИИ печатает...',
      error: 'Извините, произошла ошибка. Попробуйте еще раз.',
      networkError: 'Ошибка сети. Проверьте подключение.'
    }
  };

  const t = translations[config.language] || translations.en;

  // Load CSS
  function loadCSS() {
    const styleHref = config.apiBase.replace('/api', '') + '/widget/widget.css';
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = styleHref;
    document.head.appendChild(link);
  }

  // Create widget HTML
  function createWidget() {
    const positions = {
      'bottom-right': 'bottom:24px;right:24px;',
      'bottom-left': 'bottom:24px;left:24px;',
      'top-right': 'top:24px;right:24px;',
      'top-left': 'top:24px;left:24px;'
    };

    const mount = document.createElement('div');
    mount.id = 'ai-widget';
    mount.innerHTML = `
      <div class="ai-widget-container" style="position:fixed;${positions[config.position]}z-index:99999">
        <div class="ai-widget-toggle" id="ai-toggle">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
          </svg>
        </div>
        <div class="ai-widget-card" id="ai-card" style="display:none;">
          <div class="ai-widget-header">
            <div class="ai-widget-title">${config.title}</div>
            <button class="ai-widget-close" id="ai-close">&times;</button>
          </div>
          <div class="ai-widget-messages" id="ai-messages"></div>
          <div class="ai-widget-input-row">
            <input id="ai-input" class="ai-widget-input" placeholder="${config.placeholder}" />
            <button id="ai-send" class="ai-widget-btn">${t.send}</button>
          </div>
          <div class="ai-widget-typing" id="ai-typing" style="display:none;">
            <div class="ai-widget-typing-dots">
              <span></span><span></span><span></span>
            </div>
            ${t.typing}
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(mount);
  }

  // Widget functionality
  let isOpen = false;
  let messageHistory = [];
  let messagesEl, inputEl, sendBtn, toggleBtn, cardEl, closeBtn, typingEl;

  function appendMessage(text, type, timestamp = Date.now()) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `ai-widget-message ai-widget-message-${type}`;
    messageDiv.innerHTML = `
      <div class="ai-widget-message-content">${text}</div>
      <div class="ai-widget-message-time">${new Date(timestamp).toLocaleTimeString()}</div>
    `;

    messagesEl.appendChild(messageDiv);
    messagesEl.scrollTop = messagesEl.scrollHeight;

    // Store in history
    messageHistory.push({ text, type, timestamp });
    if (messageHistory.length > config.maxMessages) {
      messageHistory.shift();
      if (messagesEl.children.length > config.maxMessages) {
        messagesEl.removeChild(messagesEl.children[0]);
      }
    }
  }

  function showTyping() {
    typingEl.style.display = 'flex';
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function hideTyping() {
    typingEl.style.display = 'none';
  }

  async function sendQuestion(question) {
    if (!question.trim()) return;

    appendMessage(question, 'user');
    showTyping();

    try {
      const response = await fetch(config.apiBase + '/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': config.apiKey
        },
        body: JSON.stringify({
          question: question,
          collection: config.collection
        })
      });

      const data = await response.json();

      if (response.ok) {
        appendMessage(data.answer || 'Sorry, I couldn\'t generate a response.', 'bot');
      } else {
        appendMessage(data.detail || t.error, 'bot');
      }
    } catch (error) {
      console.error('AI Widget Error:', error);
      appendMessage(t.networkError, 'bot');
    } finally {
      hideTyping();
    }
  }

  function toggleWidget() {
    isOpen = !isOpen;
    cardEl.style.display = isOpen ? 'flex' : 'none';
    toggleBtn.style.display = isOpen ? 'none' : 'flex';

    if (isOpen && messageHistory.length === 0 && config.welcomeMessage) {
      setTimeout(() => appendMessage(config.welcomeMessage, 'bot'), 300);
    }
  }

  // Initialize DOM element references after a small delay
  setTimeout(() => {
    messagesEl = document.getElementById('ai-messages');
    inputEl = document.getElementById('ai-input');
    sendBtn = document.getElementById('ai-send');
    toggleBtn = document.getElementById('ai-toggle');
    cardEl = document.getElementById('ai-card');
    closeBtn = document.getElementById('ai-close');
    typingEl = document.getElementById('ai-typing');


    // Set up event listeners now that elements exist
    if (toggleBtn) toggleBtn.addEventListener('click', toggleWidget);
    if (closeBtn) closeBtn.addEventListener('click', toggleWidget);

    if (sendBtn) {
      sendBtn.addEventListener('click', () => {
        const question = inputEl ? inputEl.value.trim() : '';
        if (question) {
          sendQuestion(question);
          if (inputEl) inputEl.value = '';
        }
      });
    }

    if (inputEl) {
      inputEl.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          if (sendBtn) sendBtn.click();
        }
      });
    }

    // Auto-show welcome message (only if elements exist)
    if (config.welcomeMessage && toggleBtn) {
      setTimeout(() => {
        if (!isOpen) toggleWidget();
      }, 1000);
    }
  }, 100);


  // Click outside to close
  document.addEventListener('click', (e) => {
    if (isOpen && mount && !mount.contains(e.target)) {
      toggleWidget();
    }
  });

  // Public API
  window.AIWidget = window.AIWidget || {};
  window.AIWidget.init = (options) => {
    Object.assign(config, options);
    // Re-render if needed
    if (options.title) {
      document.querySelector('.ai-widget-title').textContent = config.title;
    }
  };

  window.AIWidget.sendMessage = (message) => {
    sendQuestion(message);
  };

  window.AIWidget.toggle = () => {
    if (toggleBtn) toggleWidget();
  };

  window.AIWidget.isOpen = () => isOpen;

  // Initialize widget
  loadCSS();
  createWidget();

  // Initialize DOM element references after a small delay
  setTimeout(() => {
    messagesEl = document.getElementById('ai-messages');
    inputEl = document.getElementById('ai-input');
    sendBtn = document.getElementById('ai-send');
    toggleBtn = document.getElementById('ai-toggle');
    cardEl = document.getElementById('ai-card');
    closeBtn = document.getElementById('ai-close');
    typingEl = document.getElementById('ai-typing');


    // Set up event listeners now that elements exist
    if (toggleBtn) toggleBtn.addEventListener('click', toggleWidget);
    if (closeBtn) closeBtn.addEventListener('click', toggleWidget);

    if (sendBtn) {
      sendBtn.addEventListener('click', () => {
        const question = inputEl ? inputEl.value.trim() : '';
        if (question) {
          sendQuestion(question);
          if (inputEl) inputEl.value = '';
        }
      });
    }

    if (inputEl) {
      inputEl.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          if (sendBtn) sendBtn.click();
        }
      });
    }

    // Click outside to close
    document.addEventListener('click', (e) => {
      if (isOpen && mount && !mount.contains(e.target)) {
        toggleWidget();
      }
    });

    // Auto-show welcome message (only if elements exist)
    if (config.welcomeMessage && toggleBtn) {
      setTimeout(() => {
        if (!isOpen) toggleWidget();
      }, 1000);
    }
  }, 100);

})();