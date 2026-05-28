"""Insight Agent — 智能数据分析欢迎界面"""

from rich.console import Console
from rich.align import Align
from rich.text import Text
from rich.rule import Rule
from rich.panel import Panel
from rich import box

console = Console()


def _get_banner():
    """使用 pyfiglet 生成 ASCII 艺术字"""
    try:
        import pyfiglet
        # 用 small 字体生成 Insight
        insight = pyfiglet.figlet_format("Insight", font="small", width=200)
        insight_lines = [l.rstrip() for l in insight.split("\n") if l.strip()]
        return insight_lines
    except ImportError:
        # 备用简洁版本
        return [
            " ___                  _           _   ",
            "|_ _|_ __  _ __   ___| |_   ___  | |_",
            " | || '_ \\| '_ \\ / _ \\ __| / _ \\ | __|",
            " | || | | | | | |  __/ |_ | (_) || |_",
            "|___|_| |_|_| |_|\\___|\\__| \\___/  \\__|",
        ]


def show_welcome():
    """显示欢迎界面"""
    console.clear()

    term_w = console.width

    # 顶部装饰线
    console.print()
    console.print(Rule(style="bright_cyan", characters="═"))

    # ASCII 标题
    banner = _get_banner()
    for line in banner:
        pad = max(0, (term_w - len(line)) // 2)
        console.print(" " * pad + f"[bold bright_cyan]{line}[/]")

    # 项目名称
    console.print()
    name = Text()
    name.append("Insight", style="bold bright_white")
    name.append("  Agent", style="bold bright_cyan")
    console.print(Align.center(name))

    # 分隔线
    console.print(Rule(style="bright_cyan", characters="═"))

    # 项目说明
    console.print()
    console.print(Align.center(Text(
        "一句话描述需求，自动采集全网数据，AI 智能分析生成报告",
        style="dim italic"
    )))

    # 能力概览（用 Panel 包裹）
    console.print()

    capabilities = Text()
    capabilities.append("  🕷 ", style="bold")
    capabilities.append("8 平台爬虫", style="cyan")
    capabilities.append("   │   ", style="dim")
    capabilities.append("📊 ", style="bold")
    capabilities.append("10 分析工具", style="green")
    capabilities.append("   │   ", style="dim")
    capabilities.append("🤖 ", style="bold")
    capabilities.append("AI 深度对话", style="yellow")
    capabilities.append("   │   ", style="dim")
    capabilities.append("📄 ", style="bold")
    capabilities.append("自动报告", style="magenta")

    console.print(Panel(
        Align.center(capabilities),
        border_style="bright_cyan",
        box=box.HEAVY,
        padding=(0, 2),
        title="[bold bright_cyan] 核心能力 [/]",
        title_align="center"
    ))

    # 工作流
    console.print()

    workflow = Text()
    workflow.append("  工作流  ", style="dim bold")
    workflow.append("采集", style="cyan bold")
    workflow.append(" ──→ ", style="dim")
    workflow.append("清洗", style="green bold")
    workflow.append(" ──→ ", style="dim")
    workflow.append("分析", style="yellow bold")
    workflow.append(" ──→ ", style="dim")
    workflow.append("报告", style="magenta bold")
    workflow.append(" ──→ ", style="dim")
    workflow.append("问答", style="red bold")

    console.print(Panel(
        Align.center(workflow),
        border_style="dim",
        box=box.ROUNDED,
        padding=(0, 1)
    ))

    # 底部装饰线
    console.print()
    console.print(Rule(style="bright_cyan", characters="═"))
    console.print()
