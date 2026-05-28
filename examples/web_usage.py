#!/usr/bin/env python3
"""
Web UI 使用示例

演示如何在后台启动 Web 服务器，并继续使用终端
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from web.server import start_server
from rich.console import Console
from rich.panel import Panel

console = Console()


def example_1_background_server():
    """示例 1: 后台启动 Web 服务器"""
    console.print(Panel.fit(
        "[bold cyan]示例 1: 后台启动 Web 服务器[/]\n\n"
        "启动 Web 服务器后，终端可以继续使用",
        border_style="cyan"
    ))

    # 后台启动服务器
    console.print("\n[cyan]启动 Web 服务器...[/]")
    server_thread = start_server(port=9527, open_browser=True, background=True)

    # 等待服务器启动
    time.sleep(2)

    console.print("[green]✅ Web 服务器已在后台启动[/]")
    console.print("[bold]访问地址:[/] http://localhost:9527")
    console.print("[dim]终端现在可以继续使用[/]")

    # 模拟其他操作
    console.print("\n[cyan]执行其他操作...[/]")
    for i in range(3):
        time.sleep(1)
        console.print(f"  [dim]操作 {i+1}/3 完成[/]")

    console.print("\n[green]✅ 所有操作完成[/]")
    console.print("[dim]Web 服务器仍在后台运行[/]")

    # 不要在这里停止服务器，让它继续运行
    return server_thread


def main():
    """主函数"""
    console.print("[bold]Insight Agent Web UI 使用示例[/]\n")
    server = example_1_background_server()
    input("\n按 Enter 停止服务器...")


if __name__ == "__main__":
    main()
