"""报告生成模块 - 生成HTML分析报告 + PDF导出"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

from config import REPORT_DIR

logger = logging.getLogger(__name__)


def export_pdf(html_path: Path, pdf_path: Path = None) -> Path:
    """
    将 HTML 报告导出为 PDF

    优先使用 weasyprint（效果最好），
    备选 playwright（无额外依赖，但需要浏览器）
    """
    if pdf_path is None:
        pdf_path = html_path.with_suffix('.pdf')

    html_content = html_path.read_text(encoding='utf-8')

    # 方式1: weasyprint（推荐）
    try:
        from weasyprint import HTML
        HTML(string=html_content, base_url=str(html_path.parent)).write_pdf(str(pdf_path))
        logger.info(f"PDF 导出成功 (weasyprint): {pdf_path}")
        return pdf_path
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"weasyprint 导出失败: {e}")

    # 方式2: playwright
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_content(html_content, wait_until="networkidle")
            page.pdf(path=str(pdf_path), format="A4", margin={"top": "20mm", "bottom": "20mm"})
            browser.close()
        logger.info(f"PDF 导出成功 (playwright): {pdf_path}")
        return pdf_path
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"playwright 导出失败: {e}")

    # 方式3: 提示安装
    logger.warning(
        "PDF 导出需要安装 weasyprint 或 playwright:\n"
        "  pip install weasyprint\n"
        "  或: pip install playwright && playwright install chromium"
    )
    return None


def generate_report(
    crawler_info: dict,
    analysis_results: Dict[str, Any],
    data_file: Path,
    output_dir: Path,
) -> Path:
    """生成完整的HTML分析报告"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORT_DIR / f"analysis_report_{timestamp}.html"

    html = _build_html(crawler_info, analysis_results, data_file, output_dir)
    report_path.write_text(html, encoding="utf-8")

    # 同时保存JSON格式便于后续AI问答
    json_path = REPORT_DIR / f"analysis_data_{timestamp}.json"
    report_data = {
        "crawler": crawler_info,
        "analysis": analysis_results,
        "data_file": str(data_file),
        "generated_at": datetime.now().isoformat(),
    }
    json_path.write_text(json.dumps(report_data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    return report_path


def _build_html(crawler_info: dict, results: Dict, data_file: Path, output_dir: Path) -> str:
    """构建HTML报告"""
    title = f"{crawler_info['name']} - 数据分析报告"

    sections = []

    # 概览
    overview = f"""
    <div class="section">
        <h2>📊 报告概览</h2>
        <table class="overview-table">
            <tr><td>数据平台</td><td>{crawler_info['platform']}</td></tr>
            <tr><td>爬虫脚本</td><td>{crawler_info['name']}</td></tr>
            <tr><td>数据文件</td><td>{data_file.name}</td></tr>
            <tr><td>生成时间</td><td>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</td></tr>
            <tr><td>分析模型数</td><td>{len(results)} 个</td></tr>
        </table>
    </div>
    """
    sections.append(overview)

    # 逐一渲染每个分析结果
    for model_key, model_result in results.items():
        section_html = _render_model_section(model_key, model_result)
        sections.append(section_html)

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f7fa; color: #333; line-height: 1.6; }}
        .header {{ background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%); color: white; padding: 40px 20px; text-align: center; }}
        .header h1 {{ font-size: 28px; margin-bottom: 8px; }}
        .header p {{ opacity: 0.8; font-size: 14px; }}
        .container {{ max-width: 1000px; margin: 0 auto; padding: 20px; }}
        .section {{ background: white; border-radius: 12px; padding: 24px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
        .section h2 {{ color: #1a1a2e; margin-bottom: 16px; font-size: 20px; border-bottom: 2px solid #e8ecf1; padding-bottom: 8px; }}
        .section h3 {{ color: #0f3460; margin: 16px 0 8px; font-size: 16px; }}
        .overview-table {{ width: 100%; border-collapse: collapse; }}
        .overview-table td {{ padding: 10px 16px; border-bottom: 1px solid #eee; }}
        .overview-table td:first-child {{ font-weight: 600; color: #666; width: 150px; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin: 16px 0; }}
        .stat-card {{ background: #f8f9fc; border-radius: 8px; padding: 16px; text-align: center; border: 1px solid #e8ecf1; }}
        .stat-card .value {{ font-size: 28px; font-weight: 700; color: #0f3460; }}
        .stat-card .label {{ font-size: 12px; color: #888; margin-top: 4px; }}
        .emotion-bar {{ display: flex; height: 30px; border-radius: 6px; overflow: hidden; margin: 12px 0; }}
        .emotion-bar .pos {{ background: #4CAF50; }}
        .emotion-bar .neu {{ background: #FF9800; }}
        .emotion-bar .neg {{ background: #f44336; }}
        .emotion-legend {{ display: flex; gap: 20px; margin-top: 8px; }}
        .emotion-legend span {{ display: flex; align-items: center; gap: 6px; font-size: 13px; }}
        .emotion-legend .dot {{ width: 12px; height: 12px; border-radius: 50%; display: inline-block; }}
        table.data-table {{ width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 13px; }}
        table.data-table th {{ background: #f0f2f5; padding: 10px 12px; text-align: left; font-weight: 600; }}
        table.data-table td {{ padding: 8px 12px; border-bottom: 1px solid #eee; }}
        .theme-card {{ background: #f8f9fc; border-left: 4px solid #0f3460; padding: 16px; margin: 12px 0; border-radius: 0 8px 8px 0; }}
        .theme-card .theme-name {{ font-size: 16px; font-weight: 600; color: #0f3460; }}
        .theme-card .sub-themes {{ margin-top: 8px; }}
        .theme-card .sub-themes span {{ display: inline-block; background: #e3e8f0; padding: 2px 10px; border-radius: 12px; font-size: 12px; margin: 2px 4px; }}
        .insight-card {{ background: #fff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 16px; margin: 10px 0; }}
        .insight-card .tag {{ display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; margin-right: 8px; }}
        .tag-attitude {{ background: #e3f2fd; color: #1565c0; }}
        .tag-problem {{ background: #fce4ec; color: #c62828; }}
        .tag-suggestion {{ background: #e8f5e9; color: #2e7d32; }}
        .tag-need {{ background: #fff3e0; color: #e65100; }}
        .chart-container {{ width: 100%; max-width: 600px; margin: 20px auto; }}
        .keyword-cloud {{ display: flex; flex-wrap: wrap; gap: 8px; padding: 16px; }}
        .keyword-tag {{ padding: 4px 14px; border-radius: 16px; font-size: 13px; }}
        .footer {{ text-align: center; padding: 20px; color: #999; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{title}</h1>
        <p>Nankai University · Data Analysis Agent · Powered by DeepSeek</p>
    </div>
    <div class="container">
        {''.join(sections)}
    </div>
    <div class="footer">
        <p>报告由 Insight Agent 自动生成 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
</body>
</html>
"""
    return html


def _render_model_section(key: str, result: Dict) -> str:
    """渲染单个分析模型的报告段落"""
    model_name = result.get("model", key)

    if "error" in result:
        return f"""
        <div class="section">
            <h2>⚠️ {model_name}</h2>
            <p style="color:#e65100;font-size:14px;">{result['error']}</p>
            <p style="color:#888;font-size:12px;">提示：请确认数据文件包含有效的文本/数值/日期字段。</p>
        </div>"""

    if key == "basic_stats":
        return _render_basic_stats(model_name, result)
    elif key == "sentiment":
        return _render_sentiment(model_name, result)
    elif key == "word_freq":
        return _render_word_freq(model_name, result)
    elif key == "time_series":
        return _render_time_series(model_name, result)
    elif key == "theme_extraction":
        return _render_themes(model_name, result)
    elif key == "content_category":
        return _render_categories(model_name, result)
    elif key == "insight_mining":
        return _render_insights(model_name, result)
    elif key == "comment_clustering":
        return _render_clusters(model_name, result)
    elif key == "user_activity":
        return _render_user_activity(model_name, result)
    elif key == "interaction_network":
        return _render_network(model_name, result)

    return f'<div class="section"><h2>{model_name}</h2><pre>{json.dumps(result, ensure_ascii=False, indent=2, default=str)[:2000]}</pre></div>'


def _render_basic_stats(name: str, result: Dict) -> str:
    html = f'<div class="section"><h2>📈 {name}</h2>'
    html += f'<div class="stats-grid"><div class="stat-card"><div class="value">{result.get("record_count", 0)}</div><div class="label">总记录数</div></div></div>'

    for field, info in result.get("fields", {}).items():
        html += f'<h3>字段: {field}</h3>'
        if info.get("type") == "numeric":
            html += f'<div class="stats-grid">'
            for k in ["min", "max", "mean", "median"]:
                if k in info:
                    html += f'<div class="stat-card"><div class="value">{round(info[k], 2)}</div><div class="label">{k}</div></div>'
            html += '</div>'
        elif info.get("type") == "text":
            html += f'<p>非空值: {info.get("non_null", 0)} | 唯一值: {info.get("unique_count", 0)}</p>'
            if info.get("top_values"):
                html += '<table class="data-table"><tr><th>值</th><th>出现次数</th></tr>'
                for val, cnt in info["top_values"][:10]:
                    html += f'<tr><td>{val[:80]}</td><td>{cnt}</td></tr>'
                html += '</table>'

    html += '</div>'
    return html


def _render_sentiment(name: str, result: Dict) -> str:
    pos_pct = result.get("positive_pct", 0)
    neu_pct = result.get("neutral_pct", 0)
    neg_pct = result.get("negative_pct", 0)
    total = result.get("total", 1)

    html = f"""
    <div class="section">
        <h2>💬 {name}</h2>
        <div class="stats-grid">
            <div class="stat-card"><div class="value">{total}</div><div class="label">分析条数</div></div>
            <div class="stat-card"><div class="value">{result.get('avg_score', 0)}</div><div class="label">平均情感分</div></div>
            <div class="stat-card"><div class="value" style="color:#4CAF50;">{result.get('positive', 0)}</div><div class="label">正面</div></div>
            <div class="stat-card"><div class="value" style="color:#f44336;">{result.get('negative', 0)}</div><div class="label">负面</div></div>
        </div>
        <div class="emotion-bar">
            <div class="pos" style="width:{pos_pct}%"></div>
            <div class="neu" style="width:{neu_pct}%"></div>
            <div class="neg" style="width:{neg_pct}%"></div>
        </div>
        <div class="emotion-legend">
            <span><span class="dot" style="background:#4CAF50;"></span>正面 {pos_pct}%</span>
            <span><span class="dot" style="background:#FF9800;"></span>中性 {neu_pct}%</span>
            <span><span class="dot" style="background:#f44336;"></span>负面 {neg_pct}%</span>
        </div>
    </div>"""
    return html


def _render_word_freq(name: str, result: Dict) -> str:
    html = f'<div class="section"><h2>🔤 {name}</h2>'

    keywords = result.get("keywords", [])
    if keywords:
        html += '<h3>TF-IDF 关键词</h3><div class="keyword-cloud">'
        for item in keywords[:20]:
            size = min(20, max(10, int(item.get("weight", 1) * 15)))
            color = f"hsl({220 + (item.get('weight', 0.5) * 80):.0f}, 60%, 50%)"
            html += f'<span class="keyword-tag" style="font-size:{size}px;background:{color};color:white;">{item["word"]}</span>'
        html += '</div>'

    top_words = result.get("top_words", [])
    if top_words:
        html += '<h3>高频词汇 (Top 30)</h3><table class="data-table"><tr><th>词汇</th><th>频次</th></tr>'
        for word, cnt in top_words[:30]:
            html += f'<tr><td>{word}</td><td>{cnt}</td></tr>'
        html += '</table>'

    html += '</div>'
    return html


def _render_time_series(name: str, result: Dict) -> str:
    time_data = result.get("time_data", [])
    html = f'<div class="section"><h2>📅 {name}</h2>'

    if time_data:
        labels = json.dumps([d["date"] for d in time_data])
        values = json.dumps([d["count"] for d in time_data])

        html += f"""
        <div class="chart-container">
            <canvas id="timeChart"></canvas>
        </div>
        <table class="data-table"><tr><th>日期</th><th>数量</th></tr>"""
        for d in time_data[-20:]:
            html += f'<tr><td>{d["date"]}</td><td>{d["count"]}</td></tr>'
        html += '</table>'

        html += f"""
        <script>
        new Chart(document.getElementById('timeChart'), {{
            type: 'line',
            data: {{
                labels: {labels},
                datasets: [{{
                    label: '数据量',
                    data: {values},
                    borderColor: '#0f3460',
                    backgroundColor: 'rgba(15, 52, 96, 0.1)',
                    fill: true,
                    tension: 0.3,
                }}]
            }},
            options: {{ responsive: true, plugins: {{ legend: {{ display: false }} }} }}
        }});
        </script>"""

    html += '</div>'
    return html


def _render_themes(name: str, result: Dict) -> str:
    html = f'<div class="section"><h2>🏷️ {name}</h2>'
    for theme in result.get("themes", []):
        html += f"""
        <div class="theme-card">
            <div class="theme-name">{theme.get('name', '')}</div>
            <p>{theme.get('description', '')}</p>"""
        if theme.get("sub_themes"):
            html += '<div class="sub-themes">'
            for st in theme["sub_themes"]:
                html += f'<span>{st}</span>'
            html += '</div>'
        if theme.get("example_quotes"):
            html += '<p style="margin-top:8px;color:#888;font-size:12px;">📌 ' + "<br>📌 ".join(theme["example_quotes"][:2]) + '</p>'
        html += '</div>'
    html += '</div>'
    return html


def _render_categories(name: str, result: Dict) -> str:
    html = f'<div class="section"><h2>📂 {name}</h2>'

    categories = result.get("categories", [])
    distribution = result.get("distribution", {})

    if categories:
        html += '<h3>分类类别</h3><ul>'
        for cat in categories:
            html += f'<li>{cat}</li>'
        html += '</ul>'

    if distribution:
        labels = json.dumps(list(distribution.keys()))
        values = json.dumps(list(distribution.values()))
        html += f"""
        <div class="chart-container">
            <canvas id="catChart"></canvas>
        </div>
        <script>
        new Chart(document.getElementById('catChart'), {{
            type: 'doughnut',
            data: {{
                labels: {labels},
                datasets: [{{
                    data: {values},
                    backgroundColor: ['#0f3460','#16213e','#1a1a2e','#e94560','#533483','#3498db','#2ecc71','#f39c12'],
                }}]
            }},
            options: {{ responsive: true }}
        }});
        </script>"""

    html += '</div>'
    return html


def _render_insights(name: str, result: Dict) -> str:
    html = f'<div class="section"><h2>💡 {name}</h2>'
    for insight in result.get("insights", []):
        tag_class = f"tag-{insight.get('type', 'attitude')}"
        tag_map = {"态度": "tag-attitude", "问题": "tag-problem", "建议": "tag-suggestion", "需求": "tag-need"}
        tag_class = tag_map.get(insight.get("type", ""), "tag-attitude")

        html += f"""
        <div class="insight-card">
            <span class="tag {tag_class}">{insight.get('type', '')}</span>
            <span style="color:#888;font-size:12px;">重要度: {insight.get('significance', '中')}</span>
            <p style="margin-top:8px;">{insight.get('content', '')}</p>
            <p style="color:#888;font-size:12px;">📌 {insight.get('evidence', '')}</p>
        </div>"""
    html += '</div>'
    return html


def _render_clusters(name: str, result: Dict) -> str:
    """渲染评论聚类分析"""
    html = f'<div class="section"><h2>🧩 {name}</h2>'

    total = result.get('total_comments', 0)
    clustered = result.get('clustered_comments', 0)
    noise = result.get('noise_comments', 0)

    html += f"""
    <div class="stats-grid">
        <div class="stat-card"><div class="value">{total}</div><div class="label">总评论数</div></div>
        <div class="stat-card"><div class="value">{clustered}</div><div class="label">已聚类</div></div>
        <div class="stat-card"><div class="value">{noise}</div><div class="label">独立评论</div></div>
        <div class="stat-card"><div class="value">{len(result.get('clusters', []))}</div><div class="label">聚类数</div></div>
    </div>"""

    for cluster in result.get("clusters", [])[:10]:
        keywords = " / ".join(cluster.get("keywords", [])[:5])
        html += f"""
        <div class="theme-card">
            <div class="theme-name">聚类 #{cluster['id']}: {cluster.get('label', '')} ({cluster['size']}条)</div>
            <div class="sub-themes">"""
        for kw in cluster.get("keywords", []):
            html += f'<span>{kw}</span>'
        html += "</div>"
        for ex in cluster.get("examples", []):
            html += f'<p style="margin-top:4px;color:#666;font-size:12px;">💬 {ex}</p>'
        html += "</div>"

    html += '</div>'
    return html


def _render_user_activity(name: str, result: Dict) -> str:
    """渲染用户活跃度分析"""
    html = f'<div class="section"><h2>👥 {name}</h2>'

    html += f"""
    <div class="stats-grid">
        <div class="stat-card"><div class="value">{result.get('total_users', 0)}</div><div class="label">用户数</div></div>
        <div class="stat-card"><div class="value">{result.get('total_comments', 0)}</div><div class="label">总评论数</div></div>
    </div>"""

    # 活跃度分布图
    dist = result.get("activity_distribution", {})
    if dist:
        labels = json.dumps(list(dist.keys()))
        values = json.dumps(list(dist.values()))
        html += f"""
        <div class="chart-container">
            <canvas id="activityChart"></canvas>
        </div>
        <script>
        new Chart(document.getElementById('activityChart'), {{
            type: 'pie',
            data: {{
                labels: {labels},
                datasets: [{{ data: {values}, backgroundColor: ['#4CAF50','#FF9800','#2196F3','#f44336'] }}]
            }},
            options: {{ responsive: true, plugins: {{ title: {{ display: true, text: '用户活跃度分布' }} }} }}
        }});
        </script>"""

    # Top 评论者
    top = result.get("top_commenters", [])
    if top:
        html += '<h3>🏆 最活跃用户</h3><table class="data-table"><tr><th>用户</th><th>评论数</th><th>平均长度</th><th>获赞</th></tr>'
        for u in top[:10]:
            html += f'<tr><td>{u["user"]}</td><td>{u["comment_count"]}</td><td>{u["avg_length"]}</td><td>{u["likes_total"]}</td></tr>'
        html += '</table>'

    html += '</div>'
    return html


def _render_network(name: str, result: Dict) -> str:
    """渲染互动网络分析"""
    html = f'<div class="section"><h2>🔗 {name}</h2>'

    if result.get("note"):
        html += f'<p style="color:#888;">{result["note"]}</p>'
        html += '</div>'
        return html

    html += f"""
    <div class="stats-grid">
        <div class="stat-card"><div class="value">{result.get('total_edges', 0)}</div><div class="label">回复关系数</div></div>
        <div class="stat-card"><div class="value">{result.get('total_reply_count', 0)}</div><div class="label">总回复次数</div></div>
    </div>"""

    # 最活跃回复关系
    top_edges = result.get("top_edges", [])
    if top_edges:
        html += '<h3>🔗 最频繁回复关系</h3><table class="data-table"><tr><th>回复者</th><th>被回复者</th><th>次数</th></tr>'
        for e in top_edges[:10]:
            html += f'<tr><td>{e["from"]}</td><td>{e["to"]}</td><td>{e["count"]}</td></tr>'
        html += '</table>'

    # 最活跃回复者
    top_repliers = result.get("top_repliers", [])
    if top_repliers:
        html += '<h3>💬 最活跃回复者</h3><table class="data-table"><tr><th>用户</th><th>回复次数</th></tr>'
        for r in top_repliers[:10]:
            html += f'<tr><td>{r["user"]}</td><td>{r["reply_count"]}</td></tr>'
        html += '</table>'

    # 被回复最多
    most_replied = result.get("most_replied", [])
    if most_replied:
        html += '<h3>🎯 被回复最多的用户</h3><table class="data-table"><tr><th>用户</th><th>收到回复</th></tr>'
        for r in most_replied[:10]:
            html += f'<tr><td>{r["user"]}</td><td>{r["received_replies"]}</td></tr>'
        html += '</table>'

    html += '</div>'
    return html
