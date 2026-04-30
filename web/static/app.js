const API = '/api';
let currentProject = '';
let projects = [];

async function fetchJSON(url) {
    // Append project param to all API calls except /api/projects
    const separator = url.includes('?') ? '&' : '?';
    const fullUrl = (url === `${API}/projects` || !currentProject)
        ? url
        : `${url}${separator}project=${encodeURIComponent(currentProject)}`;
    const resp = await fetch(fullUrl);
    return resp.json();
}

async function loadProjects() {
    const data = await fetchJSON(`${API}/projects`);
    projects = data.projects || [];
    const sel = document.getElementById('project-selector');

    // Keep current selection if it still exists
    const currentValue = sel.value;

    sel.innerHTML = '<option value="">-- 选择项目 --</option>';
    for (const p of projects) {
        const label = `${p.title} (${p.type === 'short_story' ? '短篇' : '网文'})`;
        sel.innerHTML += `<option value="${escapeHtml(p.path)}">${escapeHtml(label)}</option>`;
    }

    // Restore selection or auto-select first
    if (currentValue && projects.some(p => p.path === currentValue)) {
        sel.value = currentValue;
        currentProject = currentValue;
    } else if (projects.length > 0 && !currentProject) {
        sel.value = projects[0].path;
        currentProject = projects[0].path;
    } else if (projects.length === 0) {
        currentProject = '';
    }

    return projects;
}

function onProjectChange() {
    const sel = document.getElementById('project-selector');
    currentProject = sel.value;

    // Refresh current tab
    const activeTab = document.querySelector('.nav-btn.active');
    if (activeTab) {
        loadTab(activeTab.dataset.tab);
    }
}

// ─── Create Project ──────────────────────────────────────────────────

function showCreateModal() {
    document.getElementById('create-modal').style.display = 'flex';
    document.getElementById('create-title').focus();
    document.getElementById('create-error').style.display = 'none';

    // Set default path
    const pathInput = document.getElementById('create-path');
    if (!pathInput.value) {
        pathInput.value = '~/Documents/drafts/';
    }

    // Show/hide folder picker based on browser support
    const pickBtn = document.getElementById('pick-folder-btn');
    if (typeof window.showDirectoryPicker === 'function') {
        pickBtn.style.display = '';
    } else {
        pickBtn.style.display = 'none';
    }
}

function closeCreateModal() {
    document.getElementById('create-modal').style.display = 'none';
    document.getElementById('create-title').value = '';
    document.getElementById('create-error').style.display = 'none';
}

async function pickFolder() {
    try {
        const dirHandle = await window.showDirectoryPicker({ mode: 'readwrite' });
        document.getElementById('create-path').value = dirHandle.name;
    } catch (e) {
        // User cancelled or API not available - ignore
    }
}

async function submitCreateProject() {
    const title = document.getElementById('create-title').value.trim();
    const path = document.getElementById('create-path').value.trim();
    const type = document.getElementById('create-type').value;
    const errorEl = document.getElementById('create-error');
    const btn = document.getElementById('create-submit-btn');

    if (!title || !path) {
        errorEl.textContent = '请填写标题和路径';
        errorEl.style.display = 'block';
        return;
    }

    btn.textContent = '创建中...';
    btn.disabled = true;
    errorEl.style.display = 'none';

    try {
        const resp = await fetch(`${API}/projects`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, path, type }),
        });
        const data = await resp.json();

        if (!resp.ok) {
            errorEl.textContent = data.error || '创建失败';
            errorEl.style.display = 'block';
            return;
        }

        closeCreateModal();
        await loadProjects();

        // Select the newly created project
        const sel = document.getElementById('project-selector');
        sel.value = data.path;
        currentProject = data.path;
        loadTab('dashboard');
    } catch (e) {
        errorEl.textContent = '网络错误: ' + e.message;
        errorEl.style.display = 'block';
    } finally {
        btn.textContent = '创建项目';
        btn.disabled = false;
    }
}

// Close modal on overlay click
document.addEventListener('click', (e) => {
    if (e.target.id === 'create-modal') {
        closeCreateModal();
    }
});

// Close modal on Escape
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeCreateModal();
    }
});

