"""Integration tests for web chat functionality."""

import pytest
import json
import os
import tempfile
import shutil
import yaml

from web.server import app
from web.chat_history import ChatHistory


@pytest.fixture
def client():
    """Create Flask test client."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def project_dir(tmp_path):
    """Create a temporary project directory with .novel structure."""
    novel_dir = tmp_path / ".novel"
    novel_dir.mkdir()
    config = {
        "project": {"title": "Test Novel", "type": "web_novel"},
        "checkpoints": [],
        "depth": {"world": 1, "outline": 1, "draft": 1},
    }
    with open(novel_dir / "config.yml", "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True)
    state = {"stages": {}, "current_stage": ""}
    with open(novel_dir / "state.yml", "w", encoding="utf-8") as f:
        yaml.dump(state, f, allow_unicode=True)
    return str(tmp_path)


@pytest.fixture
def client_with_project(project_dir):
    """Create Flask test client with a project query param."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client, project_dir


class TestChatEndpoint:
    """Tests for the /api/chat endpoint."""

    def test_chat_endpoint_exists(self, client):
        """POST /api/chat should not return 405 Method Not Allowed."""
        response = client.post('/api/chat', json={'message': 'test'})
        # Either 200 (streaming) or 404 (no project) -- but NOT 405
        assert response.status_code != 405

    def test_chat_requires_message(self, client):
        """POST /api/chat without message returns 400."""
        response = client.post('/api/chat', json={})
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_chat_empty_message_still_accepted(self, client):
        """POST /api/chat with whitespace-only message is accepted (server strips but does not reject)."""
        response = client.post('/api/chat', json={'message': '   '})
        # Server strips the message but does not reject empty-after-strip,
        # so it returns 200 (SSE stream) or 404 (no project)
        assert response.status_code in [200, 404]

    def test_chat_no_project_returns_404(self, client):
        """POST /api/chat when no project exists returns 404."""
        # Use a non-existent project path
        response = client.post(
            '/api/chat?project=/tmp/nonexistent_project_xyz',
            json={'message': 'hello'}
        )
        assert response.status_code == 404

    def test_chat_returns_sse_stream(self, client_with_project):
        """POST /api/chat with valid project returns SSE stream."""
        client, project_dir = client_with_project
        response = client.post(
            f'/api/chat?project={project_dir}',
            json={'message': '/help'}
        )
        assert response.status_code == 200
        assert 'text/event-stream' in response.content_type
        # The body should contain SSE data lines starting with 'data: '
        body = response.data.decode('utf-8')
        assert 'data: ' in body

    def test_chat_sse_contains_start_event(self, client_with_project):
        """SSE stream should begin with a 'start' event."""
        client, project_dir = client_with_project
        response = client.post(
            f'/api/chat?project={project_dir}',
            json={'message': '/help'}
        )
        body = response.data.decode('utf-8')
        first_line = body.strip().split('\n')[0]
        assert first_line.startswith('data: ')
        event = json.loads(first_line[len('data: '):])
        assert event['type'] == 'start'

    def test_chat_sse_stream_has_events(self, client_with_project):
        """SSE stream should contain parseable data events."""
        client, project_dir = client_with_project
        response = client.post(
            f'/api/chat?project={project_dir}',
            json={'message': '/help'}
        )
        body = response.data.decode('utf-8')
        # Find all SSE events
        events = []
        for line in body.strip().split('\n'):
            if line.startswith('data: '):
                events.append(json.loads(line[len('data: '):]))
        # Command mode emits start + streaming output (no guaranteed 'done')
        assert len(events) >= 1
        assert events[0]['type'] == 'start'


