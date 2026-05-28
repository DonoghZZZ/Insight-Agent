"""
高级分析工具

1. 评论聚类分析 — 相似评论自动分组
2. 用户活跃度分析 — 谁发的评论最多、互动最高
3. 互动网络分析 — 回复关系、互动热力
"""

import re
import logging
from typing import Dict, List, Any
from collections import Counter, defaultdict
from datetime import datetime

logger = logging.getLogger(__name__)


# ==================== 评论聚类 ====================

def comment_clustering(data: List[Dict], text_field: str = None) -> Dict[str, Any]:
    """
    基于关键词重叠的简单聚类（不依赖 sklearn）

    将评论按核心关键词分组，识别重复/相似讨论
    """
    from analysis.quantitative import get_text_field
    from analysis.cache import cached_analysis

    results = {
        "model": "评论聚类分析",
        "timestamp": datetime.now().isoformat(),
        "clusters": [],
    }

    if not text_field:
        text_field = get_text_field(data)
    if not text_field:
        results["error"] = "未检测到文本字段"
        return results

    texts = [(i, str(row.get(text_field, ""))) for i, row in enumerate(data)
             if row.get(text_field) and len(str(row.get(text_field, ""))) > 5]
    if len(texts) < 3:
        results["error"] = "评论太少（<3条），无法聚类"
        return results

    try:
        import jieba
    except ImportError:
        results["error"] = "请安装 jieba: pip install jieba"
        return results

    # 提取每条评论的关键词集合
    comment_keywords = []
    for idx, text in texts:
        words = set(w for w in jieba.lcut(text) if len(w) >= 2 and not w.isdigit())
        comment_keywords.append((idx, text, words))

    # 简单聚类：基于 Jaccard 相似度
    clusters = []
    assigned = set()

    for i, (idx1, text1, words1) in enumerate(comment_keywords):
        if idx1 in assigned:
            continue
        cluster = {"members": [(idx1, text1[:100])], "keywords": words1}
        assigned.add(idx1)

        for j, (idx2, text2, words2) in enumerate(comment_keywords):
            if idx2 in assigned or j <= i:
                continue
            # Jaccard 相似度
            intersection = len(words1 & words2)
            union = len(words1 | words2)
            if union > 0 and intersection / union > 0.2:
                cluster["members"].append((idx2, text2[:100]))
                cluster["keywords"] = cluster["keywords"] & words2  # 取交集作为聚类关键词
                assigned.add(idx2)

        if len(cluster["members"]) >= 2:
            # 提取聚类标签（出现频率最高的共同关键词）
            keyword_counts = Counter()
            for _, _, words in [(idx1, text1, words1)] + [
                (m[0], m[1], comment_keywords[j][2])
                for j, (idx2, text2, words2) in enumerate(comment_keywords)
                if idx2 in assigned
            ]:
                for w in words:
                    keyword_counts[w] += 1

            top_keywords = [w for w, _ in keyword_counts.most_common(5)]
            clusters.append({
                "id": len(clusters) + 1,
                "size": len(cluster["members"]),
                "keywords": top_keywords,
                "label": " / ".join(top_keywords[:3]),
                "examples": [m[1] for m in cluster["members"][:3]],
            })

    # 按大小排序
    clusters.sort(key=lambda c: c["size"], reverse=True)
    results["clusters"] = clusters[:20]
    results["total_comments"] = len(texts)
    results["clustered_comments"] = len(assigned)
    results["noise_comments"] = len(texts) - len(assigned)

    return results


# ==================== 用户活跃度分析 ====================

