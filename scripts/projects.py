#!/usr/bin/env python3
"""Global project registry - tracks all novel projects on this machine."""

import os
import yaml
from datetime import datetime
from typing import Optional


class ProjectRegistry:
    """Manage ~/.novel/projects.yml - the global list of all novel projects."""

    HOME_DIR = os.path.expanduser("~/.novel")
    REGISTRY_PATH = os.path.join(HOME_DIR, "projects.yml")

    def __init__(self):
        os.makedirs(self.HOME_DIR, exist_ok=True)
        if not os.path.exists(self.REGISTRY_PATH):
            self._write({"projects": []})

    def _read(self) -> dict:
        with open(self.REGISTRY_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {"projects": []}

    def _write(self, data: dict):
        with open(self.REGISTRY_PATH, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

    def list_projects(self) -> list:
        """Return all registered projects with their paths and metadata."""
        return self._read().get("projects", [])

    def register(self, path: str, title: str, novel_type: str = None):
        """Add a project to the registry. Does nothing if already registered."""
        path = os.path.abspath(path)
        data = self._read()
        projects = data.get("projects", [])

        # Check if already registered
        for p in projects:
            if p.get("path") == path:
                p["title"] = title  # update title if changed
                p["updated_at"] = datetime.now().isoformat()
                self._write(data)
                return

        projects.append({
            "title": title,
            "path": path,
            "type": novel_type,
            "created_at": datetime.now().isoformat(),
            "last_opened": None,
        })
        data["projects"] = projects
        self._write(data)

    def unregister(self, path: str):
        """Remove a project from the registry."""
        path = os.path.abspath(path)
        data = self._read()
        data["projects"] = [p for p in data.get("projects", []) if p.get("path") != path]
        self._write(data)

    def touch(self, path: str):
        """Update last_opened timestamp for a project."""
        path = os.path.abspath(path)
        data = self._read()
        for p in data.get("projects", []):
            if p.get("path") == path:
                p["last_opened"] = datetime.now().isoformat()
                self._write(data)
                return

    def find_by_path(self, path: str) -> Optional[dict]:
        """Find a registered project by its path."""
        path = os.path.abspath(path)
        for p in self.list_projects():
            if p.get("path") == path:
                return p
        return None

    def get_state(self, path: str) -> Optional[dict]:
        """Get project state from its .novel/state.yml."""
        state_path = os.path.join(path, ".novel", "state.yml")
        if not os.path.exists(state_path):
            return None
        with open(state_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