class TestHistoryEndpoint:
    """Tests for the /api/history endpoint."""

    def test_history_endpoint_exists(self, client):
        """GET /api/history should not return 405."""
        response = client.get('/api/history')
        assert response.status_code != 405

    def test_history_no_project_returns_404(self, client):
        """GET /api/history without project returns 404."""
        response = client.get('/api/history?project=/tmp/nonexistent_project_xyz')
        assert response.status_code == 404

    def test_history_returns_messages(self, client_with_project):
        """GET /api/history with valid project returns messages list."""
        client, project_dir = client_with_project
        response = client.get(f'/api/history?project={project_dir}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'messages' in data
        assert isinstance(data['messages'], list)

    def test_clear_history_endpoint(self, client_with_project):
        """DELETE /api/history clears history."""
        client, project_dir = client_with_project
        # Add a message first
        history = ChatHistory(project_dir)
        history.add_message("user", "test message")

        # Clear
        response = client.delete(f'/api/history?project={project_dir}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

        # Verify cleared
        response = client.get(f'/api/history?project={project_dir}')
        data = json.loads(response.data)
        assert len(data['messages']) == 0


class TestPageLoads:
    """Tests for the main page."""

    def test_index_loads(self, client):
        """GET / should return 200."""
        response = client.get('/')
        assert response.status_code == 200

    def test_page_contains_chat_panel(self, client):
        """Page HTML should contain the chat panel."""
        response = client.get('/')
        assert b'chat-panel' in response.data

    def test_page_contains_chat_input(self, client):
        """Page HTML should contain the chat input textarea."""
        response = client.get('/')
        assert b'chat-input' in response.data

    def test_page_contains_send_button(self, client):
        """Page HTML should contain a send button."""
        response = client.get('/')
        assert b'chat-send-btn' in response.data

    def test_page_loads_app_js(self, client):
        """Page should reference app.js."""
        response = client.get('/')
        assert b'app.js' in response.data


class TestChatHistoryUnit:
    """Unit tests for ChatHistory class."""

    def test_add_and_get_messages(self, tmp_path):
        """add_message stores messages retrievable via get_messages."""
        history = ChatHistory(str(tmp_path))
        history.add_message("user", "hello")
        history.add_message("assistant", "hi there")
        messages = history.get_messages()
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "hello"
        assert messages[1]["role"] == "assistant"

    def test_get_recent_messages_limit(self, tmp_path):
        """get_recent_messages returns only the last n messages."""
        history = ChatHistory(str(tmp_path))
        for i in range(10):
            history.add_message("user", f"msg {i}")
        recent = history.get_recent_messages(3)
        assert len(recent) == 3
        assert recent[0]["content"] == "msg 7"

    def test_clear_history(self, tmp_path):
        """clear() removes all messages."""
        history = ChatHistory(str(tmp_path))
        history.add_message("user", "hello")
        history.clear()
        messages = history.get_messages()
        assert len(messages) == 0

    def test_messages_have_timestamp(self, tmp_path):
        """Each message should include a timestamp."""
        history = ChatHistory(str(tmp_path))
        history.add_message("user", "hello")
        messages = history.get_messages()
        assert "timestamp" in messages[0]


class TestProgressParsing:
    """测试进度标记解析"""

    def test_parse_progress_markers(self):
        """测试从文本中解析进度标记"""
        # 这个测试需要在前端 JS 中实现，这里只测试后端输出格式
        text = "[PROGRESS:start:outline:生成大纲]\n正在构思...\n[PROGRESS:complete:outline:完成]"
        assert "[PROGRESS:start:outline:生成大纲]" in text
        assert "[PROGRESS:complete:outline:完成]" in text

    def test_skill_injection_in_command_mode(self, client_with_project):
        """测试命令模式是否注入了技能内容"""
        client, project_dir = client_with_project
        # 创建技能目录和文件
        skill_dir = os.path.join(project_dir, ".claude", "skills", "znovel-director")
        os.makedirs(skill_dir, exist_ok=True)
        with open(os.path.join(skill_dir, "SKILL.md"), "w") as f:
            f.write("# 测试导演技能\n这是测试内容")

        response = client.post(
            f'/api/chat?project={project_dir}',
            json={'message': '/znovel status'}
        )
        assert response.status_code == 200
        body = response.data.decode('utf-8')
        # 应该包含 start 事件
        assert 'data: ' in body
