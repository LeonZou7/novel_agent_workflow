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

const renderers = {
    dashboard: async () => {
        const data = await fetchJSON(`${API}/status`);
        if (data.error) return '<div class="error">未找到小说项目。请在项目目录下运行。</div>';
        document.getElementById('project-title').textContent = `📖 ${data.project?.title || 'Novel Writer'}`;
        return renderDashboard(data);
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
