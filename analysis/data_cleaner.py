"""
数据清洗管道

对爬虫输出的原始数据进行标准化处理：
- 去除 HTML 标签和特殊字符
- 数值格式统一（"1.2万" → 12000, "3.5w" → 35000）
- 去重
- 空值处理
- 字段标准化
"""

import re
import html
from typing import List, Dict, Any, Optional
from collections import Counter
from datetime import datetime


# ========== 文本清洗 ==========

def clean_text(text: str) -> str:
    """清洗单条文本：去 HTML、去特殊字符、规范化空白"""
    if not text or not isinstance(text, str):
        return ""

    # 解码 HTML 实体（&amp; → &）
    text = html.unescape(text)

    # 去除 HTML 标签
    text = re.sub(r'<[^>]+>', '', text)

    # 去除零宽字符、控制字符
    text = re.sub(r'[​‌‍﻿\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)

    # "作者赞过" 等平台标记
    text = re.sub(r'作者赞过', '', text)

    # 规范化空白
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


# ========== 数值解析 ==========

_CN_UNITS = {
    '万': 10_000, 'w': 10_000, 'W': 10_000,
    '亿': 100_000_000,
    '千': 1_000, 'k': 1_000, 'K': 1_000,
}

def parse_number(value) -> Optional[float]:
    """
    解析各种数值格式：
      "1.2万" → 12000
      "3.5w"  → 35000
      "2亿"   → 200000000
      "1,234" → 1234
      "85%"   → 85
      "约100" → 100
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)

    s = str(value).strip()
    if not s or s in ('-', '--', 'N/A', 'n/a', '无', 'null', 'None'):
        return None

    # 去除前缀文字（"约"、"近"、"超过"）
    s = re.sub(r'^[约近超大约]+', '', s)

    # 百分比
    m = re.match(r'^([\d.]+)\s*%$', s)
    if m:
        return float(m.group(1))

    # 带中文单位（"1.2万"）
    for unit, multiplier in _CN_UNITS.items():
        if unit in s:
            num_part = s.replace(unit, '').strip()
            try:
                return float(num_part) * multiplier
            except ValueError:
                continue

    # 逗号分隔数字（"1,234,567"）
    s_clean = s.replace(',', '').replace('，', '')
    try:
        return float(s_clean)
    except ValueError:
        pass

    # 提取第一个数字
    m = re.search(r'[\d.]+', s)
    if m:
        try:
            return float(m.group())
        except ValueError:
            pass

    return None


def normalize_number(value) -> Any:
    """解析数值，整数则返回 int，否则返回 float，失败返回原值"""
    result = parse_number(value)
    if result is None:
        return value
    return int(result) if result == int(result) else result


# ========== 日期解析 ==========

_DATE_PATTERNS = [
    (r'(\d{4})-(\d{1,2})-(\d{1,2})\s+(\d{1,2}):(\d{1,2})(?::(\d{1,2}))?', '%Y-%m-%d %H:%M:%S'),
    (r'(\d{4})-(\d{1,2})-(\d{1,2})', '%Y-%m-%d'),
    (r'(\d{4})\.(\d{1,2})\.(\d{1,2})', '%Y.%m.%d'),
    (r'(\d{4})年(\d{1,2})月(\d{1,2})日', '%Y年%m月%d日'),
    (r'(\d{4})/(\d{1,2})/(\d{1,2})', '%Y/%m/%d'),
]


def normalize_date(value: str) -> str:
    """统一日期格式为 YYYY-MM-DD"""
    if not value or not isinstance(value, str):
        return str(value) if value else ""

    s = value.strip()

    # 已经是标准格式
    if re.match(r'^\d{4}-\d{2}-\d{2}$', s):
        return s

    # 相对时间（"3天前"、"1小时前"）
    relative_map = {'刚刚': 0, '昨天': 1}
    for word, days in relative_map.items():
        if word in s:
            from datetime import timedelta
            d = datetime.now() - timedelta(days=days)
            return d.strftime('%Y-%m-%d')

    m = re.match(r'(\d+)\s*(分钟|小时|天|周|月)前', s)
    if m:
        from datetime import timedelta
        num = int(m.group(1))
        unit = m.group(2)
        unit_map = {'分钟': 'minutes', '小时': 'hours', '天': 'days', '周': 'weeks'}
        if unit in unit_map:
            d = datetime.now() - timedelta(**{unit_map[unit]: num})
            return d.strftime('%Y-%m-%d')

    # 尝试各种格式
    for pattern, fmt in _DATE_PATTERNS:
        match = re.search(pattern, s)
        if match:
            try:
                # 构造完整的日期字符串
                groups = match.groups()
                date_str = match.group()
                for f in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%Y.%m.%d', '%Y年%m月%d日', '%Y/%m/%d']:
                    try:
                        dt = datetime.strptime(date_str, f)
                        return dt.strftime('%Y-%m-%d')
                    except ValueError:
                        continue
            except (ValueError, IndexError):
                continue

    return s


# ========== 去重 ==========

def deduplicate(data: List[Dict], key_fields: Optional[List[str]] = None,
                content_field: Optional[str] = None) -> List[Dict]:
    """
    去重

    Args:
        data: 原始数据列表
        key_fields: 用于去重的字段列表（精确匹配）
        content_field: 内容字段（模糊去重，取前 50 字符）
    """
    if not data:
        return []

    seen = set()
    result = []

    for row in data:
        # 构建去重 key
        if key_fields:
            key = tuple(str(row.get(f, '')) for f in key_fields)
        elif content_field:
            name = str(row.get(content_field, ''))[:50]
            # 也用第一个字段（通常是昵称）做辅助
            first_field = list(row.keys())[0] if row else ''
            key = (str(row.get(first_field, ''))[:20], name)
        else:
            # 自动选择：用前两个字段的前 50 字符
            keys = list(row.keys())[:2]
            key = tuple(str(row.get(f, ''))[:50] for f in keys)

        if key not in seen:
            seen.add(key)
            result.append(row)

    return result


# ========== 字段标准化 ==========

# 自动检测需要转数值的字段名
_NUMERIC_FIELD_HINTS = [
    '点赞', 'like', '赞', '评论数', 'reply', '评论', '收藏', 'fav',
    '转发', 'share', '播放', 'view', '播放量', '粉丝', 'follower',
    '弹幕', 'danmaku', '投币', 'coin', '评分', 'score', '评分人数',
    '浏览', '销量', '价格', 'price', '数量', 'count', '图片数',
]

_DATE_FIELD_HINTS = [
    '时间', 'time', 'date', '日期', '发布', 'publish', '创建',
]


def auto_clean_fields(data: List[Dict]) -> List[Dict]:
    """
    自动检测字段类型并标准化：
    - 含 "点赞/评论/收藏" 等关键词的字段 → 转数值
    - 含 "时间/日期" 等关键词的字段 → 统一日期格式
    - 文本字段 → 清洗 HTML 和特殊字符
    """
    if not data:
        return []

    cleaned = []
    for row in data:
        new_row = {}
        for key, value in row.items():
            key_lower = key.lower()

            # 数值字段
            if any(hint in key_lower for hint in _NUMERIC_FIELD_HINTS):
                new_row[key] = normalize_number(value)
            # 日期字段
            elif any(hint in key_lower for hint in _DATE_FIELD_HINTS):
                new_row[key] = normalize_date(str(value)) if value else ""
            # 文本字段
            elif isinstance(value, str) and len(value) > 10:
                new_row[key] = clean_text(value)
            else:
                new_row[key] = value

        cleaned.append(new_row)

    return cleaned


# ========== 完整清洗管道 ==========

def clean_data(data: List[Dict],
               key_fields: Optional[List[str]] = None,
               content_field: Optional[str] = None,
               do_dedup: bool = True) -> Dict[str, Any]:
    """
    完整的数据清洗管道

    Args:
        data: 原始数据
        key_fields: 去重字段
        content_field: 内容字段（用于模糊去重）
        do_dedup: 是否去重

    Returns:
        {
            "data": 清洗后的数据,
            "stats": {
                "original_count": 原始条数,
                "cleaned_count": 清洗后条数,
                "removed_duplicates": 去重数量,
                "fields_cleaned": 清洗的字段数,
            }
        }
    """
    original_count = len(data)

    # Step 1: 字段标准化
    cleaned = auto_clean_fields(data)
    fields_cleaned = len(cleaned[0]) if cleaned else 0

    # Step 2: 去重
    if do_dedup:
        cleaned = deduplicate(cleaned, key_fields=key_fields, content_field=content_field)

    removed = original_count - len(cleaned)

    return {
        "data": cleaned,
        "stats": {
            "original_count": original_count,
            "cleaned_count": len(cleaned),
            "removed_duplicates": removed,
            "fields_cleaned": fields_cleaned,
            "cleaned_at": datetime.now().isoformat(),
        }
    }


def clean_and_report(data: List[Dict], **kwargs) -> List[Dict]:
    """清洗数据并打印统计信息，返回清洗后的数据"""
    result = clean_data(data, **kwargs)
    stats = result["stats"]

    print(f"\n  🧹 数据清洗完成:")
    print(f"     原始: {stats['original_count']} 条")
    print(f"     清洗后: {stats['cleaned_count']} 条")
    if stats['removed_duplicates'] > 0:
        print(f"     去重: -{stats['removed_duplicates']} 条")

    return result["data"]
