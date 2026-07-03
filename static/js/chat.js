'use strict';

const API = ''; // same origin — proxied by FastAPI

let attachedFile = null;
let isGenerating = false;
let currentChatId = null;

// ── Helpers ───────────────────────────────────────────────────────────────────

function escHtml(s) {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function renderMarkdown(text) {
  return marked.parse(text);
}

function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 160) + 'px';
}

function timeAgo(iso) {
  const diffMs = Date.now() - new Date(iso + 'Z').getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

// ── "New chat" button visibility ──────────────────────────────────────────────

function syncNewChatBtn() {
  document.getElementById('newChatBtn').style.display = currentChatId ? '' : 'none';
}

// ── Status polling ────────────────────────────────────────────────────────────

async function pollStatus() {
  try {
    const [health, info] = await Promise.all([
      fetch(`${API}/health`).then(r => r.json()),
      fetch(`${API}/info`).then(r => r.json()),
    ]);

    const serverBadge = document.getElementById('serverBadge');
    if (health.model_loaded) {
      serverBadge.textContent = 'Ready';
      serverBadge.className = 'badge badge-green';
    } else {
      serverBadge.textContent = 'Loading…';
      serverBadge.className = 'badge badge-yellow';
      setTimeout(pollStatus, 5000);
      return;
    }

    const fullId = info.model_id || '';
    const modelShort = fullId.split('/').pop() || '—';
    const quantTag = fullId.includes(':') ? fullId.split(':').pop() : '—';
    document.getElementById('modelBadge').textContent = modelShort.split(':')[0];
    document.getElementById('deviceBadge').textContent = info.backend || 'Ollama';
    document.getElementById('quantBadge').textContent = quantTag;
  } catch {
    const b = document.getElementById('serverBadge');
    b.textContent = 'Offline';
    b.className = 'badge badge-red';
    setTimeout(pollStatus, 8000);
  }
}

// ── Chat list ─────────────────────────────────────────────────────────────────

async function loadChatList() {
  try {
    const chats = await fetch(`${API}/chats`).then(r => r.json());
    renderChatList(chats);
  } catch {
    // Sidebar list is a nice-to-have; ignore transient failures silently.
  }
}

function renderChatList(chats) {
  const list = document.getElementById('chatList');
  if (!chats.length) {
    list.innerHTML = '<div class="chat-list-empty">No chats yet</div>';
    return;
  }
  list.innerHTML = '';
  for (const chat of chats) {
    const item = document.createElement('div');
    item.className = 'chat-item' + (chat.id === currentChatId ? ' active' : '');
    item.addEventListener('click', () => selectChat(chat.id));

    const title = document.createElement('span');
    title.className = 'chat-item-title';
    title.textContent = chat.title;
    title.title = `${chat.title} · ${timeAgo(chat.updated_at)}`;

    const del = document.createElement('button');
    del.className = 'chat-item-del';
    del.textContent = '✕';
    del.title = 'Delete chat';
    del.addEventListener('click', e => { e.stopPropagation(); deleteChat(chat.id); });

    item.appendChild(title);
    item.appendChild(del);
    list.appendChild(item);
  }
}

async function selectChat(chatId) {
  if (isGenerating) return;
  try {
    const res = await fetch(`${API}/chats/${chatId}`);
    if (!res.ok) throw new Error('Chat not found');
    const chat = await res.json();

    currentChatId = chat.id;
    syncNewChatBtn();

    const area = document.getElementById('chatArea');
    area.innerHTML = '';
    for (const msg of chat.messages) {
      if (msg.role === 'system') continue;
      const role = msg.role === 'user' ? 'user' : 'assistant';
      const html = role === 'user' ? escHtml(msg.content) : renderMarkdown(msg.content);
      appendMessage(role, html, new Date(msg.created_at + 'Z').toLocaleTimeString());
    }
    if (!chat.messages.some(m => m.role !== 'system')) {
      area.innerHTML = `
        <div class="empty-state" id="emptyState">
          <div class="empty-icon">✦</div>
          <div class="empty-title">Empty chat</div>
          <div class="empty-sub">Send a message to get started.</div>
        </div>`;
    }
    loadChatList();
  } catch (err) {
    appendError(`Failed to load chat: ${err.message}`);
  }
}

function startNewChat() {
  if (isGenerating) return;
  currentChatId = null;
  clearChat();
  loadChatList();
  syncNewChatBtn();
}

async function deleteChat(chatId) {
  if (!confirm('Delete this chat? This cannot be undone.')) return;
  try {
    await fetch(`${API}/chats/${chatId}`, { method: 'DELETE' });
    if (chatId === currentChatId) {
      currentChatId = null;
      clearChat();
      syncNewChatBtn();
    }
    loadChatList();
  } catch (err) {
    appendError(`Failed to delete chat: ${err.message}`);
  }
}

// ── Image handling ────────────────────────────────────────────────────────────

function handleFileSelect(e) {
  const file = e.target.files[0];
  if (!file) return;
  attachedFile = file;
  const reader = new FileReader();
  reader.onload = ev => {
    document.getElementById('imageThumb').src = ev.target.result;
    document.getElementById('imageFileName').textContent = file.name;
    document.getElementById('imagePreviewWrap').classList.add('visible');
  };
  reader.readAsDataURL(file);
}

function removeImage() {
  attachedFile = null;
  document.getElementById('fileInput').value = '';
  document.getElementById('imagePreviewWrap').classList.remove('visible');
  document.getElementById('imageThumb').src = '';
}

// ── Chat rendering ────────────────────────────────────────────────────────────

function appendMessage(role, html, meta = '') {
  const area = document.getElementById('chatArea');
  document.getElementById('emptyState')?.remove();

  const div = document.createElement('div');
  div.className = `msg ${role}`;

  const avatar = document.createElement('div');
  avatar.className = `avatar ${role === 'user' ? 'user-av' : 'ai-av'}`;
  avatar.textContent = role === 'user' ? '👤' : '🧠';

  const bubble = document.createElement('div');
  bubble.className = `bubble ${role === 'user' ? 'user-b' : 'ai-b'}`;
  bubble.innerHTML = html;

  const wrap = document.createElement('div');
  wrap.appendChild(bubble);
  if (meta) {
    const metaEl = document.createElement('div');
    metaEl.className = 'meta';
    metaEl.textContent = meta;
    wrap.appendChild(metaEl);
  }

  div.appendChild(avatar);
  div.appendChild(wrap);
  area.appendChild(div);
  area.scrollTop = area.scrollHeight;
  return bubble;
}

function appendThinking() {
  const area = document.getElementById('chatArea');
  document.getElementById('emptyState')?.remove();

  const div = document.createElement('div');
  div.className = 'msg assistant';
  div.id = 'thinkingMsg';
  div.innerHTML = `
    <div class="avatar ai-av">🧠</div>
    <div class="thinking">
      <div class="dots"><span></span><span></span><span></span></div>
      Generating…
    </div>`;
  area.appendChild(div);
  area.scrollTop = area.scrollHeight;
}

function removeThinking() {
  document.getElementById('thinkingMsg')?.remove();
}

function appendError(msg) {
  const area = document.getElementById('chatArea');
  const div = document.createElement('div');
  div.className = 'msg assistant';
  div.innerHTML = `
    <div class="avatar ai-av">🧠</div>
    <div class="bubble error-b">⚠ ${escHtml(msg)}</div>`;
  area.appendChild(div);
  area.scrollTop = area.scrollHeight;
}

function clearChat() {
  document.getElementById('chatArea').innerHTML = `
    <div class="empty-state" id="emptyState">
      <div class="empty-icon">✦</div>
      <div class="empty-title">AI-FABLE is ready</div>
      <div class="empty-sub">Ask anything — code, reasoning, or drop an image for multimodal analysis.</div>
    </div>`;
}

// ── Send logic ────────────────────────────────────────────────────────────────

async function sendMessage() {
  if (isGenerating) return;
  const textarea = document.getElementById('promptInput');
  const prompt = textarea.value.trim();
  if (!prompt) return;

  const maxTokens = parseInt(document.getElementById('maxTokens').value);
  const temperature = parseFloat(document.getElementById('temperature').value);
  const topP = parseFloat(document.getElementById('topP').value);
  const doSample = document.getElementById('doSample').checked;
  const systemPrompt = document.getElementById('systemPrompt').value.trim();

  const userHtml = attachedFile
    ? `<img src="${document.getElementById('imageThumb').src}"
            style="max-width:260px;border-radius:8px;display:block;margin-bottom:8px;" />
       ${escHtml(prompt)}`
    : escHtml(prompt);
  appendMessage('user', userHtml, new Date().toLocaleTimeString());

  textarea.value = '';
  autoResize(textarea);
  const fileSnapshot = attachedFile;
  removeImage();

  isGenerating = true;
  document.getElementById('sendBtn').disabled = true;
  appendThinking();

  try {
    let data;
    const t0 = Date.now();

    if (fileSnapshot) {
      const form = new FormData();
      form.append('prompt', prompt);
      form.append('max_new_tokens', maxTokens);
      form.append('temperature', temperature);
      form.append('file', fileSnapshot);
      const res = await fetch(`${API}/generate/vision/upload`, { method: 'POST', body: form });
      if (!res.ok) throw new Error((await res.json()).detail || res.statusText);
      data = await res.json();
    } else {
      const body = {
        prompt,
        max_new_tokens: maxTokens,
        temperature,
        top_p: topP,
        do_sample: doSample,
        chat_id: currentChatId,
      };
      if (systemPrompt) body.system_prompt = systemPrompt;
      const res = await fetch(`${API}/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error((await res.json()).detail || res.statusText);
      data = await res.json();
      if (data.chat_id) {
        currentChatId = data.chat_id;
        syncNewChatBtn();
        loadChatList();
      }
    }

    removeThinking();
    const elapsed = ((Date.now() - t0) / 1000).toFixed(1);
    appendMessage(
      'assistant',
      renderMarkdown(data.generated_text),
      `${data.tokens_generated} tokens · ${elapsed}s`,
    );
  } catch (err) {
    removeThinking();
    appendError(err.message);
  } finally {
    isGenerating = false;
    document.getElementById('sendBtn').disabled = false;
    textarea.focus();
  }
}

// ── Event listeners (wired up after DOM is ready via defer) ───────────────────

document.getElementById('newChatBtn').addEventListener('click', startNewChat);
document.getElementById('sendBtn').addEventListener('click', sendMessage);
document.getElementById('removeImgBtn').addEventListener('click', removeImage);
document.getElementById('attachBtn').addEventListener('click', () => {
  document.getElementById('fileInput').click();
});
document.getElementById('fileInput').addEventListener('change', handleFileSelect);

document.getElementById('promptInput').addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});
document.getElementById('promptInput').addEventListener('input', e => autoResize(e.target));

document.getElementById('maxTokens').addEventListener('input', e => {
  document.getElementById('maxTokensVal').textContent = e.target.value;
});
document.getElementById('temperature').addEventListener('input', e => {
  document.getElementById('tempVal').textContent = parseFloat(e.target.value).toFixed(2);
});
document.getElementById('topP').addEventListener('input', e => {
  document.getElementById('topPVal').textContent = parseFloat(e.target.value).toFixed(2);
});

// ── Init ──────────────────────────────────────────────────────────────────────

syncNewChatBtn();
pollStatus();
loadChatList();
