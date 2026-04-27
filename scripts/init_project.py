#!/usr/bin/env python3
"""Initialize a new novel writing project."""

import os
import yaml
import copy
from datetime import datetime

CONFIG_TEMPLATE = {
    "project": {
        "title": "",
        "type": "web_novel",
        "language": "zh-CN",
    },
    "template": {
        "methodology": "web_trope",
        "custom_template_path": None,
    },
    "depth": {
        "world": "deep",
        "character": "deep",
    },
    "review": {
        "enable_proofreading": True,
        "enable_consistency": True,
        "enable_style": False,
        "style_config": {
            "chapter_target_words": 4000,
            "climax_interval_chapters": 10,
        },
    },
    "checkpoints": {
        "outline": "always",
        "world": "key_only",
        "character": "key_only",
        "draft": "every_n_chapters(10)",
        "review": "always",
    },
    "context": {
        "level1_chapters": 3,
        "level2_summary_scope": "current_arc",
        "summary_words_per_chapter": 300,
    },
    "output": {
        "base_dir": "novel",
        "chapter_filename": "ch{num}_{title}.md",
    },
}

STATE_TEMPLATE = {
    "project": "",
    "created_at": "",
    "updated_at": "",
    "current_stage": "outline",
    "stages": {
        "outline": {"status": "pending", "version": 0},
        "world": {"status": "pending", "version": 0},
        "character": {"status": "pending", "version": 0},
        "draft": {"status": "pending", "version": 0, "last_chapter": 0},
        "review": {"status": "pending", "version": 0},
    },
    "work_queue": [],
}

KG_DIRS = ["characters", "world", "plot", "chapters"]

OUTPUT_DIRS = ["outline", "world", "characters", "chapters", "review"]

NOVEL_DIR = ".novel"


def init_project(project_path: str, title: str, novel_type: str = "web_novel") -> dict:
    """Initialize a novel project directory with all required files."""
    novel_root = os.path.join(project_path, NOVEL_DIR)

    if os.path.exists(novel_root):
        return {"status": "error", "message": f"Project already exists at {novel_root}"}

    knowledge_root = os.path.join(novel_root, "knowledge")
    output_root = os.path.join(project_path, CONFIG_TEMPLATE["output"]["base_dir"])

    os.makedirs(novel_root, exist_ok=True)
    os.makedirs(knowledge_root, exist_ok=True)
    os.makedirs(output_root, exist_ok=True)

    for d in KG_DIRS:
        os.makedirs(os.path.join(knowledge_root, d), exist_ok=True)

    for d in OUTPUT_DIRS:
        os.makedirs(os.path.join(output_root, d), exist_ok=True)

    config = copy.deepcopy(CONFIG_TEMPLATE)
    config["project"]["title"] = title
    config["project"]["type"] = novel_type

    state = copy.deepcopy(STATE_TEMPLATE)
    state["project"] = title
    state["created_at"] = datetime.now().isoformat()
    state["updated_at"] = state["created_at"]

    with open(os.path.join(novel_root, "config.yml"), "w") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)

    with open(os.path.join(novel_root, "state.yml"), "w") as f:
        yaml.dump(state, f, allow_unicode=True, default_flow_style=False)

    with open(os.path.join(novel_root, "work_queue.yml"), "w") as f:
        yaml.dump({"tasks": []}, f, allow_unicode=True, default_flow_style=False)

    with open(os.path.join(knowledge_root, "foreshadowing.yml"), "w") as f:
        yaml.dump({"planted": [], "progressed": [], "resolved": []}, f, allow_unicode=True, default_flow_style=False)

    with open(os.path.join(knowledge_root, "timeline.yml"), "w") as f:
        yaml.dump({"events": []}, f, allow_unicode=True, default_flow_style=False)

    return {"status": "ok", "path": project_path, "title": title}


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python init_project.py <project_path> <title> [type]")
        sys.exit(1)

    path = sys.argv[1]
    title = sys.argv[2]
    ntype = sys.argv[3] if len(sys.argv) > 3 else "web_novel"

    result = init_project(path, title, ntype)
    if result["status"] == "error":
        print(f"Error: {result['message']}")
        sys.exit(1)
    print(f"Project '{result['title']}' initialized at {result['path']}")
