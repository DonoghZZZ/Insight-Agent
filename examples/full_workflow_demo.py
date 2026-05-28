#!/usr/bin/env python3
"""
完整工作流程演示

演示从数据加载到分析报告的完整流程
"""

import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def demo_full_workflow():
    """演示完整工作流程"""
    console.print(Panel.fit(
        "[bold cyan]🎯 Insight Agent 完整工作流程演示[/]\n\n"
        "演示：数据加载 → 工具推荐 → 智能分析 → 结果展示",
        border_style="cyan"
    ))

    # 1. 准备示例数据
    console.print("\n[bold]1️⃣ 准备示例数据[/]")
    sample_data = [
        {"content": "这个产品非常好用，强烈推荐给大家", "score": "85", "date": "2024-01-15"},
        {"content": "体验很差，非常失望，不推荐购买", "score": "45", "date": "2024-01-16"},
        {"content": "一般般，没什么特别的感觉", "score": "65", "date": "2024-01-17"},
        {"content": "太棒了，物超所值，下次还会买", "score": "95", "date": "2024-01-18"},
        {"content": "还需要改进，不够好用", "score": "55", "date": "2024-01-19"},
        {"content": "非常满意，客服态度很好", "score": "90", "date": "2024-01-20"},
        {"content": "质量一般，价格偏高", "score": "60", "date": "2024-01-21"},
        {"content": "超级喜欢，已经推荐给朋友", "score": "92", "date": "2024-01-22"},
    ]

    console.print(f"   ✅ 已加载 {len(sample_data)} 条数据")
    console.print(f"   📊 字段: {', '.join(sample_data[0].keys())}")

    # 2. 工具推荐
    console.print("\n[bold]2️⃣ 智能工具推荐[/]")
    from analysis.tools_registry import recommend_tools

    recommended = recommend_tools(sample_data)
    console.print(f"   ✅ 推荐工具: {', '.join(recommended)}")

    # 3. 智能分析
    console.print("\n[bold]3️⃣ 智能分析演示[/]")

    from analysis.smart_analyzer import smart_analyze
    from pathlib import Path

    data_file = Path("demo_data.csv")

    # 测试不同的分析需求
    queries = [
        "帮我做情感分析",
        "统计一下数据",
        "提取关键词",
    ]

    results = []
    for query in queries:
        console.print(f"\n   [cyan]查询:[/] {query}")
        result = smart_analyze(sample_data, data_file, query)

        console.print(f"   [green]✅ 使用工具:[/] {result.tool_name}")
        console.print(f"   [green]✅ 来源:[/] {result.source}")
        console.print(f"   [green]✅ 成功:[/] {'✅' if result.success else '❌'}")
        console.print(f"   [green]✅ 耗时:[/] {result.execution_time:.2f}秒")

        results.append({
            "query": query,
            "tool": result.tool_name,
            "source": result.source,
            "success": result.success,
            "time": result.execution_time,
        })

    # 4. 结果汇总
    console.print("\n[bold]4️⃣ 分析结果汇总[/]")

    table = Table(show_header=True, header_style="bold")
    table.add_column("查询", style="cyan")
    table.add_column("使用工具", style="green")
    table.add_column("来源", style="yellow")
    table.add_column("耗时", justify="right")

    for r in results:
        table.add_row(
            r["query"],
            r["tool"],
            r["source"],
            f"{r['time']:.2f}秒"
        )

    console.print(table)

    # 5. 性能统计
    console.print("\n[bold]5️⃣ 性能统计[/]")
    total_time = sum(r["time"] for r in results)
    builtin_count = sum(1 for r in results if r["source"] == "builtin")
    llm_count = sum(1 for r in results if r["source"] == "llm")

    console.print(f"   📊 总耗时: {total_time:.2f}秒")
    console.print(f"   ⚡ 专业工具: {builtin_count} 次")
    console.print(f"   🤖 大模型: {llm_count} 次")
    console.print(f"   💰 节省 API 调用: {builtin_count} 次")

    # 6. 总结
    console.print("\n" + "="*60)
    console.print("[bold green]✅ 完整工作流程演示完成！[/]")
    console.print("="*60)
    console.print("\n💡 关键优势:")
    console.print("   ✅ 专业工具优先，速度快")
    console.print("   ✅ 智能匹配，无需手动选择")
    console.print("   ✅ 大模型兜底，覆盖所有需求")
    console.print("   ✅ 节省 API 调用，降低成本")

    return results


def demo_advanced_analysis():
    """演示高级分析功能"""
    console.print(Panel.fit(
        "[bold cyan]🔬 高级分析功能演示[/]",
        border_style="cyan"
    ))

    # 示例数据
    sample_data = [
        {"content": "这个产品非常好用，强烈推荐", "score": "85", "category": "电子产品"},
        {"content": "体验很差，非常失望", "score": "45", "category": "电子产品"},
        {"content": "服务态度很好，物流很快", "score": "88", "category": "服务"},
        {"content": "价格偏高，性价比一般", "score": "60", "category": "电子产品"},
        {"content": "客服很耐心，解决问题很快", "score": "92", "category": "服务"},
    ]

    # 1. 多维度分析
    console.print("\n[bold]1️⃣ 多维度分析[/]")

    from analysis.tools_registry import execute_tool
    from pathlib import Path

    data_file = Path("demo.csv")

    # 情感分析
    sentiment = execute_tool("sentiment_analysis", sample_data, data_file)
    console.print(f"   情感分析: 正面 {sentiment.get('positive_pct', 0)}%")

    # 词频统计
    word_freq = execute_tool("word_frequency", sample_data, data_file)
    keywords = word_freq.get("keywords", [])[:5]
    console.print(f"   关键词: {', '.join(kw['word'] for kw in keywords)}")

    # 基础统计
    stats = execute_tool("basic_stats", sample_data, data_file)
    console.print(f"   记录数: {stats.get('record_count')}")

    # 2. 组合分析
    console.print("\n[bold]2️⃣ 组合分析建议[/]")

    from analysis.tools_registry import get_available_tools

    tools = get_available_tools()
    console.print("   可用工具:")
    for tool in tools[:5]:
        console.print(f"     - {tool['name']}: {tool['description'][:30]}...")

    console.print("\n" + "="*60)
    console.print("[bold green]✅ 高级分析演示完成！[/]")
    console.print("="*60)


def main():
    """主函数"""
    console.print("[bold]Insight Agent 完整工作流程演示[/]\n")

    console.print("选择演示:")
    console.print("  1. 完整工作流程")
    console.print("  2. 高级分析功能")
    console.print("  3. 运行所有演示")

    choice = input("\n请选择 (1-3): ").strip()

    if choice == "1":
        demo_full_workflow()
    elif choice == "2":
        demo_advanced_analysis()
    elif choice == "3":
        demo_full_workflow()
        console.print("\n" + "="*60 + "\n")
        demo_advanced_analysis()
    else:
        console.print("[red]无效选择[/]")


if __name__ == "__main__":
    main()
