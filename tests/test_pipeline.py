"""流水线模块测试"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline import Pipeline, PipelineStep


class TestPipelineStep:
    """流水线步骤测试"""

    def test_default_status(self):
        step = PipelineStep(name="test", func="test_fn")
        assert step.status == "pending"
        assert step.duration == 0
        assert step.error == ""

    def test_custom_args(self):
        step = PipelineStep(name="test", func="crawl", args={"key": "value"})
        assert step.args["key"] == "value"


class TestPipeline:
    """流水线测试"""

    def test_add_steps(self):
        pipe = Pipeline()
        pipe.add_crawl("test", {"url": "http://example.com"})
        pipe.add_clean()
        pipe.add_analyze(["basic_stats", "sentiment"])
        pipe.add_report()
        pipe.add_export_pdf()
        assert len(pipe.steps) == 5
        assert pipe.steps[0].func == "crawl"
        assert pipe.steps[1].func == "clean"
        assert pipe.steps[2].func == "analyze"
        assert pipe.steps[3].func == "report"
        assert pipe.steps[4].func == "export_pdf"

    def test_chain_calls(self):
        pipe = Pipeline()
        result = pipe.add_crawl("test").add_clean().add_analyze(["basic_stats"]).add_report()
        assert result is pipe
        assert len(pipe.steps) == 4

    def test_analyze_with_template(self):
        pipe = Pipeline()
        pipe.add_analyze([], template="quick_scan")
        # quick_scan 模板应该填充 models
        assert len(pipe.steps[0].args["models"]) > 0

    def test_empty_pipeline(self):
        pipe = Pipeline()
        assert len(pipe.steps) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
