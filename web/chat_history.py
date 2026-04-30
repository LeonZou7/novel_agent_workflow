"""对话历史存储模块"""

import os
import yaml
from datetime import datetime


class ChatHistory:
    """管理对话历史的存储和读取"""

    def __init__(self, project_root):
        self.history_file = os.path.join(project_root, ".novel", "chat_history.yml")
        self._ensure_file()

    def _ensure_file(self):
        """确保历史文件存在"""
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
        if not os.path.exists(self.history_file):
            self._save({"messages": []})

    def _load(self):
        """加载历史数据"""
        with open(self.history_file, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {"messages": []}

    def _save(self, data):
        """保存历史数据"""
        with open(self.history_file, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

    def add_message(self, role, content):
        """添加一条消息"""
        data = self._load()
        data["messages"].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        self._save(data)

    def get_messages(self):
        """获取所有消息"""
        data = self._load()
        return data["messages"]

    def get_recent_messages(self, n=10):
        """获取最近n条消息"""
        messages = self.get_messages()
        return messages[-n:] if len(messages) > n else messages

    def clear(self):
        """清空历史"""
        self._save({"messages": []})
