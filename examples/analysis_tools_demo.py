#!/usr/bin/env python3
"""
分析工具使用示例

演示如何使用新的工具注册系统
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def demo_list_tools():
    """演示：列出所有可用工具"""
    console.print(Panel.fit("[bold cyan]📋 所有可用分析工具[/]", border_style="cyan"))

    from analysis.tools_registry import get_available_tools

    tools = get_available_tools()

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
            tool["description"][:50] + "...",
            fields
        )

    console.print(table)


def demo_recommend_tools():
    """演示：根据数据推荐工具"""
    console.print(Panel.fit("[bold cyan]🎯 根据数据推荐工具[/]", border_style="cyan"))

    # 示例数据
    sample_data = [
        {"content": "这个产品非常好用", "score": "85", "date": "2024-01-15"},
        {"content": "体验很差，不推荐", "score": "45", "date": "2024-01-16"},
        {"content": "一般般，没什么感觉", "score": "65", "date": "2024-01-17"},
    ]

    from analysis.tools_registry import recommend_tools

    recommended = recommend_tools(sample_data)

    console.print(f"\n  [bold]数据特征:[/]")
    console.print(f"    - 记录数: {len(sample_data)}")
    console.print(f"    - 字段: {', '.join(sample_data[0].keys())}")
    console.print(f"    - 包含文本: ✅")
    console.print(f"    - 包含数值: ✅")
    console.print(f"    - 包含日期: ✅")

    console.print(f"\n  [bold]推荐工具:[/]")
    for tool_name in recommended:
        console.print(f"    ✅ {tool_name}")


def demo_smart_analyze():
    """演示：智能分析"""
    console.print(Panel.fit("[bold cyan]🤖 智能分析演示[/]", border_style="cyan"))

    # 示例数据
    sample_data = [
        {"content": "这个产品非常好用，强烈推荐", "score": "85"},
        {"content": "体验很差，非常失望", "score": "45"},
        {"content": "一般般，没什么感觉", "score": "65"},
        {"content": "太棒了，物超所值", "score": "95"},
        {"content": "还需要改进，不够好", "score": "55"},
    ]

    data_file = Path("demo_data.csv")

    from analysis.smart_analyzer import smart_analyze

    # 测试不同的分析需求
    queries = [
        "帮我做情感分析",
        "统计一下数据",
        "提取关键词",
    ]

    for query in queries:
        console.print(f"\n  [bold]用户查询:[/] {query}")
        result = smart_analyze(sample_data, data_file, query)

        console.print(f"  [bold]使用工具:[/] {result.tool_name}")
        console.print(f"  [bold]来源:[/] {result.source}")
        console.print(f"  [bold]成功:[/] {'✅' if result.success else '❌'}")
        console.print(f"  [bold]耗时:[/] {result.execution_time:.2f}秒")

        if result.success:
            console.print(f"  [bold]结果预览:[/]")
            # 显示结果的前几行
            result_str = str(result.result)
            for line in result_str.split('\n')[:5]:
                console.print(f"    {line}")
            if len(result_str.split('\n')) > 5:
                console.print(f"    ...")


def demo_tool_search():
    """演示：工具搜索"""
    console.print(Panel.fit("[bold cyan]🔍 工具搜索演示[/]", border_style="cyan"))

    from analysis.tools_registry import ToolsRegistry

    search_queries = ["情感", "统计", "时间", "分类"]

    for query in search_queries:
        console.print(f"\n  [bold]搜索:[/] {query}")
        tools = ToolsRegistry.search_tools(query)

        if tools:
            for tool in tools:
                console.print(f"    ✅ {tool.name}: {tool.description[:40]}...")
        else:
            console.print(f"    ❌ 未找到匹配工具")


def main():
    """主函数"""
    console.print("[bold]Insight Agent 分析工具系统演示[/]\n")

    console.print("选择演示:")
    console.print("  1. 列出所有工具")
    console.print("  2. 根据数据推荐工具")
    console.print("  3. 智能分析演示")
    console.print("  4. 工具搜索演示")
    console.print("  5. 运行所有演示")

    choice = input("\n请选择 (1-5): ").strip()

    if choice == "1":
        demo_list_tools()
    elif choice == "2":
        demo_recommend_tools()
    elif choice == "3":
        demo_smart_analyze()
    elif choice == "4":
        demo_tool_search()
    elif choice == "5":
        demo_list_tools()
        console.print("\n" + "="*60 + "\n")
        demo_recommend_tools()
        console.print("\n" + "="*60 + "\n")
        demo_smart_analyze()
        console.print("\n" + "="*60 + "\n")
        demo_tool_search()
    else:
        console.print("[red]无效选择[/]")


if __name__ == "__main__":
    main()
