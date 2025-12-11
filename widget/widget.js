// AI Widget
(function(){
    'use strict';

    let config = {
        apiBase: window.AIWidgetConfig?.apiBase || location.origin,
        collection: window.AIWidgetConfig?.collection || 'default_collection',
        message: window.AIWidgetConfig?.welcomeMessage || 'Hello! How can I help you?',
        color: window.AIWidgetConfig?.color || '#667eea',
        title: window.AIWidgetConfig?.title || 'AI Assistant',
        placeholder: window.AIWidgetConfig?.placeholder || 'Ask me anything...',
        sendText: window.AIWidgetConfig?.sendText || 'Send'
    };

    let button, chat, input, sendButton, closeButton, titleEl, messagesDiv;
    let messages = [];

    function appendMessage(text, type) {
        messages.push({text, type});
        const msgDiv = document.createElement('div');
        msgDiv.style.cssText = `
            margin: 5px 0;
            padding: 8px 12px;
            border-radius: 18px;
            max-width: 80%;
            word-wrap: break-word;
            ${type === 'user' ? 'background: #007bff; color: white; margin-left: auto; text-align: right;' : 'background: #e9ecef; color: black;'}
        `;
        msgDiv.innerText = text;
        messagesDiv.appendChild(msgDiv);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }

    async function sendMessage() {
        const q = input.value.trim();
        if (!q) return;
        appendMessage(q, 'user');
        input.value = '';

        sendButton.disabled = true;
        sendButton.innerText = 'Sending...';

        try {
            const response = await fetch(config.apiBase + '/chat', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({question: q, collection: config.collection})
            });
            const data = await response.json();
            appendMessage(data.answer || 'Error', 'bot');
        } catch (error) {
            appendMessage('Network error', 'bot');
        } finally {
            sendButton.disabled = false;
            sendButton.innerText = config.sendText;
        }
    }

    function initWidget() {
        button = document.createElement('button');
        button.innerText = config.title.substring(0,2).toUpperCase() || 'AI';
        button.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            width: 56px;
            height: 56px;
            border-radius: 50%;
            background: ${config.color};
            color: white;
            border: none;
            cursor: pointer;
            z-index: 99999;
            box-shadow: 0 4px 20px rgba(0,0,0,0.2);
        `;

        chat = document.createElement('div');
        chat.style.cssText = `
            position: fixed;
            bottom: 80px;
            right: 20px;
            width: 380px;
            height: 400px;
            background: white;
            border: 1px solid #ccc;
            border-radius: 16px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            display: none;
            z-index: 99999;
            flex-direction: column;
        `;

        const header = document.createElement('div');
        header.style.cssText = `display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; background: ${config.color}; color: white; border-radius: 16px 16px 0 0;`;
        titleEl = document.createElement('div');
        titleEl.innerText = config.title;
        closeButton = document.createElement('button');
        closeButton.innerText = '×';
        closeButton.style.cssText = `background: none; border: none; color: white; font-size: 24px; cursor: pointer;`;
        closeButton.onclick = function() {
            chat.style.display = 'none';
            button.style.display = 'flex';
        };
        header.appendChild(titleEl);
        header.appendChild(closeButton);
        chat.appendChild(header);

        messagesDiv = document.createElement('div');
        messagesDiv.style.cssText = `flex: 1; overflow-y: auto; padding: 16px 20px;`;
        chat.appendChild(messagesDiv);

        if (config.message) {
            appendMessage(config.message, 'bot');
        }

        const inputRow = document.createElement('div');
        inputRow.style.cssText = `display: flex; gap: 8px; padding: 16px 20px; border-top: 1px solid #e5e7eb;`;

        input = document.createElement('input');
        input.placeholder = config.placeholder;
        input.style.cssText = `flex: 1; padding: 12px 16px; border: 2px solid #e5e7eb; border-radius: 24px; outline: none;`;
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') sendMessage();
        });

        sendButton = document.createElement('button');
        sendButton.innerText = config.sendText;
        sendButton.style.cssText = `padding: 12px 20px; border: none; border-radius: 24px; background: ${config.color}; color: white; cursor: pointer;`;
        sendButton.onclick = sendMessage;

        inputRow.appendChild(input);
        inputRow.appendChild(sendButton);
        chat.appendChild(inputRow);

        button.onclick = function() {
            chat.style.display = 'flex';
            button.style.display = 'none';
        };

        document.body.appendChild(button);
        document.body.appendChild(chat);
    }

    // API to update config
    window.AIWidget = window.AIWidget || {};
    window.AIWidget.init = (opts) => {
        Object.assign(config, opts);
        if (button) {
            button.style.background = config.color;
            button.innerText = config.title.substring(0,2).toUpperCase() || 'AI';
        }
        if (titleEl) titleEl.innerText = config.title;
        if (input) input.placeholder = config.placeholder;
        if (sendButton) sendButton.innerText = config.sendText;
    };

    if (document.readyState === 'complete') {
        initWidget();
    } else {
        window.addEventListener('load', initWidget);
    }
})();
