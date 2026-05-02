const API = '/api';
let currentTaskId = null;
let ws = null;

// 阶段中文名映射
const STAGE_NAMES = {
  input_collecting: '需求收集',
  requirement_optimizing: '需求优化',
  confirmation: '方案确认',
  planning: '方案规划',
  prompt_optimizing: '提示词优化（辩论）',
  executing: '代码生成（并行）',
  verifying: '验证测试',
  archiving: '归档存储',
};

const AGENT_NAMES = {
  user_input: '用户',
  requirement_optimizer: '优化器',
  confirmation_gate: '确认门',
  planner: '规划器',
  prompt_optimizer: '提示词优化',
  executor: '执行器',
  verifier: '验证器',
  archiver: '归档器',
};

const STATUS_NAMES = {
  completed: '已完成',
  running: '运行中',
  pending: '等待中',
  blocked: '待确认',
  failed: '失败',
  input_collecting: '需求收集中',
  confirmation: '待确认',
  requirement_optimizing: '需求优化中',
  planning: '方案规划中',
  prompt_optimizing: '提示词辩论中',
  executing: '代码生成中',
  verifying: '验证中',
  archiving: '归档中',
  cancelled: '已取消',
};

// ===== API 工具 =====
async function api(path, opts = {}) {
  const res = await fetch(`${API}${path}`, {
    headers: { 'Content-Type': 'application/json', ...opts.headers },
    ...opts,
  });
  if (opts.noParse) return res;
  if (res.status === 204) return null;
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail);
  }
  return res.json();
}

// ===== 导航 =====
function showView(name) {
  document.querySelectorAll('.view').forEach(v => v.style.display = 'none');
  document.getElementById(`view-${name}`).style.display = '';
  document.querySelectorAll('.nav-link').forEach(a => a.classList.remove('active'));
  const navBtn = document.getElementById(`nav-${name}`);
  if (navBtn) navBtn.classList.add('active');
}

document.getElementById('nav-home').onclick = (e) => { e.preventDefault(); showView('home'); loadTasks(); };
document.getElementById('nav-about').onclick = (e) => { e.preventDefault(); alert('工作流AI v0.6.0\nLLM 驱动的多阶段任务编排引擎\n多Agent协作 · 辩论择优 · 并行执行'); };
document.getElementById('btn-back').onclick = (e) => { e.preventDefault(); closeTask(); showView('home'); loadTasks(); };

// ===== 创建任务 =====
document.getElementById('create-form').onsubmit = async (e) => {
  e.preventDefault();
  const input = document.getElementById('user-input').value.trim();
  if (!input) return;

  const btn = document.getElementById('btn-create');
  const btnText = btn.querySelector('.btn-text');
  btn.disabled = true;
  btnText.textContent = '启动中...';

  try {
    const task = await api('/tasks', {
      method: 'POST',
      body: JSON.stringify({ user_input: input }),
    });
    document.getElementById('user-input').value = '';
    await loadTasks();
    openTask(task.task_id);
  } catch (err) {
    alert('创建任务失败：' + err.message);
  } finally {
    btn.disabled = false;
    btnText.textContent = '启动流水线';
  }
};

