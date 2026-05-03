#!/usr/bin/env python3
"""Initialize a new novel writing project."""

import os
import yaml
import copy
import shutil
from datetime import datetime
from projects import ProjectRegistry

CONFIG_TEMPLATE = {
    "project": {
        "title": "",
        "type": None,
        "language": None,
    },
    "template": {
        "methodology": None,
        "custom_template_path": None,
    },
    "depth": {
        "world": "standard",
        "character": "standard",
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
    "style": {
        "preset": "concise_white",
        "reference_text": None,
        "custom_description": None,
    },
    "constraints": {
        "enabled": True,
        "rules": [
            "不得出现真实国家名称（如中国、美国、日本等），须使用虚构国名",
            "不得出现真实地名（如北京、东京、纽约等），须虚构地名替代",
            "不得出现真实宗教名称（如佛教、基督教、伊斯兰教等），须虚构信仰体系",
            "不得映射真实政治事件、政治人物、政党或政治运动",
            "不得出现真实历史人物姓名，可虚构化改编",
        ],
        "custom_rules": [],
    },
}

STATE_TEMPLATE = {
    "project": "",
    "created_at": "",
    "updated_at": "",
    "current_stage": "concept",
    "stages": {
        "concept": {"status": "pending", "version": 0},
        "outline": {"status": "pending", "version": 0},
        "world": {"status": "pending", "version": 0},
        "character": {"status": "pending", "version": 0},
        "draft": {"status": "pending", "version": 0, "last_chapter": 0},
        "review": {"status": "pending", "version": 0},
    },
    "work_queue": [],
}

KG_DIRS = ["characters", "world", "plot", "chapters"]

OUTPUT_DIRS = ["outline", "world", "characters", "chapters", "review", "archive"]

NOVEL_DIR = ".novel"

# Resolve the package root (parent of scripts/), used to locate bundled skills and templates
PACKAGE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def init_project(project_path: str, title: str) -> dict:
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

    # Create brainstorm directory for Q&A state persistence
    brainstorm_root = os.path.join(novel_root, "brainstorm")
    os.makedirs(brainstorm_root, exist_ok=True)

    config = copy.deepcopy(CONFIG_TEMPLATE)
    config["project"]["title"] = title

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

    # Copy bundled skills into the project so /znovel-* commands work out of the box
    skills_src = os.path.join(PACKAGE_DIR, ".claude", "skills")
    skills_dst = os.path.join(project_path, ".claude", "skills")
    if os.path.isdir(skills_src):
        for entry in os.listdir(skills_src):
            if entry.startswith("znovel-") and os.path.isdir(os.path.join(skills_src, entry)):
                shutil.copytree(os.path.join(skills_src, entry), os.path.join(skills_dst, entry))

    # Register in global project list (type is None until brainstorm determines it)
    registry = ProjectRegistry()
    registry.register(project_path, title, None)

    return {"status": "ok", "path": project_path, "title": title}


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python init_project.py <project_path> <title>")
        sys.exit(1)

    path = sys.argv[1]
    title = sys.argv[2]

    result = init_project(path, title)
    if result["status"] == "error":
        print(f"Error: {result['message']}")
        sys.exit(1)
    print(f"Project '{result['title']}' initialized at {result['path']}")
