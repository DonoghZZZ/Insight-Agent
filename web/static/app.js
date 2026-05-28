// Insight Agent Web — Full Frontend

let sessionId = null;
let selectedCrawler = null;
let selectedTemplate = null;
let thinking = false;

// ===== Init =====
document.addEventListener('DOMContentLoaded', () => {
  loadFiles();
  loadCrawlers();
  loadTemplates();
  loadSchedule();
});

// ===== Tabs =====
function switchTab(name) {
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelector(`[data-tab="${name}"]`).classList.add('active');
  document.getElementById(`tab-${name}`).classList.add('active');
}

// ===== Files =====
async function uploadFile(input) {
  const file = input.files[0];
  if (!file) return;
  const form = new FormData();
  form.append('file', file);
  try {
    await fetch('/api/upload', { method: 'POST', body: form });
    loadFiles();
    input.value = '';
  } catch(e) { alert('上传失败'); }
}

async function loadFiles() {
  try {
    const r = await fetch('/api/files');
    const files = await r.json();
    const list = document.getElementById('sideFiles');
    list.innerHTML = files.map(f =>
      `<div class="file-item" onclick="selectFile('${f.path}')">📄 ${f.name}</div>`
    ).join('') || '<div class="file-item" style="color:#555">暂无文件</div>';
  } catch(e) {}
}

function selectFile(path) {
  document.querySelectorAll('#sideFiles .file-item').forEach(f => f.classList.remove('active'));
  event.target.classList.add('active');
  createSession(path);
  switchTab('chat');
}

// ===== Session =====
async function createSession(filePath) {
  showThinking(true);
  try {
    const r = await fetch('/api/sessions', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({file: filePath}) });
    const data = await r.json();
    if (data.error) { showThinking(false); alert(data.error); return; }

    sessionId = data.session_id;
    document.getElementById('chatFile').textContent = data.file;
    document.getElementById('chatStatus').innerHTML = `${data.rows}条 · ${data.columns}字段`;
    document.getElementById('chatInput').style.display = 'flex';

    const body = document.getElementById('chatBody');
    body.innerHTML = '';
    showThinking(false);
    addMsg('assistant', data.greeting);
  } catch(e) { showThinking(false); }
}

async function sendMsg() {
  const input = document.getElementById('msgInput');
  const text = input.value.trim();
  if (!text || thinking || !sessionId) return;
  input.value = ''; input.style.height = 'auto';

  addMsg('user', text);
  showThinking(true);

  try {
    const r = await fetch('/api/chat', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({message:text, session_id:sessionId}) });
    const data = await r.json();
    showThinking(false);
    if (data.response) addMsg('assistant', data.response);
  } catch(e) { showThinking(false); addMsg('assistant', '❌ 连接失败'); }
}

function addMsg(role, text) {
  const body = document.getElementById('chatBody');
  const d = document.createElement('div'); d.className = `msg ${role}`;
  d.innerHTML = `<div class="avatar">${role==='assistant'?'🤖':'👤'}</div><div class="bubble">${renderMd(text)}</div>`;
  body.appendChild(d);
  body.scrollTop = body.scrollHeight;
}

function showThinking(show) {
  thinking = show;
  const el = document.getElementById('thinking');
  if (show) {
    if (!el) {
      const d = document.createElement('div'); d.className = 'thinking'; d.id = 'thinking';
      d.innerHTML = '<div class="thinking-dots"><span></span><span></span><span></span></div>AI 分析中...';
      document.getElementById('chatBody').appendChild(d);
    }
  } else {
    const e = document.getElementById('thinking'); if (e) e.remove();
  }
  document.querySelector('.send-btn').disabled = show;
}

