"""高级分析模块测试"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from analysis.advanced import comment_clustering, user_activity, interaction_network


class TestCommentClustering:
    """评论聚类测试"""

    def test_basic_clustering(self):
        data = [
            {"content": "人工智能技术发展很快"},
            {"content": "人工智能改变生活"},
            {"content": "今天天气真好"},
            {"content": "天气好出去玩"},
            {"content": "AI人工智能未来"},
        ]
        result = comment_clustering(data)
        assert "clusters" in result
        assert "total_comments" in result

    def test_too_few_comments(self):
        data = [{"content": "hello"}]
        result = comment_clustering(data)
        assert "error" in result

    def test_empty_data(self):
        result = comment_clustering([])
        assert "error" in result


class TestUserActivity:
    """用户活跃度测试"""

    def test_basic_user_activity(self):
        data = [
            {"昵称": "user1", "content": "hello"},
            {"昵称": "user1", "content": "world"},
            {"昵称": "user2", "content": "foo"},
        ]
        result = user_activity(data)
        assert "total_users" in result
        assert result["total_users"] == 2
        assert "top_commenters" in result

    def test_no_user_field(self):
        data = [{"content": "hello", "score": "85"}]
        result = user_activity(data)
        assert "error" in result

    def test_empty_data(self):
        result = user_activity([])
        assert "error" in result


class TestInteractionNetwork:
    """互动网络测试"""

    def test_basic_network(self):
        data = [
            {"昵称": "A", "content": "hello"},
            {"昵称": "B", "content": "回复 A: hi"},
        ]
        result = interaction_network(data)
        assert "total_edges" in result

    def test_no_replies(self):
        data = [
            {"昵称": "A", "content": "hello"},
            {"昵称": "B", "content": "world"},
        ]
        result = interaction_network(data)
        assert "note" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
