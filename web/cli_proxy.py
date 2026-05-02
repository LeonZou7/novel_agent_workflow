"""
CLI代理模块 - 安全地代理本地Claude CLI调用

此模块提供：
- 命令解析和验证
- 安全的命令执行（带超时和错误处理）
- 流式输出支持
- 完整的测试覆盖
"""

import os
import re
import subprocess
import shlex
from typing import Optional, Tuple, List, Dict, Any


# 命令到技能目录的映射
SKILL_MAP = {
    "znovel-outline": "znovel-outline",
    "znovel-world": "znovel-world",
    "znovel-character": "znovel-character",
    "znovel-draft": "znovel-draft",
    "znovel-review": "znovel-review",
    "znovel-kg": "znovel-kg",
    "znovel": "znovel-director",
}


class CLIProxy:
    """代理执行CLI命令"""

    def __init__(self, project_root: str):
        """
        初始化CLI代理

        Args:
            project_root: 项目根目录
        """
        self.project_root = project_root

    def parse_command(self, text: str) -> Tuple[Optional[str], List[str]]:
        """
        解析用户输入，提取命令类型和参数

        Args:
            text: 用户输入文本

        Returns:
            tuple: (命令类型, 参数列表)
                   命令类型为None表示非命令文本
        """
        text = text.strip()

        # 匹配 /command 格式
        match = re.match(r'^(/[\w-]+)\s*(.*)', text, re.DOTALL)
        if match:
            cmd = match.group(1)
            args_str = match.group(2).strip()
            args = shlex.split(args_str) if args_str else []
            return cmd.lstrip('/'), args

        return None, []

    def build_cli_command(self, cmd_type: str, args: List[str]) -> str:
        """
        构建CLI命令

        Args:
            cmd_type: 命令类型
            args: 参数列表

        Returns:
            str: 构建的命令字符串
        """
        # 映射命令到实际的skill
        skill_map = {
            "znovel-outline": "znovel-outline",
            "znovel-world": "znovel-world",
            "znovel-character": "znovel-character",
            "znovel-draft": "znovel-draft",
            "znovel-review": "znovel-review",
            "znovel-kg": "znovel-kg",
            "znovel": "znovel-director"
        }

        skill = skill_map.get(cmd_type, cmd_type)
        cmd_args = " ".join(args) if args else ""

        return f"{skill} {cmd_args}".strip()

    def _read_skill_file(self, skill_name: str) -> str:
        """读取技能文件内容"""
        skill_dir = os.path.join(self.project_root, ".claude", "skills", skill_name)
        skill_file = os.path.join(skill_dir, "SKILL.md")
        if os.path.exists(skill_file):
            with open(skill_file, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def _read_project_state(self) -> str:
        """读取项目状态摘要"""
        parts = []
        state_file = os.path.join(self.project_root, ".novel", "state.yml")
        config_file = os.path.join(self.project_root, ".novel", "config.yml")

        if os.path.exists(config_file):
            with open(config_file, "r", encoding="utf-8") as f:
                parts.append(f"项目配置:\n{f.read()}")

        if os.path.exists(state_file):
            with open(state_file, "r", encoding="utf-8") as f:
                parts.append(f"运行状态:\n{f.read()}")

        return "\n---\n".join(parts)

    def build_prompt(self, cmd_type: str, args: List[str], history: list = None) -> str:
        """
        构建包含技能定义和项目状态的完整 prompt

        Args:
            cmd_type: 命令类型
            args: 参数列表
            history: 对话历史列表

        Returns:
            str: 完整的 prompt
        """
        skill_name = SKILL_MAP.get(cmd_type, cmd_type)
        skill_content = self._read_skill_file(skill_name)

        # 构建命令字符串
        cmd_str = f"{skill_name} {' '.join(args)}".strip()

        parts = []

        # 技能定义
        if skill_content:
            parts.append(f"技能定义:\n{skill_content}")
        else:
            parts.append(f"执行命令: {cmd_str}")

        # 项目状态
        state = self._read_project_state()
        if state:
            parts.append(state)

        # 对话历史
        if history:
            history_str = "\n".join([f"{m['role']}: {m['content']}" for m in history[-5:]])
            parts.append(f"对话历史:\n{history_str}")

        # 用户命令
        parts.append(f"用户命令: /{cmd_str}")

        return "\n\n---\n\n".join(parts)

    def execute(self, cmd_type: str, args: List[str], history: list = None) -> Dict[str, Any]:
        """
        执行CLI命令（同步）

        Args:
            cmd_type: 命令类型
            args: 参数列表
            history: 对话历史

        Returns:
            dict: 执行结果
                - success: bool
                - output: str
                - error: Optional[str]
        """
        prompt = self.build_prompt(cmd_type, args, history)

        # 使用列表形式避免shell注入
        claude_cmd = ["claude", "-p", prompt]

        try:
            result = subprocess.run(
                claude_cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": "",
                "error": "命令执行超时"
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": str(e)
            }

    def execute_streaming(self, cmd_type: str, args: List[str], history: list = None):
        """
        执行CLI命令（流式输出）

        Args:
            cmd_type: 命令类型
            args: 参数列表
            history: 对话历史

        Yields:
            dict: 流式输出事件
                - type: "output" | "error" | "done"
                - content: str
        """
        prompt = self.build_prompt(cmd_type, args, history)

        # 使用列表形式避免shell注入
        claude_cmd = ["claude", "-p", prompt]

        try:
            process = subprocess.Popen(
                claude_cmd,
                cwd=self.project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )

            for line in process.stdout:
                yield {"type": "output", "content": line}

            process.wait()

            if process.returncode != 0:
                stderr = process.stderr.read()
                yield {"type": "error", "content": stderr}
            else:
                yield {"type": "done", "content": ""}

        except Exception as e:
            yield {"type": "error", "content": str(e)}