// ===== 任务列表 =====
async function loadTasks() {
  const tasks = await api('/tasks');
  const container = document.getElementById('task-list');
  const countBadge = document.getElementById('task-count');
  countBadge.textContent = tasks ? tasks.length : 0;

  if (!tasks || tasks.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">&#9744;</div>
        <p>暂无任务，请在上方创建</p>
      </div>`;
    return;
  }

  container.innerHTML = tasks.map((t, i) => `
    <div class="task-card" data-id="${t.task_id}" style="animation-delay: ${i * 0.06}s">
      <div class="task-header">
        <span>${t.task_id}</span>
        <span class="task-status stage-badge ${statusClass(t.status)}">${STATUS_NAMES[t.current_stage] || t.current_stage}</span>
      </div>
      <small>${t.created_at || ''}</small>
    </div>
  `).join('');

  container.querySelectorAll('.task-card').forEach(card => {
    card.onclick = () => openTask(card.dataset.id);
  });
}

function statusClass(status) {
  const map = {
    completed: 'completed', running: 'running', failed: 'failed',
    input_collecting: 'blocked', confirmation: 'blocked',
    requirement_optimizing: 'running', planning: 'running',
    prompt_optimizing: 'running', executing: 'running',
    verifying: 'running', archiving: 'running',
    cancelled: 'failed',
  };
  return map[status] || 'pending';
}

// ===== 任务详情 =====
async function openTask(taskId) {
  currentTaskId = taskId;
  showView('task');
  document.getElementById('task-title').textContent = taskId;
  document.getElementById('task-id-label').textContent = taskId;
  document.getElementById('live-log').innerHTML = '';

  document.getElementById('btn-run').onclick = () => startPipeline(taskId);

  await refreshTask();
  connectWS(taskId);
}

function closeTask() {
  currentTaskId = null;
  if (ws) { ws.close(); ws = null; }
}

async function refreshTask() {
  if (!currentTaskId) return;
  try {
    const task = await api(`/tasks/${currentTaskId}`);
    if (!task) return;

    renderPipeline(task);
    renderConfirmGate(task);
    renderError(task);
    loadArtifacts();
    loadDebatePanel(task);
    updateRunButton(task);
  } catch (err) {
    addLog('error', `刷新任务状态失败: ${err.message}`);
  }
}

// ===== 启动流水线 =====
async function startPipeline(taskId) {
  const btn = document.getElementById('btn-run');
  btn.disabled = true;
  btn.textContent = '启动中...';

  try {
    await api(`/tasks/${taskId}/run`, { method: 'POST' });
    addLog('info', '流水线已启动');
    await refreshTask();
  } catch (err) {
    addLog('error', `启动失败: ${err.message}`);
    btn.disabled = false;
    btn.textContent = '启动流水线';
  }
}

// ===== 启动按钮状态 =====
function updateRunButton(task) {
  const btn = document.getElementById('btn-run');
  if (!btn) return;
  const runningStages = ['requirement_optimizing', 'planning', 'prompt_optimizing', 'executing', 'verifying', 'archiving'];
  if (task.status === 'completed' || task.status === 'cancelled') {
    btn.style.display = 'none';
  } else if (task.status === 'failed') {
    btn.disabled = false;
    btn.textContent = '重新启动';
    btn.style.display = '';
  } else if (runningStages.includes(task.status) || task.status === 'running') {
    btn.disabled = true;
    btn.textContent = '运行中...';
    btn.style.display = '';
  } else if (task.status === 'confirmation') {
    btn.style.display = 'none';
  } else {
    btn.disabled = false;
    btn.textContent = '启动流水线';
    btn.style.display = '';
  }
}

// ===== 流水线进度 =====
function renderPipeline(task) {
  const container = document.getElementById('pipeline-progress');
  const stages = task.stages || {};

  container.innerHTML = Object.entries(stages).map(([name, s]) => {
    const displayName = STAGE_NAMES[name] || name;
    const agentName = AGENT_NAMES[s.agent] || s.agent || '';
    return `<span class="stage-badge ${s.status}">${displayName}<small>${agentName}</small></span>`;
  }).join('');
}

// ===== 错误显示 =====
function renderError(task) {
  const errEl = document.getElementById('task-error');
  if (!errEl) return;
  if (task.error) {
    errEl.textContent = task.error;
    errEl.style.display = '';
  } else {
    errEl.style.display = 'none';
  }
}

// ===== 确认门 =====
function renderConfirmGate(task) {
  const gate = document.getElementById('confirm-gate');
  if (task.status !== 'confirmation') {
    gate.style.display = 'none';
    return;
  }

  gate.style.display = '';
  loadProposal();
}

async function loadProposal() {
  try {
    const prop = await api(`/tasks/${currentTaskId}/proposals`);
    document.getElementById('proposal-content').textContent = prop.optimized || '暂无优化方案';
  } catch {
    document.getElementById('proposal-content').textContent = '方案尚未生成...';
  }
}

document.getElementById('btn-confirm').onclick = () => submitConfirm('confirm');
document.getElementById('btn-revise').onclick = () => {
  document.getElementById('revise-feedback').style.display = '';
};
document.getElementById('btn-reject').onclick = () => submitConfirm('reject');

async function submitConfirm(action) {
  const feedback = document.getElementById('revise-feedback').value.trim();
  try {
    await api(`/tasks/${currentTaskId}/confirm`, {
      method: 'POST',
      body: JSON.stringify({ action, feedback: feedback || undefined }),
    });
    document.getElementById('confirm-gate').style.display = 'none';
    document.getElementById('revise-feedback').style.display = 'none';
    document.getElementById('revise-feedback').value = '';
    addLog('info', `确认操作：${action === 'confirm' ? '确认' : action === 'revise' ? '修改' : '拒绝'}`);
    await refreshTask();
  } catch (err) {
    addLog('error', `确认操作失败: ${err.message}`);
  }
}

// ===== 产物文件 =====
async function loadArtifacts() {
  if (!currentTaskId) return;
  try {
    const artifacts = await api(`/tasks/${currentTaskId}/artifacts`);
    const container = document.getElementById('artifacts-list');
    if (!artifacts || artifacts.length === 0) {
      container.innerHTML = '<p style="color:var(--text-muted);font-size:0.85rem">暂无产物文件</p>';
      return;
    }
    container.innerHTML = artifacts.map(a => `
      <a class="artifact-link" href="${a.path}" target="_blank">${a.name} <span style="opacity:0.5">${formatSize(a.size)}</span></a>
    `).join('');
  } catch {
    // 产物目录可能尚未生成
  }
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / 1048576).toFixed(1) + ' MB';
}

// ===== 多 Agent 辩论面板 =====
const DEBATE_AGENT_LABELS = {
  prompt_optimizer: { name: '通用型', icon: '&#9878;', desc: '平衡完整性与可执行性' },
  prompt_optimizer_v2: { name: '激进型', icon: '&#9889;', desc: '创造性 + 故事化叙事' },
  prompt_optimizer_v3: { name: '保守型', icon: '&#9873;', desc: '边界条件 + 安全优先' },
};

async function loadDebatePanel(task) {
  const panel = document.getElementById('debate-panel');
  if (!panel) return;

  const stageIdx = (task.stages && task.stages.prompt_optimizing)
    ? Object.keys(task.stages).indexOf('prompt_optimizing') : -1;
  const currentIdx = (task.stages)
    ? Object.values(task.stages).findIndex(s => s.status === 'running') : -1;

  // Show panel when prompt_optimizing is completed or running, or any later stage
  const debateDone = stageIdx >= 0 && task.stages.prompt_optimizing.status === 'completed';
  const debateRunning = task.current_stage === 'prompt_optimizing';
  const pastDebate = currentIdx > stageIdx && stageIdx >= 0;

  if (!debateDone && !debateRunning && !pastDebate) {
    panel.style.display = 'none';
    return;
  }

  panel.style.display = '';

  // Try to load debate artifacts
  try {
    const base = `/api/tasks/${currentTaskId}/artifacts`;
    const resp = await fetch(base);
    const files = await resp.json();
    if (!files || !files.length) return;

    const hasOptimalPrompt = files.find(f => f.name === 'optimal_prompt.md');
    const hasV2 = files.find(f => f.name === 'optimal_prompt_v2.md');
    const hasV3 = files.find(f => f.name === 'optimal_prompt_v3.md');
    const hasVerdict = files.find(f => f.name === 'debate_verdict.json');

    if (!hasOptimalPrompt) return;

    // Load content of each prompt asynchronously
    const loadContent = async (filename) => {
      try {
        const f = files.find(x => x.name === filename);
        if (!f) return '（未生成）';
        const r = await fetch(f.path);
        return await r.text();
      } catch { return '（加载失败）'; }
    };

    const [v1, v2, v3, verdictRaw] = await Promise.all([
      loadContent('optimal_prompt.md'),
      loadContent('optimal_prompt_v2.md'),
      loadContent('optimal_prompt_v3.md'),
      loadContent('debate_verdict.json'),
    ]);

    // Parse verdict
    let verdict = null;
    try { verdict = JSON.parse(verdictRaw); } catch { /* ignore */ }

    renderDebateOutputs(v1, v2, v3, verdict);
  } catch {
    // Debate artifacts not yet available
  }
}

function renderDebateOutputs(v1, v2, v3, verdict) {
  // Render verdict banner
  const verdictEl = document.getElementById('debate-verdict');
  const winnerBadge = document.getElementById('debate-winner-badge');

  if (verdict && verdict.winner) {
    const winnerInfo = DEBATE_AGENT_LABELS[verdict.winner] || { name: verdict.winner };
    verdictEl.style.display = '';
    winnerBadge.style.display = '';
    winnerBadge.innerHTML = `&#127942; 胜出: <strong>${winnerInfo.name}</strong>`;

    const scoresHtml = verdict.scores
      ? Object.entries(verdict.scores).map(([id, s]) => {
          const label = DEBATE_AGENT_LABELS[id] || { name: id };
          const total = s.completeness + s.clarity + s.actionability + s.robustness;
          return `<div><span>${label.name}</span><span class="score-bar"><span class="score-fill" style="width:${(total/4)*100}%"></span></span><span>${(total/4).toFixed(1)}</span></div>`;
        }).join('')
      : '';

    verdictEl.innerHTML = `
      <div class="verdict-reason">${verdict.reasoning || ''}</div>
      <div class="verdict-scores">${scoresHtml}</div>`;
  } else {
    verdictEl.style.display = 'none';
    winnerBadge.style.display = 'none';
  }

  // Render three outputs side by side
  const container = document.getElementById('debate-outputs');
  const agents = [
    { id: 'prompt_optimizer', label: DEBATE_AGENT_LABELS.prompt_optimizer, content: v1, isWinner: verdict && verdict.winner === 'prompt_optimizer' },
    { id: 'prompt_optimizer_v2', label: DEBATE_AGENT_LABELS.prompt_optimizer_v2, content: v2, isWinner: verdict && verdict.winner === 'prompt_optimizer_v2' },
    { id: 'prompt_optimizer_v3', label: DEBATE_AGENT_LABELS.prompt_optimizer_v3, content: v3, isWinner: verdict && verdict.winner === 'prompt_optimizer_v3' },
  ];

  container.innerHTML = agents.map(a => `
    <div class="debate-agent-card ${a.isWinner ? 'winner' : ''}">
      <div class="debate-agent-header">
        <span>${a.label.icon} ${a.label.name}</span>
        ${a.isWinner ? '<span class="winner-tag">&#127942;</span>' : ''}
      </div>
      <div class="debate-agent-desc">${a.label.desc}</div>
      <div class="debate-agent-content">
        <pre>${escapeHTML(a.content.substring(0, 1500))}${a.content.length > 1500 ? '\n... (已截断)' : ''}</pre>
      </div>
    </div>
  `).join('');
}

