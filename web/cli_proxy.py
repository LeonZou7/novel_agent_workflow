"""
CLI代理模块 - 安全地代理本地Claude CLI调用

此模块提供：
- 命令解析和验证
- 安全的命令执行（带超时和错误处理）
- 流式输出支持
- 完整的测试覆盖
"""

import re
import subprocess
import shlex
import logging
from typing import Optional, Tuple, List, Dict, Any

logger = logging.getLogger(__name__)


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
            "novel": "znovel-director"
        }

        skill = skill_map.get(cmd_type, cmd_type)
        cmd_args = " ".join(args) if args else ""

        return f"{skill} {cmd_args}".strip()

    def execute(self, cmd_type: str, args: List[str]) -> Dict[str, Any]:
        """
        执行CLI命令（同步）

        Args:
            cmd_type: 命令类型
            args: 参数列表

        Returns:
            dict: 执行结果
                - success: bool
                - output: str
                - error: Optional[str]
        """
        skill = self.build_cli_command(cmd_type, args)

        # 构建Claude CLI命令
        claude_cmd = f'claude -p "{skill}" --no-input'

        try:
            result = subprocess.run(
                claude_cmd,
                shell=True,
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

    def execute_streaming(self, cmd_type: str, args: List[str]):
        """
        执行CLI命令（流式输出）

        Args:
            cmd_type: 命令类型
            args: 参数列表

        Yields:
            dict: 流式输出事件
                - type: "output" | "error" | "done"
                - content: str
        """
        skill = self.build_cli_command(cmd_type, args)
        claude_cmd = f'claude -p "{skill}" --no-input'

        try:
            process = subprocess.Popen(
                claude_cmd,
                shell=True,
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
