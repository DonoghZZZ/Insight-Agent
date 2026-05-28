"""分析技能模板 — 预设分析套餐，一键执行"""

SKILL_TEMPLATES = {
    "brand_audit": {
        "name": "🏷️ 品牌舆情审计",
        "description": "全套品牌分析：情感+词频+主题+观点挖掘",
        "models": ["basic_stats", "sentiment", "word_freq", "theme_extraction", "insight_mining"],
        "report_title": "品牌舆情分析报告",
        "prompt": "请对这份数据进行品牌舆情审计：\n1. 整体情感倾向如何？\n2. 高频关键词是什么？\n3. 用户主要讨论哪些话题？\n4. 有什么关键观点和建议？\n5. 品牌方应该关注什么？",
    },
    "quick_scan": {
        "name": "⚡ 快速扫描",
        "description": "基础统计+情感+词频，3分钟出结果",
        "models": ["basic_stats", "sentiment", "word_freq"],
        "report_title": "数据快速扫描报告",
        "prompt": "快速扫描这份数据：统计概览、情感分布、Top关键词。",
    },
    "deep_dive": {
        "name": "🔬 深度挖掘",
        "description": "全部7个模型+详细解读",
        "models": ["basic_stats", "sentiment", "word_freq", "time_series", "theme_extraction", "content_category", "insight_mining"],
        "report_title": "深度数据分析报告",
        "prompt": "全面深度分析：描述性统计→情感分析→词频→时序趋势→主题提取→内容分类→观点挖掘。每个维度给出详细解读和可操作建议。",
    },
    "competitor": {
        "name": "🥊 竞品对比",
        "description": "两个数据集对比分析",
        "models": ["basic_stats", "sentiment", "word_freq"],
        "report_title": "竞品对比分析报告",
        "prompt": "对比两份数据集：统计差异、情感差异、关键词差异。指出各自的优劣势。",
    },
    "trend_tracker": {
        "name": "📈 趋势追踪",
        "description": "时序分析+情感变化趋势",
        "models": ["basic_stats", "time_series", "sentiment"],
        "report_title": "趋势追踪报告",
        "prompt": "追踪数据随时间的变化：数量趋势、情感变化曲线、周期性规律。",
    },
}


def get_template(template_id: str) -> dict:
    return SKILL_TEMPLATES.get(template_id)


def list_templates() -> list:
    return [{"id": k, "name": v["name"], "desc": v["description"]} for k, v in SKILL_TEMPLATES.items()]
