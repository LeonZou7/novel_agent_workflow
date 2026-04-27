const API = '/api';

async function fetchJSON(url) {
    const resp = await fetch(url);
    return resp.json();
}

function renderDashboard(data) {
    const stages = data.stages || {};
    const statusLabels = { pending: '⏳ 未开始', in_progress: '🔄 进行中', completed: '✅ 已完成', dirty: '⚠️ 需更新' };
    let html = '<div class="panel"><h2>项目进度</h2><div class="stage-list">';
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
            { id: 'outline-generate', label: '生成大纲', text: '/novel-outline generate', hint: '基于模板和用户创意生成完整大纲', args: [] },
            { id: 'outline-revise', label: '修订大纲', text: '/novel-outline revise', hint: '修改指定的大纲文件', args: [{ name: 'file', placeholder: '文件名', default: 'story_structure.yml' }] },
        ],
    },
    {
        stage: 'world',
        label: '背景设定',
        commands: [
            { id: 'world-generate-light', label: '生成背景 (轻量)', text: '/novel-world generate --depth light', hint: '仅世界观总览 + 力量体系', args: [] },
            { id: 'world-generate-deep', label: '生成背景 (深度)', text: '/novel-world generate --depth deep', hint: '完整世界观含地理、历史、势力', args: [] },
            { id: 'world-revise', label: '修订背景', text: '/novel-world revise', hint: '修改指定世界观条目', args: [{ name: '条目名', placeholder: '条目名', default: 'overview' }] },
        ],
    },
    {
        stage: 'character',
        label: '人物设定',
        commands: [
            { id: 'character-generate-light', label: '生成人物 (轻量)', text: '/novel-character generate --depth light', hint: '仅主要人物卡片', args: [] },
            { id: 'character-generate-deep', label: '生成人物 (深度)', text: '/novel-character generate --depth deep', hint: '完整档案+成长弧线+关系网', args: [] },
            { id: 'character-revise', label: '修订人物', text: '/novel-character revise', hint: '修改指定人物设定', args: [{ name: '人物名', placeholder: '人物名', default: '' }] },
        ],
    },
    {
        stage: 'draft',
        label: '正文编写',
        commands: [
            { id: 'draft-write', label: '写新章节', text: '/novel-draft write', hint: '基于大纲和三层上下文写指定章节', args: [{ name: '章节号', placeholder: '章节号', default: '1' }] },
            { id: 'draft-rewrite', label: '重写章节', text: '/novel-draft rewrite', hint: '根据原因修订指定章节', args: [{ name: '章节号', placeholder: '章节号', default: '' }, { name: 'reason', placeholder: '原因', default: '' }] },
        ],
    },
    {
        stage: 'review',
        label: '审阅校对',
        commands: [
            { id: 'review-check', label: '审阅章节', text: '/novel-review check', hint: '多维度检查章节质量', args: [{ name: '章节号', placeholder: '章节号', default: '1' }] },
            { id: 'review-report', label: '全局审阅报告', text: '/novel-review report', hint: '汇总所有已审阅章节', args: [] },
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
        <p>以下每个按钮对应一条 <code>/novel-*</code> 命令。点击<strong>复制</strong>按钮，然后在 <strong>Claude Code 终端</strong>中粘贴执行。<br>
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
        const data = await fetchJSON(`${API}/status`);
        if (data.error) return '<div class="error">未找到小说项目。请在项目目录下运行。</div>';
        document.getElementById('project-title').textContent = `📖 ${data.project?.title || 'Novel Writer'}`;
        return renderDashboard(data);
    },
    commands: async () => {
        const data = await fetchJSON(`${API}/status`);
        if (data.error) return '<div class="error">未找到小说项目。请在项目目录下运行。</div>';
        document.getElementById('project-title').textContent = `📖 ${data.project?.title || 'Novel Writer'}`;
        return await renderCommands();
    },
    chapters: renderChapters,
    outline: renderOutline,
    characters: renderCharacters,
    world: renderWorld,
    review: renderReview,
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

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', () => loadTab(btn.dataset.tab));
    });
    loadTab('dashboard');
});
