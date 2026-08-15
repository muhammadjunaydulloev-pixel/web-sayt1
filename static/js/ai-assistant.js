/* ===========================================================
   AI Assistant — 🤖 ёрдамчии AI барои омӯзиши забони русӣ
   Танҳо ин файл ва DOM-и ба он вобаста қисми AI Assistant-ро
   идора мекунад — ба дигар қисмҳои сайт даст намерасонад.
   =========================================================== */
(function () {
  'use strict';

  var root = document.getElementById('ai-assistant-root');
  if (!root) return; // Виҷет дар ин саҳифа фаъол нест (масалан панели админ).

  var HISTORY_KEY = 'ai_chat_history_v1';
  var CONTEXT_KEY = 'ai_chat_context_v1';
  var MAX_STORED_TURNS = 40;
  var MAX_SENT_TURNS = 8;

  var fab = document.getElementById('ai-assistant-fab');
  var backdrop = document.getElementById('ai-assistant-backdrop');
  var panel = document.getElementById('ai-assistant-panel');
  var closeBtn = document.getElementById('ai-panel-close');
  var messagesEl = document.getElementById('ai-messages');
  var formEl = document.getElementById('ai-form');
  var inputEl = document.getElementById('ai-input');
  var sendBtn = document.getElementById('ai-send-btn');
  var contextChip = document.getElementById('ai-context-chip');
  var contextChipText = document.getElementById('ai-context-chip-text');
  var contextChipClear = document.getElementById('ai-context-chip-clear');
  var quickBtns = Array.prototype.slice.call(document.querySelectorAll('.ai-quick-btn'));

  var state = {
    history: loadJSON(HISTORY_KEY, []),
    contextWord: loadJSON(CONTEXT_KEY, null),
    sending: false,
  };

  function loadJSON(key, fallback) {
    try {
      var raw = sessionStorage.getItem(key);
      return raw ? JSON.parse(raw) : fallback;
    } catch (e) {
      return fallback;
    }
  }

  function saveState() {
    try {
      sessionStorage.setItem(HISTORY_KEY, JSON.stringify(state.history.slice(-MAX_STORED_TURNS)));
      sessionStorage.setItem(CONTEXT_KEY, JSON.stringify(state.contextWord));
    } catch (e) { /* sessionStorage холӣ ё пур — сарфи назар мекунем */ }
  }

  function esc(s) {
    var d = document.createElement('div');
    d.textContent = s == null ? '' : String(s);
    return d.innerHTML;
  }

  function scrollToBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function renderContextChip() {
    if (state.contextWord && state.contextWord.ru) {
      var tj = state.contextWord.tj ? ' — ' + esc(state.contextWord.tj) : '';
      contextChipText.innerHTML = '📖 Контекст: <strong>' + esc(state.contextWord.ru) + '</strong>' + tj;
      contextChip.setAttribute('data-active', 'true');
    } else {
      contextChip.setAttribute('data-active', 'false');
    }
  }

  function renderEmptyState() {
    if (state.history.length) return;
    var empty = document.createElement('p');
    empty.className = 'ai-empty';
    empty.id = 'ai-empty-msg';
    empty.textContent = 'Салом! Ман ёрдамчии AI ҳастам 🤖 Дар омӯзиши забони русӣ метавонам кӯмак кунам — калимаро фаҳмонам, ҷумла созам, тарҷума кунам ё тест диҳам. Аз тугмаҳои боло истифода баред ё саволатонро нависед.';
    messagesEl.appendChild(empty);
  }

  function removeEmptyState() {
    var e = document.getElementById('ai-empty-msg');
    if (e) e.remove();
  }

  function appendMessage(role, text, opts) {
    opts = opts || {};
    removeEmptyState();
    var wrap = document.createElement('div');
    wrap.className = 'ai-msg ' + role + (opts.error ? ' error' : '');
    var avatarEmoji = role === 'user' ? '🧑' : '🤖';
    var bubbleHtml = '<div class="ai-bubble">' + esc(text).replace(/\n/g, '<br>') + '</div>';
    if (opts.error && opts.retry) {
      bubbleHtml = '<div class="ai-bubble">' + esc(text).replace(/\n/g, '<br>') +
        '<div><button type="button" class="ai-retry-btn">↻ Такрор кӯшиш кунед</button></div></div>';
    }
    wrap.innerHTML =
      '<span class="ai-msg-avatar">' + avatarEmoji + '</span>' + bubbleHtml;
    messagesEl.appendChild(wrap);
    scrollToBottom();

    if (opts.error && opts.retry) {
      var retryBtn = wrap.querySelector('.ai-retry-btn');
      retryBtn.addEventListener('click', function () {
        wrap.remove();
        sendMessage(opts.retry);
      });
    }
    return wrap;
  }

  function appendTyping() {
    var wrap = document.createElement('div');
    wrap.className = 'ai-msg assistant';
    wrap.id = 'ai-typing-indicator';
    wrap.innerHTML =
      '<span class="ai-msg-avatar">🤖</span>' +
      '<div class="ai-bubble"><span class="ai-typing"><span></span><span></span><span></span></span></div>';
    messagesEl.appendChild(wrap);
    scrollToBottom();
  }

  function removeTyping() {
    var t = document.getElementById('ai-typing-indicator');
    if (t) t.remove();
  }

  function renderHistory() {
    messagesEl.innerHTML = '';
    if (!state.history.length) {
      renderEmptyState();
      return;
    }
    state.history.forEach(function (turn) {
      appendMessage(turn.role === 'assistant' ? 'assistant' : 'user', turn.content);
    });
    scrollToBottom();
  }

  function setSending(isSending) {
    state.sending = isSending;
    sendBtn.disabled = isSending;
    quickBtns.forEach(function (b) { b.disabled = isSending; });
  }

  async function sendMessage(text) {
    text = (text || '').trim();
    if (!text || state.sending) return;

    appendMessage('user', text);
    state.history.push({ role: 'user', content: text });
    saveState();
    setSending(true);
    appendTyping();

    try {
      var res = await fetch('/api/ai/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          context_word: state.contextWord,
          history: state.history.slice(-MAX_SENT_TURNS - 1, -1),
        }),
      });

      var data = null;
      try { data = await res.json(); } catch (e) { /* ignore */ }

      removeTyping();

      if (!res.ok || !data || data.error) {
        appendMessage(
          'assistant',
          '⚠️ Мутаассифона, хатогӣ рух дод. Лутфан якчанд сония сабр карда, боз кӯшиш кунед.',
          { error: true, retry: text }
        );
        return;
      }

      appendMessage('assistant', data.reply);
      state.history.push({ role: 'assistant', content: data.reply });
      saveState();
    } catch (e) {
      removeTyping();
      appendMessage(
        'assistant',
        '⚠️ Пайваст ба сервер имконпазир нашуд. Интернети худро санҷед ва боз кӯшиш кунед.',
        { error: true, retry: text }
      );
    } finally {
      setSending(false);
    }
  }

  function openPanel() {
    panel.hidden = false;
    backdrop.hidden = false;
    // force reflow so the transition runs
    void panel.offsetWidth;
    panel.setAttribute('data-open', 'true');
    backdrop.setAttribute('data-open', 'true');
    document.body.style.overflow = 'hidden';
    setTimeout(function () { inputEl.focus(); }, 260);
  }

  function closePanel() {
    panel.setAttribute('data-open', 'false');
    backdrop.setAttribute('data-open', 'false');
    document.body.style.overflow = '';
    setTimeout(function () {
      panel.hidden = true;
      backdrop.hidden = true;
    }, 320);
  }

  function setContextWord(ru, tj) {
    state.contextWord = ru ? { ru: ru, tj: tj || '' } : null;
    saveState();
    renderContextChip();
  }

  function clearContextWord() {
    setContextWord(null, null);
  }

  function quickActionPrompt(kind) {
    var ctx = state.contextWord;
    var ruLabel = ctx && ctx.ru ? '«' + ctx.ru + '»' : null;

    switch (kind) {
      case 'explain':
        return ruLabel ? 'Ин калимаро фаҳмон: ' + ruLabel : 'Лутфан як калимаи русиро нависед, то фаҳмонам.';
      case 'sentence':
        return ruLabel ? 'Барои ' + ruLabel + ' ҷумла соз.' : 'Барои кадом калима ҷумла созам? Калимаро нависед.';
      case 'translate':
        return ruLabel ? 'Ин калимаро ба тоҷикӣ тарҷума кун: ' + ruLabel : 'Кадом калимаро тарҷума кунам? Нависед.';
      case 'test':
        return ruLabel ? 'Аз ' + ruLabel + ' тест соз.' : 'Ба ман 5 саволи тестӣ деҳ.';
      case 'pronounce':
        return ruLabel ? 'Талаффузи ' + ruLabel + '-ро фаҳмон.' : 'Лутфан калимаеро нависед, то талаффузашро фаҳмонам.';
      default:
        return '';
    }
  }

  quickBtns.forEach(function (btn) {
    btn.addEventListener('click', function () {
      var kind = btn.getAttribute('data-action');
      if (kind === 'pronounce' && state.contextWord && state.contextWord.ru && window.SlFx && window.SlFx.speakRu) {
        window.SlFx.speakRu(state.contextWord.ru, btn);
      }
      var prompt = quickActionPrompt(kind);
      if (prompt) sendMessage(prompt);
    });
  });

  formEl.addEventListener('submit', function (e) {
    e.preventDefault();
    var text = inputEl.value;
    inputEl.value = '';
    sendMessage(text);
  });

  fab.addEventListener('click', function () {
    openPanel();
  });

  closeBtn.addEventListener('click', closePanel);
  backdrop.addEventListener('click', closePanel);

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && panel.getAttribute('data-open') === 'true') {
      closePanel();
    }
  });

  contextChipClear.addEventListener('click', clearContextWord);

  renderContextChip();
  renderHistory();

  // ---------- Public API used by word cards (lesson_detail.html) ----------
  window.AIAssistant = {
    open: function () {
      openPanel();
    },
    openWithWord: function (ru, tj) {
      setContextWord(ru, tj);
      openPanel();
    },
    clearContext: clearContextWord,
  };
})();