function escapeHTML(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

// ===== WebSocket =====
function connectWS(taskId) {
  if (ws) ws.close();
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  ws = new WebSocket(`${proto}//${location.host}/ws/tasks/${taskId}`);

  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    if (msg.type === 'state') {
      renderPipeline(msg.data);
      renderConfirmGate(msg.data);
      updateRunButton(msg.data);
    } else if (msg.type === 'heartbeat') {
      // ignore
    } else if (msg.type === 'stage_changed') {
      const from = STAGE_NAMES[msg.data?.from] || msg.data?.from || '';
      const to = STAGE_NAMES[msg.data?.to] || msg.data?.to || '';
      addLog('info', `${from} → ${to}`);
      refreshTask();
    } else if (msg.type === 'pipeline_completed') {
      addLog('info', '流水线已完成');
      refreshTask();
    } else if (msg.type === 'pipeline_paused') {
      addLog('info', `流水线暂停，等待: ${STATUS_NAMES[msg.data?.waiting_for] || msg.data?.waiting_for || ''}`);
      refreshTask();
    } else if (msg.type === 'pipeline_error') {
      addLog('error', `流水线错误: ${msg.data?.error || '未知错误'}`);
      refreshTask();
    } else if (msg.type === 'confirmation_handled') {
      addLog('info', `确认操作: ${msg.data?.action}`);
      refreshTask();
    } else {
      const stageName = STAGE_NAMES[msg.data?.stage] || msg.data?.stage || '';
      addLog('info', `[${msg.type}] ${stageName} ${msg.data?.error || ''}`);
      refreshTask();
    }
  };

  ws.onerror = () => addLog('error', 'WebSocket 连接错误');
  ws.onclose = () => addLog('warn', 'WebSocket 连接断开');
}

// ===== 实时日志 =====
function addLog(level, message) {
  const panel = document.getElementById('live-log');
  const entry = document.createElement('div');
  entry.className = `log-entry ${level}`;
  const time = new Date().toLocaleTimeString('zh-CN');
  entry.textContent = `[${time}] ${message}`;
  panel.appendChild(entry);
  panel.scrollTop = panel.scrollHeight;
}

// ===== 初始化 =====
loadTasks();
