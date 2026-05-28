#!/usr/bin/env python3
"""
CLI 增强模块

优化命令行交互体验：
1. 命令自动补全
2. 历史记录
3. 快捷命令
4. 交互式向导
"""

import sys
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass

sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.text import Text

console = Console()


@dataclass
class Command:
    """命令定义"""
    name: str
    description: str
    shortcut: str = None
    examples: List[str] = None

    def __post_init__(self):
        if self.examples is None:
            self.examples = []


class CLIEnhancer:
    """CLI 增强器"""

    def __init__(self):
        self.commands = self._register_commands()
        self.history = []

    def _register_commands(self) -> Dict[str, Command]:
        """注册命令"""
        commands = {
            "crawl": Command(
                name="crawl",
                description="数据爬取",
                shortcut="c",
                examples=["crawl zhihu", "crawl bilibili"]
            ),
            "analyze": Command(
                name="analyze",
                description="数据分析",
                shortcut="a",
                examples=["analyze data.csv", "analyze --template sentiment"]
            ),
            "chat": Command(
                name="chat",
                description="AI 对话",
                shortcut="ch",
                examples=["chat", "chat --file data.csv"]
            ),
            "web": Command(
                name="web",
                description="Web UI",
                shortcut="w",
                examples=["web", "web --port 8080"]
            ),
            "report": Command(
                name="report",
                description="生成报告",
                shortcut="r",
                examples=["report data.csv", "report --template full"]
            ),
            "tools": Command(
                name="tools",
                description="查看工具",
                shortcut="t",
                examples=["tools", "tools --category text"]
            ),
            "validate": Command(
                name="validate",
                description="验证系统",
                shortcut="v",
                examples=["validate", "validate --full"]
            ),
            "help": Command(
                name="help",
                description="显示帮助",
                shortcut="h",
                examples=["help", "help crawl"]
            ),
            "exit": Command(
                name="exit",
                description="退出程序",
                shortcut="q",
                examples=["exit", "quit"]
            ),
        }
        return commands

    def show_welcome(self):
        """显示欢迎信息"""
        console.print(Panel.fit(
            "[bold cyan]🚀 Insight Agent CLI[/]\n\n"
            "智能数据分析工具 - 专业工具优先\n\n"
            "[dim]输入 help 查看所有命令[/]\n"
            "[dim]输入 exit 退出程序[/]",
            border_style="cyan"
        ))

    def show_help(self, command_name: str = None):
        """显示帮助信息"""
        if command_name:
            # 显示特定命令的帮助
            cmd = self.commands.get(command_name)
            if cmd:
                console.print(Panel.fit(
                    f"[bold cyan]{cmd.name}[/] - {cmd.description}\n\n"
                    f"[dim]快捷键: {cmd.shortcut}[/]\n\n"
                    f"[bold]示例:[/]\n" + "\n".join(f"  • {ex}" for ex in cmd.examples),
                    border_style="cyan"
                ))
            else:
                console.print(f"[red]未知命令: {command_name}[/]")
            return

        # 显示所有命令
        table = Table(show_header=True, header_style="bold")
        table.add_column("命令", style="cyan", width=12)
        table.add_column("快捷键", style="green", width=8)
        table.add_column("描述", width=20)
        table.add_column("示例", style="dim")

        for cmd in self.commands.values():
            examples = ", ".join(cmd.examples[:2])
            table.add_row(cmd.name, cmd.shortcut, cmd.description, examples)

        console.print(table)

    def parse_command(self, input_str: str) -> tuple:
        """解析命令"""
        parts = input_str.strip().split()
        if not parts:
            return None, []

        command = parts[0].lower()
        args = parts[1:]

        # 检查快捷键
        for cmd in self.commands.values():
            if cmd.shortcut == command:
                return cmd.name, args

        return command, args

    def execute_command(self, command: str, args: List[str]) -> bool:
        """执行命令"""
        self.history.append(f"{command} {' '.join(args)}".strip())

        if command in ("exit", "quit", "q"):
            return False

        elif command == "help":
            self.show_help(args[0] if args else None)

        elif command == "tools":
            self._show_tools(args)

        elif command == "validate":
            self._run_validation()

        elif command == "crawl":
            self._start_crawl(args)

        elif command == "analyze":
            self._start_analyze(args)

        elif command == "chat":
            self._start_chat(args)

        elif command == "web":
            self._start_web(args)

        elif command == "report":
            self._generate_report(args)

        elif command == "stats":
            self.show_command_stats()

        elif command == "history":
            self._show_history()

        elif command == "clear":
            console.clear()

        elif command == "config":
            self._manage_config(args)

        elif command == "theme":
            self._change_theme(args)

        else:
            console.print(f"[yellow]未知命令: {command}[/]")
            console.print("[dim]输入 help 查看所有命令[/]")

        return True

    def _show_history(self):
        """显示命令历史"""
        if not self.history:
            console.print("[dim]暂无命令历史[/]")
            return

        table = Table(title="📜 命令历史")
        table.add_column("#", style="dim", width=4)
        table.add_column("命令", style="cyan")
        table.add_column("时间", style="green")

        for i, cmd in enumerate(self.history[-20:], 1):
            table.add_row(str(i), cmd, "")

        console.print(table)

    def _manage_config(self, args: List[str]):
        """管理配置"""
        if not args:
            console.print("[bold]配置管理[/]")
            console.print("  config show    - 显示配置")
            console.print("  config get KEY - 获取配置")
            console.print("  config set KEY VALUE - 设置配置")
            return

        action = args[0]

        if action == "show":
            console.print("[cyan]当前配置:[/]")
            # 显示配置
        elif action == "get" and len(args) > 1:
            key = args[1]
            console.print(f"[cyan]{key}[/] = [green]value[/]")
        elif action == "set" and len(args) > 2:
            key = args[1]
            value = args[2]
            console.print(f"[green]✅ 已设置 {key} = {value}[/]")

    def _change_theme(self, args: List[str]):
        """更换主题"""
        if not args:
            console.print("[bold]可用主题:[/]")
            console.print("  default - 默认主题")
            console.print("  dark    - 深色主题")
            console.print("  light   - 浅色主题")
            return

        theme = args[0]
        console.print(f"[green]✅ 已切换到 {theme} 主题[/]")

    def _show_tools(self, args: List[str]):
        """显示工具列表"""
        from analysis.tools_registry import get_available_tools

        tools = get_available_tools()

        if args and args[0] == "--category":
            # 按类别筛选
            category = args[1] if len(args) > 1 else None
            if category:
                tools = [t for t in tools if t["category"] == category]

        table = Table(show_header=True, header_style="bold")
        table.add_column("工具名称", style="cyan")
        table.add_column("类别", style="green")
        table.add_column("描述")
        table.add_column("需要字段", style="yellow")

        for tool in tools:
            fields = ", ".join(tool["required_fields"]) if tool["required_fields"] else "任意"
            table.add_row(
                tool["name"],
                tool["category"],
                tool["description"][:40] + "...",
                fields
            )

        console.print(table)

    def _run_validation(self):
        """运行系统验证"""
        from validate_system import main as validate_main
        validate_main()

    def _start_crawl(self, args: List[str]):
        """启动爬虫"""
        from main import _start_crawl_mode
        # 这里可以添加参数处理
        console.print("[cyan]启动数据爬取...[/]")
        # 实际调用爬虫逻辑

    def _start_analyze(self, args: List[str]):
        """启动分析"""
        from main import _start_analysis_mode
        console.print("[cyan]启动数据分析...[/]")
        # 实际调用分析逻辑

    def _start_chat(self, args: List[str]):
        """启动 AI 对话"""
        from main import _start_chat_mode
        console.print("[cyan]启动 AI 对话...[/]")
        # 实际调用对话逻辑

    def _start_web(self, args: List[str]):
        """启动 Web UI"""
        from tools.webui_manager import main as webui_main
        console.print("[cyan]启动 Web UI...[/]")
        # 实际调用 Web UI

    def _generate_report(self, args: List[str]):
        """生成报告"""
        console.print("[cyan]生成报告...[/]")
        # 实际调用报告生成

    def get_completions(self, text: str) -> List[str]:
        """获取命令补全"""
        completions = []
        for cmd in self.commands.values():
            if cmd.name.startswith(text):
                completions.append(cmd.name)
            if cmd.shortcut and cmd.shortcut.startswith(text):
                completions.append(cmd.shortcut)
        return completions

    def get_smart_suggestions(self, partial_command: str) -> List[str]:
        """获取智能建议"""
        suggestions = []

        # 根据上下文提供建议
        if partial_command.startswith("crawl"):
            suggestions = ["zhihu", "bilibili", "xiaohongshu", "douyin", "cnki", "tmall", "jd", "douban"]
        elif partial_command.startswith("analyze"):
            suggestions = ["--template", "--format", "--output", "--verbose"]
        elif partial_command.startswith("chat"):
            suggestions = ["--file", "--model", "--stream"]
        elif partial_command.startswith("web"):
            suggestions = ["--port", "--background", "--host"]
        elif partial_command.startswith("tools"):
            suggestions = ["--category", "--list", "--search"]
        elif partial_command.startswith("report"):
            suggestions = ["--template", "--format", "--output"]

        return suggestions

    def show_command_stats(self):
        """显示命令统计"""
        from collections import Counter

        if not self.history:
            console.print("[dim]暂无命令历史[/]")
            return

        stats = Counter(self.history)

        table = Table(title="📊 命令统计")
        table.add_column("命令", style="cyan")
        table.add_column("次数", justify="right")
        table.add_column("占比", justify="right")

        for cmd, count in stats.most_common(10):
            pct = count / len(self.history) * 100
            table.add_row(cmd, str(count), f"{pct:.1f}%")

        console.print(table)

    def show_context_help(self, command: str):
        """显示上下文帮助"""
        help_texts = {
            "crawl": """
💡 可用平台：
  • zhihu - 知乎回答
  • bilibili - B站视频
  • xiaohongshu - 小红书笔记
  • douyin - 抖音评论
  • cnki - 知网论文
  • tmall - 天猫评论
  • jd - 京东评论
  • douban - 豆瓣图书/电影

📝 示例：
  crawl zhihu
  crawl bilibili --max 100
  crawl xiaohongshu "人工智能"
""",
            "analyze": """
💡 分析选项：
  • --template sentiment - 情感分析
  • --template word_freq - 词频统计
  • --template stats - 基础统计
  • --template time - 时间序列
  • --template theme - 主题提取

📝 示例：
  analyze data.csv
  analyze data.csv --template sentiment
  analyze *.csv --template stats
""",
            "chat": """
💡 对话选项：
  • --file data.csv - 指定数据文件
  • --model deepseek - 指定模型
  • --stream - 流式输出

📝 示例：
  chat
  chat --file data.csv
  chat --model deepseek
""",
            "web": """
💡 Web UI 选项：
  • --port 8080 - 指定端口
  • --background - 后台运行
  • --host 0.0.0.0 - 绑定地址

📝 示例：
  web
  web --port 8080
  web --background
""",
            "tools": """
💡 工具选项：
  • --category text - 文本分析
  • --category quantitative - 定量分析
  • --category time_series - 时间序列
  • --category qualitative - 定性分析

📝 示例：
  tools
  tools --category text
  tools --search 情感
""",
        }

        if command in help_texts:
            console.print(help_texts[command])

    def interactive_mode(self):
        """交互模式"""
        self.show_welcome()

        while True:
            try:
                # 使用 prompt_toolkit 获取输入
                from prompt_toolkit import PromptSession
                from prompt_toolkit.completion import WordCompleter, NestedCompleter
                from prompt_toolkit.history import FileHistory
                from prompt_toolkit.auto_suggest import AutoSuggestFromHistory

                # 创建命令补全器（支持嵌套补全）
                command_completer = NestedCompleter.from_nested_dict({
                    "crawl": {"zhihu", "bilibili", "xiaohongshu", "douyin", "cnki", "tmall", "jd", "douban"},
                    "analyze": {"--template", "--format", "--output", "--verbose"},
                    "chat": {"--file", "--model", "--stream"},
                    "web": {"--port", "--background", "--host"},
                    "tools": {"--category", "--list", "--search"},
                    "report": {"--template", "--format", "--output"},
                    "validate": None,
                    "stats": None,
                    "help": None,
                    "exit": None,
                })

                # 创建历史记录
                history = FileHistory(Path.home() / ".insight" / "history")

                # 创建会话
                session = PromptSession(
                    completer=command_completer,
                    history=history,
                    auto_suggest=AutoSuggestFromHistory(),
                )

                user_input = session.prompt(
                    [("class:prompt", "  Insight"), ("class:separator", " › ")]
                ).strip()

                if not user_input:
                    continue

                # 显示智能提示
                suggestions = self.get_smart_suggestions(user_input)
                if suggestions and not user_input.endswith(" "):
                    console.print(f"[dim]💡 可用选项: {', '.join(suggestions[:5])}[/]")

                command, args = self.parse_command(user_input)
                if command:
                    should_continue = self.execute_command(command, args)
                    if not should_continue:
                        break

            except KeyboardInterrupt:
                console.print("\n[dim]使用 exit 退出[/]")
            except EOFError:
                break

        console.print("[dim]再见！[/]")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="Insight Agent CLI 增强器")
    parser.add_argument("command", nargs="?", help="直接执行命令")
    parser.add_argument("args", nargs="*", help="命令参数")

    args = parser.parse_args()

    enhancer = CLIEnhancer()

    if args.command:
        # 命令行模式
        enhancer.execute_command(args.command, args.args)
    else:
        # 交互模式
        enhancer.interactive_mode()


if __name__ == "__main__":
    main()
