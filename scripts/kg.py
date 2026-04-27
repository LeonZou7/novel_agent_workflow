#!/usr/bin/env python3
"""Knowledge Graph read/write utilities."""

import os
import yaml
from datetime import datetime
from typing import Optional


class KnowledgeGraph:
    """Read and write entries in the novel knowledge graph."""

    def __init__(self, project_root: str):
        self.kg_root = os.path.join(project_root, ".novel", "knowledge")
        if not os.path.isdir(self.kg_root):
            raise FileNotFoundError(f"KG not found at {self.kg_root}. Run init first.")

    def _path(self, category: str, name: str) -> str:
        safe = name.replace("/", "_").replace(" ", "_")
        return os.path.join(self.kg_root, category, f"{safe}.yml")

    def read(self, category: str, name: str) -> Optional[dict]:
        p = self._path(category, name)
        if not os.path.exists(p):
            return None
        with open(p, "r") as f:
            return yaml.safe_load(f)

    def write(self, category: str, name: str, data: dict) -> str:
        p = self._path(category, name)
        data.setdefault("name", name)
        data.setdefault("category", category)
        data.setdefault("version", 1)
        data.setdefault("updated_at", datetime.now().isoformat())
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
        return p

    def list_entries(self, category: str) -> list:
        d = os.path.join(self.kg_root, category)
        if not os.path.isdir(d):
            return []
        return [f.replace(".yml", "") for f in os.listdir(d) if f.endswith(".yml")]

    def delete(self, category: str, name: str) -> bool:
        p = self._path(category, name)
        if os.path.exists(p):
            os.remove(p)
            return True
        return False

    def read_foreshadowing(self) -> dict:
        p = os.path.join(self.kg_root, "foreshadowing.yml")
        with open(p, "r") as f:
            return yaml.safe_load(f) or {"planted": [], "progressed": [], "resolved": []}

    def write_foreshadowing(self, data: dict):
        p = os.path.join(self.kg_root, "foreshadowing.yml")
        with open(p, "w") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

    def read_timeline(self) -> dict:
        p = os.path.join(self.kg_root, "timeline.yml")
        with open(p, "r") as f:
            return yaml.safe_load(f) or {"events": []}

    def write_timeline(self, data: dict):
        p = os.path.join(self.kg_root, "timeline.yml")
        with open(p, "w") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

    def find_references(self, category: str, name: str) -> list:
        """Find all KG entries that reference a given entry."""
        refs = []
        search_key = name.lower()
        for cat in ["characters", "world", "plot", "chapters"]:
            cat_dir = os.path.join(self.kg_root, cat)
            if not os.path.isdir(cat_dir):
                continue
            for fname in os.listdir(cat_dir):
                if not fname.endswith(".yml"):
                    continue
                fpath = os.path.join(cat_dir, fname)
                with open(fpath, "r") as f:
                    content = f.read().lower()
                if search_key in content:
                    entry_name = fname.replace(".yml", "")
                    if not (cat == category and entry_name == name):
                        refs.append({"category": cat, "name": entry_name})
        return refs
