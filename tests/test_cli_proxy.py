import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock
from web.cli_proxy import CLIProxy


def test_parse_command():
    """测试解析命令"""
    proxy = CLIProxy("/tmp/test_project")

    # 测试znovel命令
    cmd_type, args = proxy.parse_command("/znovel-outline generate")
    assert cmd_type == "znovel-outline"
    assert args == ["generate"]

    # 测试novel命令
    cmd_type, args = proxy.parse_command("/znovel status")
    assert cmd_type == "znovel"
    assert args == ["status"]

    # 测试非命令文本
    cmd_type, args = proxy.parse_command("这不是命令")
    assert cmd_type is None
    assert args == []


def test_build_cli_command():
    """测试构建CLI命令"""
    proxy = CLIProxy("/tmp/test_project")

    # 测试有参数的命令
    cmd = proxy.build_cli_command("znovel-outline", ["generate"])
    assert cmd == "znovel-outline generate"

    # 测试 novel -> znovel-director 映射
    cmd = proxy.build_cli_command("znovel", ["status"])
    assert cmd == "znovel-director status"

    # 测试空参数
    cmd = proxy.build_cli_command("znovel-outline", [])
    assert cmd == "znovel-outline"


def test_build_prompt_includes_skill():
    """测试 build_prompt 包含技能内容"""
    # 创建临时项目目录
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建技能目录和文件
        skill_dir = os.path.join(tmpdir, ".claude", "skills", "znovel-outline")
        os.makedirs(skill_dir)
        with open(os.path.join(skill_dir, "SKILL.md"), "w") as f:
            f.write("# 测试技能\n这是测试内容")

        proxy = CLIProxy(tmpdir)
        prompt = proxy.build_prompt("znovel-outline", ["generate"])

        assert "测试技能" in prompt
        assert "znovel-outline generate" in prompt


def test_build_prompt_without_skill_file():
    """测试技能文件不存在时的回退"""
    proxy = CLIProxy("/tmp/nonexistent")
    prompt = proxy.build_prompt("znovel-outline", ["generate"])

    assert "znovel-outline generate" in prompt


def test_build_prompt_includes_history():
    """测试 build_prompt 包含对话历史"""
    proxy = CLIProxy("/tmp")
    history = [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "你好！"},
    ]
    prompt = proxy.build_prompt("znovel", ["status"], history=history)

    assert "你好" in prompt
    assert "对话历史" in prompt


def test_read_skill_file():
    """测试 _read_skill_file 读取技能文件"""
    with tempfile.TemporaryDirectory() as tmpdir:
        skill_dir = os.path.join(tmpdir, ".claude", "skills", "test-skill")
        os.makedirs(skill_dir)
        with open(os.path.join(skill_dir, "SKILL.md"), "w") as f:
            f.write("# Test Skill Content")

        proxy = CLIProxy(tmpdir)
        content = proxy._read_skill_file("test-skill")
        assert content == "# Test Skill Content"


def test_read_skill_file_not_found():
    """测试 _read_skill_file 文件不存在时返回空字符串"""
    proxy = CLIProxy("/tmp/nonexistent")
    content = proxy._read_skill_file("nonexistent-skill")
    assert content == ""


def test_read_project_state():
    """测试 _read_project_state 读取项目状态"""
    with tempfile.TemporaryDirectory() as tmpdir:
        novel_dir = os.path.join(tmpdir, ".novel")
        os.makedirs(novel_dir)
        with open(os.path.join(novel_dir, "config.yml"), "w") as f:
            f.write("title: 测试小说")
        with open(os.path.join(novel_dir, "state.yml"), "w") as f:
            f.write("current_chapter: 1")

        proxy = CLIProxy(tmpdir)
        state = proxy._read_project_state()

        assert "测试小说" in state
        assert "current_chapter" in state


def test_read_project_state_empty():
    """测试 _read_project_state 无状态文件时返回空字符串"""
    proxy = CLIProxy("/tmp/nonexistent")
    state = proxy._read_project_state()
    assert state == ""
