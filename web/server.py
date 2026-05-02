#!/usr/bin/env python3
"""znovel Web Server - Flask application."""

import os
import sys
import json
import subprocess
import yaml
from flask import Flask, jsonify, send_from_directory, request, Response, stream_with_context

# Add project root and scripts to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "scripts"))

from kg import KnowledgeGraph
from state import StateManager
from work_queue import WorkQueue
from projects import ProjectRegistry
from init_project import init_project
from web.cli_proxy import CLIProxy
from web.chat_history import ChatHistory

app = Flask(__name__, static_folder="static", template_folder="templates")


def get_project_root():
    """Get project root from ?project= query param or CWD fallback."""
    # Priority 1: explicit ?project= query parameter
    project = request.args.get("project")
    if project:
        project = os.path.abspath(project)
        if os.path.isdir(os.path.join(project, ".novel")):
            return project
        return None

    # Priority 2: walk up from CWD
    cwd = os.getcwd()
    while cwd != "/":
        if os.path.isdir(os.path.join(cwd, ".novel")):
            return cwd
        cwd = os.path.dirname(cwd)
    return None


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/projects")
def api_projects():
    registry = ProjectRegistry()
    projects = registry.list_projects()

    result = []
    for p in projects:
        item = dict(p)
        # Attach stage summaries if project exists on disk
        state = registry.get_state(p["path"])
        if state:
            item["stages"] = state.get("stages", {})
            item["current_stage"] = state.get("current_stage", "")
        else:
            item["stages"] = {}
            item["current_stage"] = ""
        result.append(item)

    return jsonify({"projects": result})


@app.route("/api/projects", methods=["POST"])
def api_create_project():
    data = request.get_json()
    if not data or "title" not in data or "path" not in data:
        return jsonify({"error": "title and path are required"}), 400

    title = data["title"].strip()
    path = data["path"].strip()
    novel_type = data.get("type", "web_novel")

    if not title:
        return jsonify({"error": "title is required"}), 400

    # Expand ~ and resolve to absolute path
    path = os.path.expanduser(path)
    path = os.path.abspath(path)

    if os.path.exists(os.path.join(path, ".novel")):
        return jsonify({"error": "Project already exists at this path"}), 409

    result = init_project(path, title, novel_type)
    if result["status"] == "error":
        return jsonify(result), 400

    return jsonify(result), 201