function renderDashboard(data) {
    if (data.error) {
        return `<div class="panel">
            <h2>欢迎使用 Novel Writer</h2>
            <div class="how-to-use">
                <h3>开始使用</h3>
                <p>还没有小说项目。你可以：</p>
                <p style="margin-top:12px;">
                    <button class="create-project-btn" onclick="showCreateModal()">+ 新建项目</button>
                </p>
                <p style="margin-top:12px;color:#666;">或在终端运行：<code>novelwriting init ./我的小说 "小说标题"</code></p>
            </div>
        </div>`;
    }

    const stages = data.stages || {};
    const statusLabels = { pending: '⏳ 未开始', in_progress: '🔄 进行中', completed: '✅ 已完成', dirty: '⚠️ 需更新' };
    let html = '<div class="dashboard-toolbar"><button class="create-project-btn" onclick="showCreateModal()">+ 新建项目</button></div>';
    html += '<div class="panel"><h2>项目进度</h2><div class="stage-list">';
    for (const [name, info] of Object.entries(stages)) {
        const cls = info.status === 'completed' ? 'completed' : info.status === 'in_progress' ? 'in_progress' : '';
        html += `<div class="stage-card ${cls}">
            <h3>${name}</h3>
            <div class="status">${statusLabels[info.status] || info.status}</div>
            <div class="version">v${info.version || 0}</div>
        </div>`;
    }
    html += '</div></div>';

    if (data.work_queue_pending > 0) {
        html += `<div class="work-queue"><h2>工作队列 (${data.work_queue_pending})</h2></div>`;
    }

    return html;
}

async function renderChapters() {
    const data = await fetchJSON(`${API}/chapters`);
    const chapters = data.chapters || [];
    let html = '<div class="panel"><h2>正文章节</h2><div class="chapter-list">';
    for (const ch of chapters) {
        html += `<div class="chapter-item" onclick="loadChapter('${ch}')">${ch}</div>`;
    }
    html += '</div><div id="chapter-content"></div></div>';
    return html;
}

async function loadChapter(filename) {
    const data = await fetchJSON(`${API}/chapters/${encodeURIComponent(filename)}`);
    document.getElementById('chapter-content').innerHTML =
        `<div class="chapter-content">${escapeHtml(data.content || '')}</div>`;
}

