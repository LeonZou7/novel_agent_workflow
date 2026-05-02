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
        init_project(cls.tmpdir, "E2E测试小说")

    def test_01_directory_structure(self):
        """Verify all directories were created."""
        dirs = [
            ".novel",
            ".novel/knowledge",
            ".novel/knowledge/characters",
            ".novel/knowledge/world",
            ".novel/knowledge/plot",
            ".novel/knowledge/chapters",
            ".novel/brainstorm",
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

    def test_01b_brainstorm_directory(self):
        """Verify brainstorm/ directory is empty and ready for use."""
        import yaml

        brainstorm_dir = os.path.join(self.tmpdir, ".novel", "brainstorm")
        self.assertTrue(os.path.isdir(brainstorm_dir))

        # Verify no stale brainstorm files exist
        outline_path = os.path.join(brainstorm_dir, "outline.yml")
        world_path = os.path.join(brainstorm_dir, "world.yml")
        character_path = os.path.join(brainstorm_dir, "character.yml")
        self.assertFalse(os.path.exists(outline_path))
        self.assertFalse(os.path.exists(world_path))
        self.assertFalse(os.path.exists(character_path))

    def test_01c_brainstorm_outline_yml(self):
        """Test the brainstorm outline.yml lifecycle: pending to confirmed (new format)."""
        import yaml

        outline_path = os.path.join(self.tmpdir, ".novel", "brainstorm", "outline.yml")

        # Simulate director starting brainstorm with concept selection
        brainstorm = {
            "status": "pending",
            "config": {
                "type": "web_novel",
                "methodology": "web_xianxia",
                "language": "zh-CN",
            },
            "selected_concept": None,
            "modifications": [],
            "all_concepts": [
                {"title": "概念A", "theme": "复仇", "conflict": "卧底", "ending": "HE", "elements": ["宗门大比"], "pitch": "..."},
                {"title": "概念B", "theme": "成长", "conflict": "身世之谜", "ending": "开放", "elements": ["上古遗迹"], "pitch": "..."},
            ],
        }
        with open(outline_path, "w", encoding="utf-8") as f:
            yaml.dump(brainstorm, f, allow_unicode=True, default_flow_style=False)

        # Verify pending state
        with open(outline_path, "r", encoding="utf-8") as f:
            saved = yaml.safe_load(f)
        self.assertEqual(saved["status"], "pending")
        self.assertEqual(saved["config"]["type"], "web_novel")
        self.assertEqual(len(saved["all_concepts"]), 2)

        # Simulate user selecting a concept and confirming
        saved["status"] = "confirmed"
        saved["selected_concept"] = {
            "title": "概念A",
            "theme": "复仇",
            "conflict": "卧底仇人门下",
            "ending": "HE",
            "elements": ["宗门大比", "隐世传承"],
            "pitch": "一个被灭门的少年...",
        }
        saved["modifications"] = [
            {"field": "conflict", "original": "卧底", "modified": "卧底仇人门下"},
        ]
        with open(outline_path, "w", encoding="utf-8") as f:
            yaml.dump(saved, f, allow_unicode=True, default_flow_style=False)

        # Verify confirmed state
        with open(outline_path, "r", encoding="utf-8") as f:
            confirmed = yaml.safe_load(f)
        self.assertEqual(confirmed["status"], "confirmed")
        self.assertIsNotNone(confirmed["selected_concept"])
        self.assertEqual(confirmed["selected_concept"]["ending"], "HE")
        self.assertEqual(len(confirmed["modifications"]), 1)

    def test_02_config_file(self):
        """Verify config.yml has all required keys."""
        import yaml
        with open(os.path.join(self.tmpdir, ".novel", "config.yml"), "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        self.assertEqual(config["project"]["title"], "E2E测试小说")
        self.assertIsNone(config["project"]["type"])
        self.assertIsNone(config["project"]["language"])
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
        self.assertEqual(sm.get_current_stage(), "concept")

        sm.set_stage_status("concept", "completed")
        self.assertEqual(sm.get_next_pending_stage(), "outline")

        sm.set_stage_status("outline", "completed")
        self.assertEqual(sm.get_next_pending_stage(), "world")

        sm.set_stage_status("world", "completed")
        sm.set_stage_status("character", "completed")

        sm.advance_draft_chapter(42)
        state = sm.read()
        self.assertEqual(state["stages"]["draft"]["last_chapter"], 42)

    def test_05b_concept_stage(self):
        """Test that concept stage exists and is the initial current_stage."""
        import shutil
        tmpdir = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(tmpdir))
        init_project(tmpdir, "概念阶段测试")

        sm = StateManager(tmpdir)
        self.assertEqual(sm.get_current_stage(), "concept")

        # concept should be first in stage order
        self.assertEqual(sm.get_next_pending_stage(), "concept")

        sm.set_stage_status("concept", "completed")
        self.assertEqual(sm.get_next_pending_stage(), "outline")

    def test_05c_concept_yml_lifecycle(self):
        """Test concept.yml brainstorm lifecycle: pending → confirmed."""
        import yaml

        concept_path = os.path.join(self.tmpdir, ".novel", "brainstorm", "concept.yml")

        # Simulate director writing pending concept
        concept = {
            "status": "pending",
            "config": {
                "type": "web_novel",
                "methodology": "web_xianxia",
                "language": "zh-CN",
            },
            "concept": {
                "theme": "复仇与成长",
                "tone": "热血爽文，节奏明快",
                "conflict": "废材逆袭",
                "ending": "HE",
                "elements": ["金手指", "升级打怪"],
                "pitch": "一个被灭门的少年...",
            },
            "modifications": [],
        }
        with open(concept_path, "w", encoding="utf-8") as f:
            yaml.dump(concept, f, allow_unicode=True, default_flow_style=False)

        # Verify pending state
        with open(concept_path, "r", encoding="utf-8") as f:
            saved = yaml.safe_load(f)
        self.assertEqual(saved["status"], "pending")
        self.assertEqual(saved["concept"]["theme"], "复仇与成长")
        self.assertEqual(saved["config"]["type"], "web_novel")

        # Simulate user confirming
        saved["status"] = "confirmed"
        saved["modifications"] = [
            {"field": "conflict", "original": "废材逆袭", "modified": "废材逆袭，打脸装逼"},
        ]
        with open(concept_path, "w", encoding="utf-8") as f:
            yaml.dump(saved, f, allow_unicode=True, default_flow_style=False)

        # Verify confirmed state
        with open(concept_path, "r", encoding="utf-8") as f:
            confirmed = yaml.safe_load(f)
        self.assertEqual(confirmed["status"], "confirmed")
        self.assertEqual(confirmed["concept"]["ending"], "HE")
        self.assertEqual(len(confirmed["modifications"]), 1)

    def test_05d_alignment_report(self):
        """Test alignment report generation and work queue integration."""
        import yaml

        # Simulate alignment check finding conflicts
        wq = WorkQueue(self.tmpdir)
        tid = wq.add(
            "alignment_conflict",
            "alignment_check",
            "outline",
            "大纲提到「天剑宗」但世界观中无此势力",
            "在世界观factions.md中补充天剑宗设定"
        )
        self.assertTrue(tid.startswith("WQ-"))

        pending = wq.list_pending()
        self.assertTrue(any(t["source"] == "alignment_check" for t in pending))

        # Write alignment report
        report_path = os.path.join(self.tmpdir, ".novel", "alignment_report.yml")
        report = {
            "checked_at": "2026-05-02T12:00:00",
            "conflicts": [
                {
                    "id": "AL-001",
                    "type": "missing_entity",
                    "description": "大纲提到「天剑宗」但世界观中无此势力",
                    "source_agent": "outline",
                    "target_agent": "world",
                    "work_queue_id": tid,
                }
            ],
            "status": "pending_review",
        }
        with open(report_path, "w", encoding="utf-8") as f:
            yaml.dump(report, f, allow_unicode=True, default_flow_style=False)

        with open(report_path, "r", encoding="utf-8") as f:
            saved = yaml.safe_load(f)
        self.assertEqual(saved["status"], "pending_review")
        self.assertEqual(len(saved["conflicts"]), 1)
        self.assertEqual(saved["conflicts"][0]["work_queue_id"], tid)

        # Resolve the work queue item to clean up for subsequent tests
        wq.resolve(tid)
        self.assertEqual(wq.count_pending(), 0)

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
        init_project(d2, "第二本小说")

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