@app.route("/api/status")
def api_status():
    project_root = get_project_root()
    if not project_root:
        return jsonify({"error": "No novel project found"}), 404

    sm = StateManager(project_root)
    state = sm.read()

    with open(os.path.join(project_root, ".novel", "config.yml"), "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    wq = WorkQueue(project_root)

    return jsonify({
        "project": config["project"],
        "stages": state["stages"],
        "current_stage": state["current_stage"],
        "work_queue_pending": wq.count_pending(),
        "checkpoints": config["checkpoints"],
        "depth": config["depth"],
    })


@app.route("/api/knowledge/<category>")
def api_knowledge_list(category):
    project_root = get_project_root()
    if not project_root:
        return jsonify({"error": "No novel project found"}), 404

    kg = KnowledgeGraph(project_root)
    entries = kg.list_entries(category)
    return jsonify({"category": category, "entries": entries})


@app.route("/api/knowledge/<category>/<name>")
def api_knowledge_entry(category, name):
    project_root = get_project_root()
    if not project_root:
        return jsonify({"error": "No novel project found"}), 404

    kg = KnowledgeGraph(project_root)
    entry = kg.read(category, name)
    if not entry:
        return jsonify({"error": "Entry not found"}), 404
    return jsonify(entry)


@app.route("/api/chapters")
def api_chapters():
    project_root = get_project_root()
    if not project_root:
        return jsonify({"error": "No novel project found"}), 404

    chapters_dir = os.path.join(project_root, "novel", "chapters")
    chapters = []
    if os.path.isdir(chapters_dir):
        for f in sorted(os.listdir(chapters_dir)):
            if f.endswith(".md"):
                chapters.append(f)
    return jsonify({"chapters": chapters})


@app.route("/api/chapters/<filename>")
def api_chapter_content(filename):
    project_root = get_project_root()
    if not project_root:
        return jsonify({"error": "No novel project found"}), 404

    chapter_path = os.path.join(project_root, "novel", "chapters", filename)
    if not os.path.exists(chapter_path):
        return jsonify({"error": "Chapter not found"}), 404

    with open(chapter_path, "r", encoding="utf-8") as f:
        content = f.read()
    return jsonify({"filename": filename, "content": content})


@app.route("/api/outline")
def api_outline():
    project_root = get_project_root()
    if not project_root:
        return jsonify({"error": "No novel project found"}), 404

    outline_dir = os.path.join(project_root, "novel", "outline")
    files = {}
    chapter_outlines = []
    if os.path.isdir(outline_dir):
        for f in os.listdir(outline_dir):
            fpath = os.path.join(outline_dir, f)
            if f.endswith(".md") or f.endswith(".yml"):
                with open(fpath, "r", encoding="utf-8") as fh:
                    files[f] = fh.read()

        # Scan chapter_outlines subdirectory
        chapters_dir = os.path.join(outline_dir, "chapter_outlines")
        if os.path.isdir(chapters_dir):
            for f in sorted(os.listdir(chapters_dir)):
                if f.endswith(".md"):
                    chapter_outlines.append(f)

    return jsonify({"files": files, "chapter_outlines": chapter_outlines})


@app.route("/api/outline/chapter/<filename>")
def api_outline_chapter(filename):
    project_root = get_project_root()
    if not project_root:
        return jsonify({"error": "No novel project found"}), 404

    fpath = os.path.join(project_root, "novel", "outline", "chapter_outlines", filename)
    if not os.path.isfile(fpath):
        return jsonify({"error": "File not found"}), 404

    with open(fpath, "r", encoding="utf-8") as f:
        content = f.read()
    return jsonify({"filename": filename, "content": content})


@app.route("/api/work-queue")
def api_work_queue():
    project_root = get_project_root()
    if not project_root:
        return jsonify({"error": "No novel project found"}), 404

    wq = WorkQueue(project_root)
    return jsonify({"tasks": wq.read()["tasks"]})


@app.route("/api/reviews")
def api_reviews():
    project_root = get_project_root()
    if not project_root:
        return jsonify({"error": "No novel project found"}), 404

    review_dir = os.path.join(project_root, "novel", "review")
    files = {}
    if os.path.isdir(review_dir):
        for f in os.listdir(review_dir):
            fpath = os.path.join(review_dir, f)
            if f.endswith(".md"):
                with open(fpath, "r", encoding="utf-8") as fh:
                    files[f] = fh.read()
    return jsonify({"files": files})


@app.route("/api/chat", methods=["POST"])
def api_chat():
    """处理聊天消息，返回SSE流"""
    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"error": "message is required"}), 400

    message = data["message"].strip()
    project_root = get_project_root()

    if not project_root:
        return jsonify({"error": "No novel project found"}), 404

    # 保存用户消息到历史
    history = ChatHistory(project_root)
    history.add_message("user", message)

    # 解析命令
    proxy = CLIProxy(project_root)
    cmd_type, args = proxy.parse_command(message)

    def generate():
        """生成SSE流"""
        if cmd_type:
            # 命令模式：执行CLI（带技能注入）
            yield f"data: {json.dumps({'type': 'start', 'mode': 'command'})}\n\n"

            recent_messages = history.get_recent_messages(5)
            for chunk in proxy.execute_streaming(cmd_type, args, history=recent_messages):
                yield f"data: {json.dumps(chunk)}\n\n"

        else:
            # 自然语言模式：构建包含项目状态的上下文
            yield f"data: {json.dumps({'type': 'start', 'mode': 'chat'})}\n\n"

            recent_messages = history.get_recent_messages(5)
            context = "\n".join([f"{m['role']}: {m['content']}" for m in recent_messages])

            # 读取项目状态
            state_context = proxy._read_project_state()

            prompt = f"用户说: {message}\n\n项目状态:\n{state_context}\n\n对话历史:\n{context}"

            try:
                process = subprocess.Popen(
                    ["claude", "-p", prompt],
                    cwd=project_root,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1
                )

                full_response = ""
                for line in process.stdout:
                    full_response += line
                    yield f"data: {json.dumps({'type': 'output', 'content': line})}\n\n"

                try:
                    process.wait(timeout=300)
                except subprocess.TimeoutExpired:
                    process.kill()
                    yield f"data: {json.dumps({'type': 'error', 'content': '命令执行超时'})}\n\n"
                    yield f"data: {json.dumps({'type': 'done', 'content': ''})}\n\n"
                    return

                # 保存助手回复
                history.add_message("assistant", full_response)

                if process.returncode != 0:
                    stderr = process.stderr.read()
                    yield f"data: {json.dumps({'type': 'error', 'content': stderr})}\n\n"

            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

            # 始终发送 done 事件
            yield f"data: {json.dumps({'type': 'done', 'content': ''})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )


@app.route("/api/history", methods=["GET"])
def api_history():
    """获取对话历史"""
    project_root = get_project_root()
    if not project_root:
        return jsonify({"error": "No novel project found"}), 404

    history = ChatHistory(project_root)
    limit = request.args.get("limit", 50, type=int)

    return jsonify({
        "messages": history.get_recent_messages(limit)
    })


@app.route("/api/history", methods=["DELETE"])
def api_clear_history():
    """清空对话历史"""
    project_root = get_project_root()
    if not project_root:
        return jsonify({"error": "No novel project found"}), 404

    history = ChatHistory(project_root)
    history.clear()

    return jsonify({"success": True})


if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 8080
    print(f"Starting znovel Web Server on http://localhost:{port}")
    app.run(debug=True, port=port)