// ===== Markdown =====
function renderMd(t) {
  if (!t) return '';
  let h = t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  h = h.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
  h = h.replace(/`([^`]+)`/g, '<code>$1</code>');
  h = h.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  h = h.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  h = h.replace(/^## (.+)$/gm, '<h2>$1</h2>');
  h = h.replace(/^# (.+)$/gm, '<h1>$1</h1>');
  h = h.replace(/^- (.+)$/gm, '<li>$1</li>');
  h = h.replace(/(<li>[\s\S]*?<\/li>){2,}/g, '<ul>$&</ul>');
  h = h.replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>');
  return h.replace(/\n\n/g, '<br><br>');
}

// ===== Crawlers =====
async function loadCrawlers() {
  try {
    const r = await fetch('/api/crawlers');
    const crawlers = await r.json();
    const grid = document.getElementById('crawlerGrid');
    grid.innerHTML = crawlers.map(c =>
      `<div class="crawler-card" data-key="${c.key}" onclick="selectCrawler('${c.key}')">
        <div class="name">${c.platform}</div>
        <div class="desc">${c.name}</div>
      </div>`
    ).join('');
  } catch(e) {}
}

function selectCrawler(key) {
  selectedCrawler = key;
  document.querySelectorAll('.crawler-card').forEach(c => c.classList.remove('selected'));
  const card = document.querySelector(`[data-key="${key}"]`);
  if (card) card.classList.add('selected');

  document.getElementById('crawlForm').style.display = 'block';
  document.getElementById('crawlFormTitle').textContent = '⚙️ 配置参数';
}

async function doCrawl() {
  if (!selectedCrawler) return alert('请先选择平台');
  const url = document.getElementById('crawlUrl').value;
  const max = parseInt(document.getElementById('crawlMax').value) || 50;
  const res = document.getElementById('crawlResult');
  res.innerHTML = '<div class="thinking"><div class="thinking-dots"><span></span><span></span><span></span></div>采集中...</div>';

  try {
    const r = await fetch('/api/crawl', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({crawler:selectedCrawler, params:{url, max}}) });
    const data = await r.json();
    if (data.error) { res.innerHTML = `<div class="result-box error">❌ ${data.error}</div>`; return; }
    res.innerHTML = `<div class="result-box success">✅ 采集完成！<br>文件: ${data.name}<br>记录: ${data.rows}条<br><button class="btn-accent" onclick="selectFile('${data.file}')" style="margin-top:8px">→ 开始分析</button></div>`;
    loadFiles();
  } catch(e) { res.innerHTML = `<div class="result-box error">❌ ${e.message}</div>`; }
}

// ===== NL Crawl =====
async function doNLCrawl() {
  const desc = document.getElementById('nlDesc').value.trim();
  if (!desc) return alert('请描述需求');
  const res = document.getElementById('nlResult');
  res.innerHTML = '<div class="thinking"><div class="thinking-dots"><span></span><span></span><span></span></div>AI 分析中...</div>';

  try {
    const r = await fetch('/api/nl-crawl', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({description:desc}) });
    const data = await r.json();
    if (data.error) { res.innerHTML = `<div class="result-box error">❌ ${data.error}</div>`; return; }
    res.innerHTML = `<div class="result-box success">✅ ${data.platform} 采集完成<br>文件: ${data.file ? data.file.split('/').pop() : 'N/A'}<br>${data.rows ? data.rows+'条' : ''}<br>${data.reason ? '💡 '+data.reason : ''}</div>`;
    loadFiles();
  } catch(e) { res.innerHTML = `<div class="result-box error">❌ ${e.message}</div>`; }
}

// ===== Templates =====
async function loadTemplates() {
  try {
    const r = await fetch('/api/templates');
    const tmpls = await r.json();
    document.getElementById('templateGrid').innerHTML = tmpls.map(t =>
      `<div class="template-card" data-id="${t.id}" onclick="selectTemplate('${t.id}')">
        <div class="name">${t.name}</div>
        <div class="desc">${t.desc}</div>
      </div>`
    ).join('');
  } catch(e) {}
}

function selectTemplate(tid) {
  selectedTemplate = tid;
  document.querySelectorAll('.template-card').forEach(c => c.classList.remove('selected'));
  document.querySelector(`[data-id="${tid}"]`)?.classList.add('selected');
  showFileModal();
}

function showFileModal() {
  document.getElementById('fileModal').classList.add('show');
  fetch('/api/files').then(r => r.json()).then(files => {
    document.getElementById('fileModalList').innerHTML = files.map(f =>
      `<div class="file-item" onclick="runTemplate('${f.path}')">📄 ${f.name}</div>`
    ).join('');
  });
}

function closeModal() { document.getElementById('fileModal').classList.remove('show'); }

async function runTemplate(filePath) {
  closeModal();
  const res = document.getElementById('templateResult');
  res.innerHTML = '<div class="thinking"><div class="thinking-dots"><span></span><span></span><span></span></div>分析中...</div>';

  try {
    const r = await fetch('/api/templates/run', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({template_id:selectedTemplate, file:filePath}) });
    const data = await r.json();
    if (data.error) { res.innerHTML = `<div class="result-box error">❌ ${data.error}</div>`; return; }
    res.innerHTML = `<div class="result-box success">✅ 分析完成！${data.models_ran}个模型<br>报告: ${data.report.split('/').pop()}</div>`;
  } catch(e) { res.innerHTML = `<div class="result-box error">❌ ${e.message}</div>`; }
}

// ===== Schedule =====
async function loadSchedule() {
  try {
    const r = await fetch('/api/schedule');
    const jobs = await r.json();
    document.getElementById('scheduleList').innerHTML = jobs.map(j =>
      `<div class="schedule-item">
        <span>${j.status} ${j.platform} · ${j.interval} · 上次:${j.last}</span>
        <button onclick="removeSchedule('${j.id}')">删除</button>
      </div>`
    ).join('') || '<p style="color:#555">暂无任务</p>';
  } catch(e) {}

  // Load crawlers for select
  fetch('/api/crawlers').then(r => r.json()).then(crawlers => {
    document.getElementById('schedCrawler').innerHTML = crawlers.map(c =>
      `<option value="${c.key}">${c.platform}</option>`
    ).join('');
  });
}

async function addSchedule() {
  const crawler = document.getElementById('schedCrawler').value;
  const interval = parseInt(document.getElementById('schedInterval').value) || 24;
  try {
    await fetch('/api/schedule', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({crawler, params:{}, interval_hours:interval}) });
    loadSchedule();
  } catch(e) { alert(e.message); }
}

async function removeSchedule(id) {
  try {
    await fetch(`/api/schedule/${id}`, { method:'DELETE' });
    loadSchedule();
  } catch(e) {}
}
