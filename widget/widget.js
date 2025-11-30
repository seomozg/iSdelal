(function(){
  const API_BASE = window.AIWidgetConfig?.apiBase || (location.origin);
  const COLLECTION = window.AIWidgetConfig?.collection || 'site_collection';

  const styleHref = API_BASE + '/widget/widget.css';
  const link = document.createElement('link');
  link.rel = 'stylesheet';
  link.href = styleHref;
  document.head.appendChild(link);

  const mount = document.createElement('div');
  mount.id = 'ai-widget';
  mount.innerHTML = `
    <div class="ai-card" style="position:fixed;bottom:24px;right:24px;z-index:99999">
      <div class="ai-header">Помощник сайта</div>
      <div class="ai-messages" id="ai-messages"></div>
      <div class="ai-input-row">
        <input id="ai-input" class="ai-input" placeholder="Задайте вопрос посетителю..." />
        <button id="ai-send" class="ai-btn">Отправить</button>
      </div>
    </div>
  `;
  document.body.appendChild(mount);

  const messagesEl = document.getElementById('ai-messages');
  const inputEl = document.getElementById('ai-input');
  const sendBtn = document.getElementById('ai-send');

  function appendMessage(text, cls) {
    const d = document.createElement('div');
    d.className = 'ai-msg ' + cls;
    d.textContent = text;
    messagesEl.appendChild(d);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  async function sendQuestion(q) {
    appendMessage(q, 'ai-msg-user');
    try {
      const resp = await fetch(API_BASE + '/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-API-Key': window.AIWidgetConfig?.apiKey || '' },
        body: JSON.stringify({ question: q, collection: COLLECTION })
      });
      const data = await resp.json();
      appendMessage(data.answer || (data.detail || 'Ошибка получения ответа'), 'ai-msg-bot');
    } catch (e) {
      appendMessage('Ошибка сети: ' + e.message, 'ai-msg-bot');
    }
  }

  sendBtn.addEventListener('click', () => {
    const v = inputEl.value.trim();
    if (!v) return;
    sendQuestion(v);
    inputEl.value = '';
  });

  inputEl.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      sendBtn.click();
    }
  });

  window.AIWidget = window.AIWidget || {};
  window.AIWidget.init = (opts) => {
    if (opts?.apiBase) window.AIWidgetConfig = window.AIWidgetConfig || {}, window.AIWidgetConfig.apiBase = opts.apiBase;
    if (opts?.collection) window.AIWidgetConfig = window.AIWidgetConfig || {}, window.AIWidgetConfig.collection = opts.collection;
    if (opts?.apiKey) window.AIWidgetConfig = window.AIWidgetConfig || {}, window.AIWidgetConfig.apiKey = opts.apiKey;
  };

})();