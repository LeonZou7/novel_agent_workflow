#!/usr/bin/env python3
"""Project state management."""

import os
import yaml
from datetime import datetime
from typing import Optional


class StateManager:
    """Manage .novel/state.yml for workflow tracking."""

    def __init__(self, project_root: str):
        self.state_path = os.path.join(project_root, ".novel", "state.yml")
        if not os.path.exists(self.state_path):
            raise FileNotFoundError(f"State file not found at {self.state_path}")

    def read(self) -> dict:
        with open(self.state_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def write(self, state: dict):
        state["updated_at"] = datetime.now().isoformat()
        with open(self.state_path, "w", encoding="utf-8") as f:
            yaml.dump(state, f, allow_unicode=True, default_flow_style=False)

    def get_stage(self, stage: str) -> Optional[dict]:
        s = self.read()
        return s.get("stages", {}).get(stage)

    def set_stage_status(self, stage: str, status: str):
        s = self.read()
        if stage not in s["stages"]:
            raise ValueError(f"Unknown stage: {stage}")
        s["stages"][stage]["status"] = status
        if status == "completed":
            s["stages"][stage]["version"] += 1
        s["current_stage"] = stage
        self.write(s)

    def get_current_stage(self) -> str:
        return self.read().get("current_stage", "outline")

    def get_next_pending_stage(self) -> Optional[str]:
        stage_order = ["outline", "world", "character", "draft", "review"]
        s = self.read()
        for stage in stage_order:
            if s["stages"][stage]["status"] != "completed":
                return stage
        return None

    def advance_draft_chapter(self, chapter_num: int):
        s = self.read()
        s["stages"]["draft"]["last_chapter"] = chapter_num
        self.write(s)