function escapeHtml(text) {
    return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

async function renderOutline() {
    const data = await fetchJSON(`${API}/outline`);
    const files = data.files || {};
    let html = '<div class="panel"><h2>大纲</h2>';
    for (const [name, content] of Object.entries(files)) {
        html += `<h3>${name}</h3><pre style="white-space:pre-wrap;background:#1a1a2e;padding:12px;border-radius:6px;margin-bottom:12px;">${escapeHtml(content)}</pre>`;
    }
    html += '</div>';
    return html;
}

async function renderCharacters() {
    const data = await fetchJSON(`${API}/knowledge/characters`);
    const entries = data.entries || [];
    let html = '<div class="panel"><h2>人物</h2>';
    if (entries.length === 0) {
        html += '<p class="loading">暂无人物数据</p>';
    } else {
        for (const name of entries) {
            html += `<div class="chapter-item" onclick="loadCharacter('${name}')">${name}</div>`;
        }
    }
    html += '<div id="character-detail"></div></div>';
    return html;
}

async function loadCharacter(name) {
    const data = await fetchJSON(`${API}/knowledge/characters/${encodeURIComponent(name)}`);
    document.getElementById('character-detail').innerHTML =
        `<div class="chapter-content"><pre>${escapeHtml(JSON.stringify(data, null, 2))}</pre></div>`;
}

async function renderWorld() {
    const data = await fetchJSON(`${API}/knowledge/world`);
    const entries = data.entries || [];
    let html = '<div class="panel"><h2>世界观设定</h2>';
    for (const name of entries) {
        html += `<div class="chapter-item" onclick="loadWorldEntry('${name}')">${name}</div>`;
    }
    html += '<div id="world-detail"></div></div>';
    return html;
}

async function loadWorldEntry(name) {
    const data = await fetchJSON(`${API}/knowledge/world/${encodeURIComponent(name)}`);
    document.getElementById('world-detail').innerHTML =
        `<div class="chapter-content"><pre>${escapeHtml(JSON.stringify(data, null, 2))}</pre></div>`;
}

async function renderReview() {
    const data = await fetchJSON(`${API}/reviews`);
    const files = data.files || {};
    let html = '<div class="panel"><h2>审阅报告</h2>';
    for (const [name, content] of Object.entries(files)) {
        html += `<details style="margin-bottom:12px;"><summary>${name}</summary><div class="chapter-content">${escapeHtml(content)}</div></details>`;
    }
    html += '</div>';
    return html;
}

// ─── Command Center ────────────────────────────────────────────────

const COMMAND_DEFS = [
    {
        stage: 'outline',
        label: '大纲构思',
        commands: [
            { id: 'outline-generate', label: '生成大纲', text: '/znovel-outline generate', hint: '基于模板和用户创意生成完整大纲', args: [] },
            { id: 'outline-revise', label: '修订大纲', text: '/znovel-outline revise', hint: '修改指定的大纲文件', args: [{ name: 'file', placeholder: '文件名', default: 'story_structure.yml' }] },
        ],
    },
    {
        stage: 'world',
        label: '背景设定',
        commands: [
            { id: 'world-generate-light', label: '生成背景 (轻量)', text: '/znovel-world generate --depth light', hint: '仅世界观总览 + 力量体系', args: [] },
            { id: 'world-generate-deep', label: '生成背景 (深度)', text: '/znovel-world generate --depth deep', hint: '完整世界观含地理、历史、势力', args: [] },
            { id: 'world-revise', label: '修订背景', text: '/znovel-world revise', hint: '修改指定世界观条目', args: [{ name: '条目名', placeholder: '条目名', default: 'overview' }] },
        ],
    },
    {
        stage: 'character',
        label: '人物设定',
        commands: [
            { id: 'character-generate-light', label: '生成人物 (轻量)', text: '/znovel-character generate --depth light', hint: '仅主要人物卡片', args: [] },
            { id: 'character-generate-deep', label: '生成人物 (深度)', text: '/znovel-character generate --depth deep', hint: '完整档案+成长弧线+关系网', args: [] },
            { id: 'character-revise', label: '修订人物', text: '/znovel-character revise', hint: '修改指定人物设定', args: [{ name: '人物名', placeholder: '人物名', default: '' }] },
        ],
    },
    {
        stage: 'draft',
        label: '正文编写',
        commands: [
            { id: 'draft-write', label: '写新章节', text: '/znovel-draft write', hint: '基于大纲和三层上下文写指定章节', args: [{ name: '章节号', placeholder: '章节号', default: '1' }] },
            { id: 'draft-rewrite', label: '重写章节', text: '/znovel-draft rewrite', hint: '根据原因修订指定章节', args: [{ name: '章节号', placeholder: '章节号', default: '' }, { name: 'reason', placeholder: '原因', default: '' }] },
        ],
    },
    {
        stage: 'review',
        label: '审阅校对',
        commands: [
            { id: 'review-check', label: '审阅章节', text: '/znovel-review check', hint: '多维度检查章节质量', args: [{ name: '章节号', placeholder: '章节号', default: '1' }] },
            { id: 'review-report', label: '全局审阅报告', text: '/znovel-review report', hint: '汇总所有已审阅章节', args: [] },
        ],
    },
    {
        stage: 'director',
        label: '主编指令',
        commands: [
            { id: 'director-status', label: '查看状态', text: '/novel status', hint: '查看项目整体进度和工作队列', args: [] },
            { id: 'director-continue', label: '继续推进', text: '/novel continue', hint: '从当前阶段自动继续', args: [] },
            { id: 'director-workqueue', label: '查看工作队列', text: '/novel work-queue', hint: '查看审阅发现的待处理问题', args: [] },
        ],
    },
];

function getStageStatus(stages, stage) {
    if (!stages || !stages[stage]) return 'pending';
    return stages[stage].status || 'pending';
}

function getLastChapter(stages) {
    if (!stages || !stages['draft']) return 0;
    return stages['draft'].last_chapter || 0;
}

function getNextChapter(stages) {
    return getLastChapter(stages) + 1;
}

function renderCommandCard(cmd, stages) {
    // Fill in dynamic defaults based on project state
    let text = cmd.text;
    const args = JSON.parse(JSON.stringify(cmd.args)); // deep copy

    for (const arg of args) {
        if (arg.name === '章节号' && arg.default === '1') {
            arg.default = String(getNextChapter(stages));
        }
        if (arg.name === 'file' && arg.default === 'story_structure.yml') {
            arg.default = 'story_structure.yml';
        }
    }

    const hasArgs = args.length > 0;
    let argsHtml = '';
    if (hasArgs) {
        argsHtml = '<div style="margin-top:6px;display:flex;gap:6px;flex-wrap:wrap;">';
        for (const arg of args) {
            argsHtml += `<input class="arg-input" type="text" placeholder="${arg.placeholder}" value="${arg.default}" data-arg="${arg.name}">`;
        }
        argsHtml += '</div>';
    }

    const cmdId = cmd.id;
    return `
        <div class="cmd-card" id="card-${cmdId}">
            <div class="cmd-info">
                <div class="cmd-label">${cmd.label}</div>
                <div class="cmd-text" id="cmd-text-${cmdId}">${text}${hasArgs ? ' ' + args.map(a => a.default).join(' ') : ''}</div>
                <div class="cmd-hint">${cmd.hint}</div>
                ${argsHtml}
            </div>
            <button class="cmd-btn" onclick="copyCommand('${cmdId}')" id="btn-${cmdId}">📋 复制</button>
        </div>`;
}

function buildCommandText(cmd, stages) {
    let text = cmd.text;
    const args = cmd.args || [];
    const values = [];
    for (const arg of args) {
        if (arg.name === '章节号') values.push(String(getNextChapter(stages)));
        else values.push(arg.default || '');
    }
    if (values.length > 0) text += ' ' + values.join(' ');
    return text;
}

function copyCommand(cmdId) {
    const cmd = COMMAND_DEFS.flatMap(d => d.commands).find(c => c.id === cmdId);
    if (!cmd) return;

    // Read current arg values from inputs
    let text = cmd.text;
    if (cmd.args && cmd.args.length > 0) {
        const values = [];
        for (const arg of cmd.args) {
            const input = document.querySelector(`#card-${cmdId} [data-arg="${arg.name}"]`);
            values.push(input ? input.value : arg.default);
        }
        text += ' ' + values.join(' ');
    }

    navigator.clipboard.writeText(text).then(() => {
        const btn = document.getElementById('btn-' + cmdId);
        btn.textContent = '✅ 已复制';
        btn.classList.add('copied');
        setTimeout(() => {
            btn.textContent = '📋 复制';
            btn.classList.remove('copied');
        }, 1500);
    }).catch(() => {
        // Fallback for older browsers
        const el = document.getElementById('cmd-text-' + cmdId);
        const range = document.createRange();
        range.selectNodeContents(el);
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
    });
}

async function renderCommands() {
    const statusData = await fetchJSON(`${API}/status`);
    const stages = statusData.stages || {};

    let html = `
    <div class="how-to-use">
        <h3>⚡ 如何使用命令中心</h3>
        <p>以下每个按钮对应一条 <code>/znovel-*</code> 命令。点击<strong>复制</strong>按钮，然后在 <strong>Claude Code 终端</strong>中粘贴执行。<br>
        命令会根据当前项目状态自动填充参数（如章节号自动设为下一章）。执行完成后回到此页面刷新即可看到最新结果。</p>
    </div>`;

    for (const section of COMMAND_DEFS) {
        const stageStatus = getStageStatus(stages, section.stage);
        const statusLabels = { completed: '已完成', in_progress: '进行中', pending: '未开始', dirty: '需更新' };
        const statusCls = stageStatus;
        const statusLabel = statusLabels[stageStatus] || stageStatus;

        html += `<div class="command-section">`;
        html += `<h3>${section.label} <span class="stage-status ${statusCls}">${statusLabel}</span></h3>`;
        html += `<div class="cmd-grid">`;
        for (const cmd of section.commands) {
            html += renderCommandCard(cmd, stages);
        }
        html += `</div></div>`;
    }

    return html;
}

// Update arg values on input
document.addEventListener('input', (e) => {
    if (!e.target.classList.contains('arg-input')) return;
    const card = e.target.closest('.cmd-card');
    if (!card) return;
    const cmdId = card.id.replace('card-', '');
    const cmd = COMMAND_DEFS.flatMap(d => d.commands).find(c => c.id === cmdId);
    if (!cmd) return;

    let text = cmd.text;
    const values = [];
    for (const arg of (cmd.args || [])) {
        const inp = card.querySelector(`[data-arg="${arg.name}"]`);
        values.push(inp ? inp.value : arg.default);
    }
    if (values.length > 0) text += ' ' + values.join(' ');
    const el = document.getElementById('cmd-text-' + cmdId);
    if (el) el.textContent = text;
});

const renderers = {
    dashboard: async () => {
        // First ensure projects are loaded
        if (projects.length === 0) {
            await loadProjects();
        }
        if (!currentProject) {
            document.getElementById('project-title').textContent = '📖 Novel Writer';
            return renderDashboard({ error: 'no-project' });
        }
        const data = await fetchJSON(`${API}/status`);
        if (data.error) return '<div class="error">未找到小说项目。请在项目目录下运行。</div>';
        document.getElementById('project-title').textContent = `📖 ${data.project?.title || 'Novel Writer'}`;
        return renderDashboard(data);
    },
    commands: async () => {
        if (!currentProject) {
            return '<div class="panel"><h2>请先选择一个项目</h2><p class="loading">在顶部下拉框中选择项目后可用</p></div>';
        }
        const data = await fetchJSON(`${API}/status`);
        if (data.error) return '<div class="error">项目无效。请检查项目路径。</div>';
        document.getElementById('project-title').textContent = `📖 ${data.project?.title || 'Novel Writer'}`;
        return await renderCommands();
    },
    chapters: async () => {
        if (!currentProject) return '<div class="panel"><h2>请先选择一个项目</h2></div>';
        return await renderChapters();
    },
    outline: async () => {
        if (!currentProject) return '<div class="panel"><h2>请先选择一个项目</h2></div>';
        return await renderOutline();
    },
    characters: async () => {
        if (!currentProject) return '<div class="panel"><h2>请先选择一个项目</h2></div>';
        return await renderCharacters();
    },
    world: async () => {
        if (!currentProject) return '<div class="panel"><h2>请先选择一个项目</h2></div>';
        return await renderWorld();
    },
    review: async () => {
        if (!currentProject) return '<div class="panel"><h2>请先选择一个项目</h2></div>';
        return await renderReview();
    },
};

async function loadTab(tab) {
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    document.querySelector(`[data-tab="${tab}"]`)?.classList.add('active');

    const content = document.getElementById('content');
    content.innerHTML = '<div class="loading">加载中...</div>';

    try {
        const renderer = renderers[tab];
        if (renderer) {
            content.innerHTML = await renderer();
        }
    } catch (e) {
        content.innerHTML = `<div class="error">加载失败: ${e.message}</div>`;
    }
}

// ─── Chat Panel ───────────────────────────────────────────────────────

function clearChat() {
    const container = document.getElementById('chat-messages');
    container.innerHTML = `
        <div class="chat-welcome">
            <p>欢迎使用 Novel Writer</p>
            <p class="chat-hint">输入命令或自然语言与Claude对话</p>
        </div>`;

    // 清空服务器端历史
    fetch(`${API}/history`, { method: 'DELETE' }).catch(console.error);
}

function appendChatMessage(role, text) {
    const container = document.getElementById('chat-messages');
    // Remove welcome message on first real message
    const welcome = container.querySelector('.chat-welcome');
    if (welcome) welcome.remove();

    const div = document.createElement('div');
    div.className = `chat-message ${role}`;
    div.innerHTML = `
        <div class="msg-role">${role === 'user' ? '你' : role === 'assistant' ? 'Claude' : '错误'}</div>
        <div class="msg-content">${escapeHtml(text)}</div>
    `;

    container.appendChild(div);
    scrollToBottom();

    return div;
}

function scrollToBottom() {
    const container = document.getElementById('chat-messages');
    container.scrollTop = container.scrollHeight;
}

async function sendMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    if (!message) return;

    input.value = '';

    // 显示用户消息
    appendChatMessage('user', message);

    // 禁用发送按钮
    const sendBtn = document.querySelector('.chat-send-btn');
    sendBtn.disabled = true;
    sendBtn.textContent = '发送中...';

    try {
        const response = await fetch(`${API}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message, project: currentProject })
        });

        if (!response.ok) {
            throw new Error('请求失败');
        }

        // 创建SSE读取器
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let currentMessage = null;

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));
                        handleSSEEvent(data, currentMessage);
                        if (data.type === 'start') {
                            currentMessage = appendChatMessage('assistant', '');
                        }
                    } catch (e) {
                        console.error('SSE解析错误:', e);
                    }
                }
            }
        }
    } catch (error) {
        appendChatMessage('error', '发送失败: ' + error.message);
    } finally {
        // 恢复发送按钮
        const sendBtn = document.querySelector('.chat-send-btn');
        sendBtn.disabled = false;
        sendBtn.textContent = '发送';
    }
}

function handleSSEEvent(data, currentMessage) {
    switch (data.type) {
        case 'output':
            if (currentMessage) {
                const content = currentMessage.querySelector('.msg-content');
                if (content) content.textContent += data.content;
                scrollToBottom();
            }
            break;
        case 'error':
            if (currentMessage) {
                currentMessage.classList.remove('assistant');
                currentMessage.classList.add('error');
                const content = currentMessage.querySelector('.msg-content');
                if (content) content.textContent = data.content;
            }
            break;
    }
}

// ─── Init ─────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', async () => {
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', () => loadTab(btn.dataset.tab));
    });

    const chatInput = document.getElementById('chat-input');
    if (chatInput) {
        chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    }

    await loadProjects();
    loadTab('dashboard');
});
