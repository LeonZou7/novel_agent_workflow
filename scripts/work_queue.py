#!/usr/bin/env python3
"""Work queue management for review callbacks."""

import os
import yaml
from datetime import datetime


class WorkQueue:
    """Manage .novel/work_queue.yml for review-flagged issues."""

    def __init__(self, project_root: str):
        self.queue_path = os.path.join(project_root, ".novel", "work_queue.yml")
        if not os.path.exists(self.queue_path):
            raise FileNotFoundError(f"Work queue not found at {self.queue_path}")

    def read(self) -> dict:
        with open(self.queue_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {"tasks": []}

    def write(self, data: dict):
        with open(self.queue_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

    def add(self, task_type: str, source: str, target_agent: str,
            description: str, suggested_action: str) -> str:
        data = self.read()
        task_id = f"WQ-{len(data['tasks']) + 1:03d}"
        task = {
            "id": task_id,
            "type": task_type,
            "source": source,
            "target_agent": target_agent,
            "description": description,
            "suggested_action": suggested_action,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
        }
        data["tasks"].append(task)
        self.write(data)
        return task_id

    def list_pending(self) -> list:
        data = self.read()
        return [t for t in data["tasks"] if t["status"] == "pending"]

    def resolve(self, task_id: str):
        data = self.read()
        for t in data["tasks"]:
            if t["id"] == task_id:
                t["status"] = "resolved"
                t["resolved_at"] = datetime.now().isoformat()
                break
        self.write(data)

    def count_pending(self) -> int:
        return len(self.list_pending())
