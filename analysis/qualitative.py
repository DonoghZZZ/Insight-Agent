"""定性分析模型 - 基于 LLM + 智能字段检测"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
from analysis.quantitative import get_text_field, auto_detect_fields


def _get_llm_client():
    """获取 LLM 客户端"""
    from openai import OpenAI
    return OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)


def _call_llm(system_prompt: str, user_prompt: str, max_tokens: int = 2048) -> str:
    """调用 LLM"""
    client = _get_llm_client()
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=max_tokens,
        temperature=0.3,
    )
    return response.choices[0].message.content


def _parse_json_response(response: str) -> dict:
    """安全解析 LLM JSON 响应"""
    json_match = response
    if "```json" in response:
        json_match = response.split("```json")[1].split("```")[0]
    elif "```" in response:
        parts = response.split("```")
        if len(parts) >= 2:
            json_match = parts[1]
    try:
        return json.loads(json_match.strip())
    except json.JSONDecodeError:
        return {}


def theme_extraction(data: List[Dict], text_field: str = None) -> Dict[str, Any]:
    """主题提取"""
    results = {
        "model": "主题提取",
        "timestamp": datetime.now().isoformat(),
        "themes": [],
    }

    if not text_field:
        text_field = get_text_field(data)

    if not text_field:
        results["error"] = "未检测到文本字段，无法提取主题"
        return results

    if not data:
        results["error"] = "无数据"
        return results

    results["text_field"] = text_field

    sample_size = min(50, len(data))
    texts = [
        str(row.get(text_field, ""))[:500]
        for row in data[:sample_size] if row.get(text_field)
    ]
    if not texts:
        results["error"] = "文本字段为空"
        return results

    combined = "\n---\n".join(f"[{i+1}] {t}" for i, t in enumerate(texts))

    system_prompt = """你是一个质性研究分析专家。从以下文本数据中提取核心主题。
输出JSON格式：{"themes": [{"name": "主题名", "description": "简要描述", "sub_themes": ["子主题"], "example_quotes": ["引文"]}]}
提取3-8个主题，主题之间要互斥、有区分度。用中文输出。"""
    user_prompt = f"请分析以下文本，提取核心主题：\n\n{combined[:8000]}"

    try:
        response = _call_llm(system_prompt, user_prompt)
        parsed = _parse_json_response(response)
        results["themes"] = parsed.get("themes", [])
    except Exception as e:
        results["error"] = f"LLM调用失败: {e}"

    return results


def content_category(data: List[Dict], text_field: str = None) -> Dict[str, Any]:
    """内容分类"""
    results = {
        "model": "内容分类",
        "timestamp": datetime.now().isoformat(),
        "categories": [],
        "distribution": {},
    }

    if not text_field:
        text_field = get_text_field(data)

    if not text_field:
        results["error"] = "未检测到文本字段"
        return results

    if not data:
        results["error"] = "无数据"
        return results

    results["text_field"] = text_field

    sample_size = min(30, len(data))
    texts = [
        str(row.get(text_field, ""))[:300]
        for row in data[:sample_size] if row.get(text_field)
    ]
    if not texts:
        results["error"] = "文本字段为空"
        return results

    combined = "\n---\n".join(f"[{i+1}] {t}" for i, t in enumerate(texts))

    system_prompt = """你是内容分析专家。分析以下内容，提出5-8个分类，将每条内容归类。
输出JSON：{"categories": ["类别名"], "distribution": {"类别名": 数量}}。用中文。"""
    user_prompt = f"请对以下内容进行分类：\n\n{combined[:6000]}"

    try:
        response = _call_llm(system_prompt, user_prompt)
        parsed = _parse_json_response(response)
        results["categories"] = parsed.get("categories", [])
        results["distribution"] = parsed.get("distribution", {})
    except Exception as e:
        results["error"] = f"LLM调用失败: {e}"

    return results


def insight_mining(data: List[Dict], text_field: str = None) -> Dict[str, Any]:
    """观点挖掘"""
    results = {
        "model": "观点挖掘",
        "timestamp": datetime.now().isoformat(),
        "insights": [],
    }

    if not text_field:
        text_field = get_text_field(data)

    if not text_field:
        results["error"] = "未检测到文本字段"
        return results

    if not data:
        results["error"] = "无数据"
        return results

    results["text_field"] = text_field

    sample_size = min(40, len(data))
    texts = [
        str(row.get(text_field, ""))[:500]
        for row in data[:sample_size] if row.get(text_field)
    ]
    if not texts:
        results["error"] = "文本字段为空"
        return results

    combined = "\n---\n".join(f"[{i+1}] {t}" for i, t in enumerate(texts))

    system_prompt = """你是深度分析专家。从数据中提取：用户态度、反复出现的问题、建设性建议、隐含需求。
输出JSON：{"insights": [{"type": "态度/问题/建议/需求", "content": "描述", "evidence": "原文证据", "significance": "高/中/低"}]}
用中文。"""
    user_prompt = f"请挖掘以下数据中的关键观点：\n\n{combined[:8000]}"

    try:
        response = _call_llm(system_prompt, user_prompt)
        parsed = _parse_json_response(response)
        results["insights"] = parsed.get("insights", [])
    except Exception as e:
        results["error"] = f"LLM调用失败: {e}"

    return results


def run_qualitative(data: List[Dict], models: List[str], data_file: Path) -> Dict[str, Any]:
    """运行选定的定性分析模型"""
    all_results = {}

    for model in models:
        try:
            if model == "theme_extraction":
                all_results["theme_extraction"] = theme_extraction(data)
            elif model == "content_category":
                all_results["content_category"] = content_category(data)
            elif model == "insight_mining":
                all_results["insight_mining"] = insight_mining(data)
        except Exception as e:
            all_results[model] = {"model": model, "error": str(e)}

    return all_results
