"""CLI 交互式命令 — 从 main.py 拆分

包含：自然语言爬虫、技能模板、定时任务、Web UI、登录管理、批量分析
"""

import json
import logging
from pathlib import Path
from typing import List

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, CRAWLER_SCRIPTS, ANALYSIS_MODELS
from ui import select_crawler, get_crawler_args, select_existing_file, select_multiple_files, confirm_step
from crawlers.runner import run_crawler, get_latest_output_files, login_crawler

logger = logging.getLogger(__name__)
console = Console()


def check_and_login_if_needed(crawler_key: str):
    """爬虫运行前的登录检查"""
    needs_login = {"douyin", "zhihu", "xiaohongshu", "tmall", "jd"}
    if crawler_key not in needs_login:
        return

    from crawlers.common.login_helper import is_session_valid

    if is_session_valid(crawler_key):
        return

    console.print()
    console.print(f"  [yellow]⚠ {crawler_key} 尚未登录或 session 已过期[/]")
    console.print(f"  [dim]需要先在浏览器中手动登录，登录状态会缓存，之后无需重复登录[/]")

    from rich.prompt import Confirm
    if Confirm.ask(f"  是否现在登录 {crawler_key}？", default=True):
        login_crawler(crawler_key)


def login_setup():
    """登录设置：预登录各平台"""
    from crawlers.common.login_helper import print_session_status

    console.print()
    console.print(Panel.fit(
        "[bold cyan]🔑 登录设置[/]\n\n"
        "预登录各平台，缓存 session，之后爬取时无需重复登录\n"
        "[dim]首次使用或 session 过期时需要执行[/]",
        border_style="cyan"
    ))

    print_session_status()

    console.print("  [bold]可登录的平台:[/]")
    platforms = [
        ("douyin", "抖音"),
        ("zhihu", "知乎"),
        ("xiaohongshu", "小红书"),
        ("tmall", "天猫"),
        ("jd", "京东"),
    ]
    for i, (key, name) in enumerate(platforms, 1):
        console.print(f"    {i}. {name} ({key})")

    console.print(f"    0. 返回")

    try:
        choice = input("\n  选择平台 (输入数字): ").strip()
        if choice == "0" or not choice:
            return
        idx = int(choice) - 1
        if 0 <= idx < len(platforms):
            key, name = platforms[idx]
            login_crawler(key)
        else:
            console.print("  [red]无效选择[/]")
    except (ValueError, IndexError):
        console.print("  [red]无效输入[/]")


def natural_language_crawl(load_data_fn, run_ai_flow_fn):
    """自然语言描述需求，AI 自动选爬虫"""
    console.print()
    console.print(Panel.fit(
        "[bold cyan]💬 自然语言启动爬虫[/]\n"
        "用日常语言描述你想采集什么数据",
        border_style="cyan"
    ))

    if not LLM_API_KEY:
        console.print("  [red]未配置 DEEPSEEK_API_KEY，无法使用自然语言功能[/]")
        return

    desc = Prompt.ask("\n  [bold]描述需求[/]",
        default="爬知乎上关于人工智能的回答，要100条")

    from openai import OpenAI
    client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)

    platforms_desc = "\n".join(
        f"- {k}: {v['platform']} — {v['description']}"
        for k, v in CRAWLER_SCRIPTS.items()
    )

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{
            "role": "system",
            "content": f"""你是一个爬虫任务解析器。根据用户描述，选择最合适的爬虫平台并解析参数。
可用平台：
{platforms_desc}

输出JSON格式：
{{"platform_key": "zhihu", "params": {{"url": "https://...", "max": 100}}, "reason": "选择理由"}}
如果无法确定，platform_key 为 null。直接输出JSON不要其他文字。"""
        }, {
            "role": "user",
            "content": desc
        }],
        max_tokens=300,
        temperature=0.1,
    )

    raw = response.choices[0].message.content
    try:
        parsed = json.loads(raw.strip().split("```")[0].strip())
    except json.JSONDecodeError as e:
        console.print(f"  [red]无法解析AI回复: {raw[:200]}[/]")
        logger.error(f"JSON解析失败: {e}")
        return

    platform = parsed.get("platform_key")
    if not platform or platform not in CRAWLER_SCRIPTS:
        console.print(f"  [yellow]无法确定爬虫平台，建议手动选择[/]")
        return

    info = CRAWLER_SCRIPTS[platform]
    params = parsed.get("params", {})
    reason = parsed.get("reason", "")

    console.print(f"\n  [green]✓[/] AI 分析: [bold]{info['name']}[/] ({info['platform']})")
    console.print(f"  [dim]原因: {reason}[/]")

    if not confirm_step("确认执行？"):
        return

    output_dir = run_crawler(platform, params)
    files = get_latest_output_files(output_dir)
    if not files:
        return

    data = load_data_fn(files[0])
    if data:
        run_ai_flow_fn(data, files[0])


