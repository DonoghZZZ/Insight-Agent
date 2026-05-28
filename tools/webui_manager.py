#!/usr/bin/env python3
"""Web UI 管理器 - 独立管理 Web 服务器"""

import sys
import signal
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from web.server import app, start_server
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt

console = Console()

# 全局服务器线程
_server_thread = None
_server_running = False


def signal_handler(sig, frame):
    """处理 Ctrl+C 信号"""
    global _server_running
    console.print("\n\n[yellow]🛑 正在停止 Web 服务器...[/]")
    _server_running = False
    sys.exit(0)


def show_status():
    """显示服务器状态"""
    global _server_running, _server_thread

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("项目", style="dim")
    table.add_column("状态")

    table.add_row("服务器状态", "🟢 运行中" if _server_running else "🔴 已停止")
    table.add_row("访问地址", "http://localhost:9527" if _server_running else "未启动")
    table.add_row("线程", str(_server_thread) if _server_thread else "无")

    console.print(table)


def start_background():
    """后台启动服务器"""
    global _server_thread, _server_running

    if _server_running:
        console.print("[yellow]⚠️ 服务器已在运行中[/]")
        return

    console.print("\n[cyan]🌐 正在启动 Web 服务器...[/]")

    _server_thread = start_server(port=9527, open_browser=True, background=True)
    _server_running = True

    time.sleep(2)
    console.print("\n[green]✅ Web 服务器已启动[/]")
    console.print("[bold]访问地址:[/] http://localhost:9527")
    console.print("[dim]终端可继续使用[/]")


def stop_server():
    """停止服务器"""
    global _server_running, _server_thread

    if not _server_running:
        console.print("[yellow]⚠️ 服务器未在运行[/]")
        return

    console.print("\n[yellow]🛑 正在停止服务器...[/]")
    _server_running = False
    # 注意：daemon 线程会在主程序退出时自动停止
    console.print("[green]✅ 服务器已停止[/]")


def interactive_mode():
    """交互模式"""
    global _server_running

    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)

    console.print(Panel.fit(
        "[bold cyan]🌐 Insight Agent Web UI 管理器[/]\n\n"
        "可用命令:\n"
        "  start   - 启动服务器（后台）\n"
        "  stop    - 停止服务器\n"
        "  status  - 查看状态\n"
        "  open    - 在浏览器打开\n"
        "  help    - 显示帮助\n"
        "  exit    - 退出",
        border_style="cyan"
    ))

    while True:
        try:
            command = Prompt.ask("\n[bold]webui[/]").strip().lower()

            if command in ("start", "s"):
                start_background()
            elif command == "stop":
                stop_server()
            elif command in ("status", "st"):
                show_status()
            elif command == "open":
                import webbrowser
                if _server_running:
                    webbrowser.open("http://localhost:9527")
                    console.print("[green]✅ 已在浏览器打开[/]")
                else:
                    console.print("[yellow]⚠️ 服务器未运行，请先启动[/]")
            elif command in ("help", "h", "?"):
                console.print("""
[bold]可用命令:[/]
  [cyan]start[/]   - 启动 Web 服务器（后台运行）
  [cyan]stop[/]    - 停止 Web 服务器
  [cyan]status[/]  - 查看服务器状态
  [cyan]open[/]    - 在浏览器中打开 Web UI
  [cyan]help[/]    - 显示此帮助信息
  [cyan]exit[/]    - 退出管理器
                """)
            elif command in ("exit", "quit", "q"):
                if _server_running:
                    console.print("[yellow]⚠️ 服务器仍在运行，退出时将自动停止[/]")
                console.print("[dim]再见！[/]")
                break
            else:
                console.print(f"[yellow]未知命令: {command}，输入 help 查看帮助[/]")

        except KeyboardInterrupt:
            console.print("\n[dim]使用 exit 退出[/]")
        except EOFError:
            break


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="Insight Agent Web UI 管理器")
    parser.add_argument("command", nargs="?", choices=["start", "stop", "status", "open"],
                        help="直接执行命令")
    parser.add_argument("--port", type=int, default=9527, help="服务器端口")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")

    args = parser.parse_args()

    if args.command:
        # 命令行模式
        if args.command == "start":
            start_background()
        elif args.command == "stop":
            stop_server()
        elif args.command == "status":
            show_status()
        elif args.command == "open":
            import webbrowser
            webbrowser.open(f"http://localhost:{args.port}")
    else:
        # 交互模式
        interactive_mode()


if __name__ == "__main__":
    main()