def user_activity(data: List[Dict], user_field: str = None,
                  content_field: str = None) -> Dict[str, Any]:
    """
    分析用户活跃度：谁评论最多、内容最长、互动最高
    """
    results = {
        "model": "用户活跃度分析",
        "timestamp": datetime.now().isoformat(),
    }

    # 自动检测用户字段
    if not user_field:
        for candidate in ['昵称', 'name', '用户', 'user', '作者', 'author', '买家']:
            for row in data[:5]:
                if candidate in str(row.keys()):
                    user_field = candidate
                    break
            if user_field:
                break

    if not user_field:
        results["error"] = "未检测到用户/昵称字段"
        return results

    # 自动检测内容字段
    if not content_field:
        from analysis.quantitative import get_text_field
        content_field = get_text_field(data)

    # 统计每个用户
    user_stats = defaultdict(lambda: {
        "count": 0, "total_length": 0, "max_length": 0,
        "contents": [], "likes_total": 0,
    })

    like_field = None
    for candidate in ['点赞', 'likes', 'like', '赞', '评论点赞']:
        for row in data[:5]:
            if candidate in str(row.keys()):
                like_field = candidate
                break
        if like_field:
            break

    for row in data:
        user = str(row.get(user_field, "")).strip()
        if not user or user in ('', 'None', 'null'):
            continue

        content = str(row.get(content_field, "")) if content_field else ""
        likes = 0
        if like_field:
            try:
                likes = int(float(str(row.get(like_field, 0))))
            except (ValueError, TypeError):
                pass

        stats = user_stats[user]
        stats["count"] += 1
        stats["total_length"] += len(content)
        stats["max_length"] = max(stats["max_length"], len(content))
        stats["likes_total"] += likes
        if len(stats["contents"]) < 3:
            stats["contents"].append(content[:80])

    # 排序
    top_commenters = sorted(user_stats.items(), key=lambda x: x[1]["count"], reverse=True)
    top_liked = sorted(user_stats.items(), key=lambda x: x[1]["likes_total"], reverse=True)

    results["total_users"] = len(user_stats)
    results["total_comments"] = len(data)
    results["top_commenters"] = [
        {
            "user": user,
            "comment_count": stats["count"],
            "avg_length": round(stats["total_length"] / max(stats["count"], 1)),
            "likes_total": stats["likes_total"],
            "examples": stats["contents"],
        }
        for user, stats in top_commenters[:15]
    ]
    results["top_liked_users"] = [
        {"user": user, "likes_total": stats["likes_total"], "comment_count": stats["count"]}
        for user, stats in top_liked[:10]
        if stats["likes_total"] > 0
    ]

    # 活跃度分布
    count_dist = Counter()
    for _, stats in user_stats.items():
        c = stats["count"]
        if c == 1:
            count_dist["1条"] += 1
        elif c <= 3:
            count_dist["2-3条"] += 1
        elif c <= 10:
            count_dist["4-10条"] += 1
        else:
            count_dist["10条以上"] += 1

    results["activity_distribution"] = dict(count_dist)

    return results


# ==================== 互动网络分析 ====================

def interaction_network(data: List[Dict],
                        user_field: str = None,
                        reply_field: str = None) -> Dict[str, Any]:
    """
    分析评论中的回复关系网络

    识别：谁回复了谁、互动密集用户、孤立用户
    """
    results = {
        "model": "互动网络分析",
        "timestamp": datetime.now().isoformat(),
    }

    # 自动检测字段
    if not user_field:
        for candidate in ['昵称', 'name', '用户', 'user']:
            for row in data[:5]:
                if candidate in str(row.keys()):
                    user_field = candidate
                    break
            if user_field:
                break

    if not reply_field:
        for candidate in ['回复', 'reply_to', '回复给', 'replyTo']:
            for row in data[:5]:
                if candidate in str(row.keys()):
                    reply_field = candidate
                    break
            if reply_field:
                break

    # 有些爬虫把回复关系写在评论内容里："回复 xxx: 内容"
    content_field = None
    from analysis.quantitative import get_text_field
    content_field = get_text_field(data)

    # 提取回复关系
    edges = defaultdict(int)  # (回复者, 被回复者) → 次数
    user_reply_count = defaultdict(int)

    for row in data:
        user = str(row.get(user_field, "")).strip() if user_field else ""
        if not user:
            continue

        reply_to = ""

        # 方式1：从专用字段读取
        if reply_field:
            reply_to = str(row.get(reply_field, "")).strip()

        # 方式2：从内容中提取 "回复 xxx:"
        if not reply_to and content_field:
            content = str(row.get(content_field, ""))
            m = re.match(r'回复\s*(.+?)[:：]', content)
            if m:
                reply_to = m.group(1).strip()

        if reply_to and reply_to != user:
            edges[(user, reply_to)] += 1
            user_reply_count[user] += 1

    if not edges:
        results["edges"] = []
        results["note"] = "未检测到回复关系（评论中可能没有子评论/回复）"
        return results

    # 统计
    results["total_edges"] = len(edges)
    results["total_reply_count"] = sum(edges.values())

    # 最活跃的回复关系
    top_edges = sorted(edges.items(), key=lambda x: x[1], reverse=True)[:20]
    results["top_edges"] = [
        {"from": e[0], "to": e[1], "count": c}
        for (e, c) in top_edges
    ]

    # 最活跃的回复者
    top_repliers = sorted(user_reply_count.items(), key=lambda x: x[1], reverse=True)[:10]
    results["top_repliers"] = [
        {"user": u, "reply_count": c} for u, c in top_repliers
    ]

    # 被回复最多的人
    reply_target_count = defaultdict(int)
    for (_, target), count in edges.items():
        reply_target_count[target] += count
    top_targets = sorted(reply_target_count.items(), key=lambda x: x[1], reverse=True)[:10]
    results["most_replied"] = [
        {"user": u, "received_replies": c} for u, c in top_targets
    ]

    return results