def run_skill_template(load_data_fn, preview_fn, run_ai_flow_fn):
    """运行预设分析模板"""
    from skills import list_templates, get_template
    from rich.table import Table
    from concurrent.futures import ThreadPoolExecutor, as_completed

    console.print()
    console.print(Panel.fit("[bold cyan]📋 分析技能模板[/]", border_style="cyan"))

    templates = list_templates()
    t = Table(show_header=True, header_style="bold")
    t.add_column("#", width=4)
    t.add_column("模板", width=22)
    t.add_column("说明", width=45)
    for i, tmpl in enumerate(templates, 1):
        t.add_row(str(i), tmpl["name"], tmpl["desc"])
    console.print(t)
    console.print()

    try:
        choice = Prompt.ask("[bold]选择模板[/]", default="1")
        idx = int(choice) - 1
        if 0 <= idx < len(templates):
            tmpl = get_template(templates[idx]["id"])
        else:
            return
    except (ValueError, IndexError) as e:
        console.print(f"[red]无效选择: {e}[/]")
        return

    data_file = select_existing_file()
    if not data_file:
        return

    data = load_data_fn(data_file)
    if not data:
        return

    if not preview_fn(data, data_file):
        return

    console.print(f"\n  [cyan]执行: {tmpl['name']}...[/]")
    from main import _run_single_quant, _run_single_qual
    results = {}
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {}
        for model in tmpl["models"]:
            if model in ANALYSIS_MODELS.get("quantitative", {}):
                futures[pool.submit(_run_single_quant, data, model, data_file)] = model
            elif model in ANALYSIS_MODELS.get("qualitative", {}):
                futures[pool.submit(_run_single_qual, data, model, data_file)] = model
        for f in as_completed(futures):
            try:
                results.update(f.result())
            except Exception as e:
                logger.warning(f"分析任务失败: {e}")
                continue

    from report import generate_report
    crawler_info = {"platform": "模板分析", "name": data_file.name}
    report_path = generate_report(crawler_info, results, data_file, data_file.parent)
    console.print(f"\n  [green]✓[/] 报告: {report_path}")

    if confirm_step("进入AI对话？"):
        run_ai_flow_fn(data, data_file)


def manage_schedule():
    """管理定时任务"""
    from scheduler import Scheduler
    from rich.table import Table

    scheduler = Scheduler()
    console.print()
    console.print(Panel.fit("[bold cyan]📅 定时任务管理[/]", border_style="cyan"))

    jobs = scheduler.list_jobs()
    if jobs:
        t = Table(show_header=True, header_style="bold")
        t.add_column("ID", width=14)
        t.add_column("状态", width=6)
        t.add_column("平台", width=10)
        t.add_column("参数", width=30)
        t.add_column("间隔", width=6)
        t.add_column("上次", width=16)
        for j in jobs:
            t.add_row(j["id"], j["status"], j["platform"], j["params"][:28], j["interval"], j["last"])
        console.print(t)
    else:
        console.print("  [dim]暂无定时任务[/]")

    console.print()
    action = Prompt.ask("[bold]操作[/]", choices=["add", "remove", "run", "q"], default="add")
    if action == "q":
        return
    elif action == "add":
        sel = select_crawler()
        if not sel:
            return
        key, info = sel
        args = get_crawler_args(info)
        interval = Prompt.ask("  间隔(小时)", default="24")
        job_id = scheduler.add(key, args, int(interval))
        console.print(f"  [green]✓[/] 任务已创建: {job_id}")
    elif action == "remove":
        jid = Prompt.ask("  任务ID")
        scheduler.remove(jid)
        console.print("  [green]✓[/] 已删除")
    elif action == "run":
        results = scheduler.run_now()
        for r in results:
            console.print(f"  {r['status']} {r.get('report', '')}")


def start_web_ui():
    """启动 Web UI"""
    from web.server import start_server

    console.print("\n  [cyan]🌐 Web UI 启动选项[/]")
    console.print("  [dim]1. 前台运行（占用终端，按 Ctrl+C 停止）[/]")
    console.print("  [dim]2. 后台运行（终端可继续使用）[/]")

    choice = Prompt.ask("  [bold]选择模式[/]", choices=["1", "2"], default="2")

    if choice == "1":
        console.print("\n  [cyan]🌐 正在启动 Web UI (前台模式)...[/]")
        start_server(port=9527, open_browser=True, background=False)
    else:
        console.print("\n  [cyan]🌐 正在启动 Web UI (后台模式)...[/]")
        start_server(port=9527, open_browser=True, background=True)

        import time
        time.sleep(2)

        console.print("\n  [green]✅ Web UI 已在后台启动[/]")
        console.print(f"  [bold]访问地址:[/] http://localhost:9527")
        console.print("  [dim]终端可继续使用，Web 服务器在后台运行[/]")


def run_batch_analysis(files: List[Path], load_data_fn=None):
    """批量分析多个文件并生成对比报告"""
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from main import load_data, _run_single_quant, _show_summary
    from report import generate_report

    if load_data_fn is None:
        load_data_fn = load_data

    all_reports = []
    console.print()
    console.print(Panel.fit(
        f"[bold magenta]批量分析: {len(files)} 个文件[/]",
        border_style="magenta"
    ))

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
                  console=console) as progress:
        task = progress.add_task("[cyan]分析中...", total=len(files))

        for f in files:
            progress.update(task, description=f"[cyan]分析: {f.name}[/]")
            data = load_data_fn(f)
            if not data:
                progress.advance(task)
                continue

            results = {}
            for model in ["basic_stats", "sentiment", "word_freq"]:
                try:
                    r = _run_single_quant(data, model, f)
                    results.update(r)
                except Exception as e:
                    logger.warning(f"分析模型 {model} 失败: {e}")
                    continue

            crawler_info = {"platform": "本地文件", "name": f.name}
            report_path = generate_report(crawler_info, results, f, f.parent)
            all_reports.append({"file": f.name, "path": report_path, "results": results})
            progress.advance(task)

    console.print(f"\n  [green]✓[/] {len(all_reports)}/{len(files)} 个文件分析完成")
    for r in all_reports:
        record_count = r["results"].get("basic_stats", {}).get("record_count", "?")
        console.print(f"    📄 {r['file']} — {record_count} 条记录 → {r['path'].name}")

    console.print()
    if confirm_step(f"在浏览器中打开所有报告？"):
        import webbrowser
        for r in all_reports:
            webbrowser.open(f"file://{r['path']}")
