#!/usr/bin/env python3
"""End-to-end test: init a project, run KG operations, verify file outputs."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

from init_project import init_project
from kg import KnowledgeGraph
from state import StateManager
from work_queue import WorkQueue
from projects import ProjectRegistry


class TestE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp()
        init_project(cls.tmpdir, "E2E测试小说", "web_novel")

    def test_01_directory_structure(self):
        """Verify all directories were created."""
        dirs = [
            ".novel",
            ".novel/knowledge",
            ".novel/knowledge/characters",
            ".novel/knowledge/world",
            ".novel/knowledge/plot",
            ".novel/knowledge/chapters",
            "novel",
            "novel/outline",
            "novel/world",
            "novel/characters",
            "novel/chapters",
            "novel/review",
        ]
        for d in dirs:
            path = os.path.join(self.tmpdir, d)
            self.assertTrue(os.path.isdir(path), f"Missing: {d}")

    def test_02_config_file(self):
        """Verify config.yml has all required keys."""
        import yaml
        with open(os.path.join(self.tmpdir, ".novel", "config.yml"), "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        self.assertEqual(config["project"]["title"], "E2E测试小说")
        self.assertEqual(config["project"]["type"], "web_novel")
        self.assertIn("checkpoints", config)

    def test_03_kg_write_read(self):
        """Test writing and reading KG entries."""
        kg = KnowledgeGraph(self.tmpdir)

        kg.write("characters", "主角", {"level": "筑基期", "faction": "天剑宗"})
        entry = kg.read("characters", "主角")
        self.assertEqual(entry["level"], "筑基期")

        kg.write("world", "力量体系", {"type": "修仙", "realms": ["炼气", "筑基", "金丹"]})
        entry = kg.read("world", "力量体系")
        self.assertEqual(entry["type"], "修仙")

    def test_04_kg_references(self):
        """Test cross-reference detection."""
        kg = KnowledgeGraph(self.tmpdir)
        kg.write("chapters", "ch001_summary", {"summary": "主角进入天剑宗修炼"})
        refs = kg.find_references("characters", "主角")
        self.assertTrue(len(refs) > 0, "Should find chapter referencing 主角")

    def test_05_state_management(self):
        """Test workflow state transitions."""
        sm = StateManager(self.tmpdir)
        self.assertEqual(sm.get_current_stage(), "outline")

        sm.set_stage_status("outline", "completed")
        self.assertEqual(sm.get_next_pending_stage(), "world")

        sm.set_stage_status("world", "completed")
        sm.set_stage_status("character", "completed")

        sm.advance_draft_chapter(42)
        state = sm.read()
        self.assertEqual(state["stages"]["draft"]["last_chapter"], 42)

    def test_06_work_queue(self):
        """Test work queue operations."""
        wq = WorkQueue(self.tmpdir)

        tid1 = wq.add("inconsistency", "review_ch1", "character",
                       "主角等级与第5章矛盾", "确认后更新KG")
        tid2 = wq.add("foreshadowing_gap", "review_ch2", "outline",
                       "伏笔V3未推进", "在大纲中安排回收章节")

        pending = wq.list_pending()
        self.assertEqual(len(pending), 2)

        wq.resolve(tid1)
        self.assertEqual(wq.count_pending(), 1)

        wq.resolve(tid2)
        self.assertEqual(wq.count_pending(), 0)

    def test_07_kg_timeline_and_foreshadowing(self):
        """Test timeline and foreshadowing files."""
        kg = KnowledgeGraph(self.tmpdir)
        timeline = kg.read_timeline()
        self.assertIn("events", timeline)

        foreshadowing = kg.read_foreshadowing()
        self.assertIn("planted", foreshadowing)
        self.assertIn("resolved", foreshadowing)

        foreshadowing["planted"].append({
            "id": "V1",
            "description": "上古龙族线索",
            "chapter_planted": 10,
        })
        kg.write_foreshadowing(foreshadowing)
        updated = kg.read_foreshadowing()
        self.assertEqual(len(updated["planted"]), 1)

    def test_08_project_registry(self):
        """Test global project registry operations."""
        registry = ProjectRegistry()

        # init_project already registered self.tmpdir
        projects = registry.list_projects()
        self.assertTrue(any(p["path"] == os.path.abspath(self.tmpdir) for p in projects),
                        "Project should be registered after init")

        # Test touch
        registry.touch(self.tmpdir)
        p = registry.find_by_path(self.tmpdir)
        self.assertIsNotNone(p)
        self.assertIsNotNone(p["last_opened"])

        # Test state retrieval
        state = registry.get_state(self.tmpdir)
        self.assertIsNotNone(state)
        self.assertIn("stages", state)

    def test_09_multi_project(self):
        """Test registering multiple projects."""
        registry = ProjectRegistry()
        old_count = len(registry.list_projects())

        # Create a second temp project
        d2 = tempfile.mkdtemp()
        self.addCleanup(lambda: self._cleanup_project(d2))
        init_project(d2, "第二本小说", "short_story")

        projects = registry.list_projects()
        self.assertEqual(len(projects), old_count + 1)

        # Clean up registry
        registry.unregister(d2)
        projects_after = registry.list_projects()
        self.assertEqual(len(projects_after), old_count)

    def _cleanup_project(self, path):
        import shutil
        registry = ProjectRegistry()
        registry.unregister(path)
        if os.path.isdir(path):
            shutil.rmtree(path)

    @classmethod
    def tearDownClass(cls):
        import shutil
        registry = ProjectRegistry()
        registry.unregister(cls.tmpdir)
        shutil.rmtree(cls.tmpdir)


if __name__ == "__main__":
    unittest.main()
