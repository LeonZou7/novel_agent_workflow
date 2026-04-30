import pytest
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
    cmd_type, args = proxy.parse_command("/novel status")
    assert cmd_type == "novel"
    assert args == ["status"]

    # 测试非命令文本
    cmd_type, args = proxy.parse_command("这不是命令")
    assert cmd_type is None
    assert args == []


def test_build_cli_command():
    """测试构建CLI命令"""
    proxy = CLIProxy("/tmp/test_project")

    cmd = proxy.build_cli_command("znovel-outline", ["generate"])
    assert "znovel-outline" in cmd
    assert "generate" in cmd
