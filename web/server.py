#!/usr/bin/env python3
"""Novel Writer Web Server - Flask application."""

import os
import sys
import yaml
from flask import Flask, jsonify, send_from_directory, request

SCRIPT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
sys.path.insert(0, SCRIPT_DIR)

from kg import KnowledgeGraph
from state import StateManager
from work_queue import WorkQueue
from projects import ProjectRegistry

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
    if os.path.isdir(outline_dir):
        for f in os.listdir(outline_dir):
            fpath = os.path.join(outline_dir, f)
            if f.endswith(".md") or f.endswith(".yml"):
                with open(fpath, "r", encoding="utf-8") as fh:
                    files[f] = fh.read()
    return jsonify({"files": files})


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


if __name__ == "__main__":
    print("Starting Novel Writer Web Server on http://localhost:5000")
    app.run(debug=True, port=5000)
