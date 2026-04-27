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


if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(description="Work Queue Manager")
    sub = parser.add_subparsers(dest="cmd")

    add_p = sub.add_parser("add")
    add_p.add_argument("--type", required=True)
    add_p.add_argument("--source", required=True)
    add_p.add_argument("--target", required=True)
    add_p.add_argument("--desc", required=True)
    add_p.add_argument("--action", required=True)

    sub.add_parser("list")
    sub.add_parser("pending")

    resolve_p = sub.add_parser("resolve")
    resolve_p.add_argument("id")

    args = parser.parse_args()

    if args.cmd is None:
        parser.print_help()
        sys.exit(1)

    cwd = os.getcwd()
    while cwd != "/":
        if os.path.isdir(os.path.join(cwd, ".novel")):
            break
        cwd = os.path.dirname(cwd)

    if cwd == "/":
        print("Error: Not in a novel project. Run init first.")
        sys.exit(1)

    wq = WorkQueue(cwd)

    if args.cmd == "add":
        tid = wq.add(args.type, args.source, args.target, args.desc, args.action)
        print(f"Task {tid} added to work queue")
    elif args.cmd == "list":
        tasks = wq.read()["tasks"]
        if not tasks:
            print("No tasks in work queue")
        else:
            for t in tasks:
                status_icon = "✅" if t["status"] == "resolved" else "⏳"
                print(f"  [{t['id']}] {status_icon} {t['description']} → {t['target_agent']}")
    elif args.cmd == "pending":
        tasks = wq.list_pending()
        if not tasks:
            print("No pending tasks")
        else:
            for t in tasks:
                print(f"  [{t['id']}] {t['description']} → {t['target_agent']}")
    elif args.cmd == "resolve":
        wq.resolve(args.id)
        print(f"Task {args.id} resolved")
