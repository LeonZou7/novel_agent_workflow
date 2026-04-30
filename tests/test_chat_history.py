import pytest
import os
import sys
import yaml
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from web.chat_history import ChatHistory

def test_save_and_load_messages():
    """测试保存和加载对话消息"""
    with tempfile.TemporaryDirectory() as tmpdir:
        history = ChatHistory(tmpdir)

        # 保存消息
        history.add_message("user", "生成大纲")
        history.add_message("assistant", "好的，让我先了解你的小说创意...")

        # 加载消息
        messages = history.get_messages()
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "生成大纲"
        assert messages[1]["role"] == "assistant"
        assert messages[1]["content"] == "好的，让我先了解你的小说创意..."

def test_get_recent_messages():
    """测试获取最近N条消息"""
    with tempfile.TemporaryDirectory() as tmpdir:
        history = ChatHistory(tmpdir)

        # 添加多条消息
        for i in range(10):
            history.add_message("user", f"消息{i}")

        # 获取最近3条
        recent = history.get_recent_messages(3)
        assert len(recent) == 3
        assert recent[0]["content"] == "消息7"
        assert recent[2]["content"] == "消息9"

def test_clear_history():
    """测试清空历史"""
    with tempfile.TemporaryDirectory() as tmpdir:
        history = ChatHistory(tmpdir)
        history.add_message("user", "测试")
        history.clear()

        messages = history.get_messages()
        assert len(messages) == 0
