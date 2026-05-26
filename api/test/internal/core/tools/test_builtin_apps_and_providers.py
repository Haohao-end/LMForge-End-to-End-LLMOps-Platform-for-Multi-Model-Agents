import asyncio
import importlib
import json

import pytest
from langchain_core.tools import StructuredTool

from internal.exception import FailException
from internal.core.tools.builtin_tools.providers.dalle.dalle3 import Dalle3ArgsSchema, dalle3
from internal.core.tools.builtin_tools.providers.atlascloud_video.atlascloud_seedance_2_0 import (
    atlascloud_seedance_2_0_text_to_video,
)
from internal.core.tools.builtin_tools.providers.duckduckgo.duckduckgo_search import DDGInput, duckduckgo_search
from internal.core.tools.builtin_tools.providers.gaode.gaode_weather import GaodeWeatherTool, gaode_weather
from internal.core.tools.builtin_tools.providers.google.google_serper import (
    GoogleSerperArgsSchema,
    google_serper,
)
from internal.core.tools.builtin_tools.providers.qwen.qwen_image_text_to_image import _generate_image
from internal.core.tools.builtin_tools.providers.time.current_time import CurrentTimeTool, current_time
from internal.core.tools.builtin_tools.providers.time.timezone_converter import timezone_converter
from internal.core.tools.builtin_tools.providers.wikipedia.wikipedia_search import wikipedia_search


def test_gaode_weather_tool_should_cover_success_failure_and_exception(monkeypatch):
    gaode_module = importlib.import_module("internal.core.tools.builtin_tools.providers.gaode.gaode_weather")

    class _FakeResponse:
        def __init__(self, payload, should_raise=False):
            self._payload = payload
            self._should_raise = should_raise

        def raise_for_status(self):
            if self._should_raise:
                raise RuntimeError("boom")

        def json(self):
            return self._payload

    class _FakeSession:
        def __init__(self, responses):
            self.responses = responses
            self.calls = []

        def request(self, **kwargs):
            self.calls.append(kwargs)
            return self.responses.pop(0)

    tool = GaodeWeatherTool()

    monkeypatch.delenv("GAODE_API_KEY", raising=False)
    assert tool._run(city="广州") == "高德开放平台API未配置"

    monkeypatch.setenv("GAODE_API_KEY", "token")
    success_session = _FakeSession(
        [
            _FakeResponse({"info": "OK", "districts": [{"adcode": "440100"}]}),
            _FakeResponse({"info": "OK", "forecasts": [{"date": "2026-02-26"}]}),
        ]
    )
    monkeypatch.setattr(gaode_module.requests, "session", lambda: success_session)
    success = tool._run(city="广州")
    assert json.loads(success)["info"] == "OK"
    assert len(success_session.calls) == 2
    assert success_session.calls[0]["timeout"] == 10
    assert success_session.calls[1]["timeout"] == 10

    failure_session = _FakeSession([_FakeResponse({"info": "FAIL"})])
    monkeypatch.setattr(gaode_module.requests, "session", lambda: failure_session)
    assert tool._run(city="深圳") == "获取深圳天气预报信息失败：行政区查询失败"

    # 覆盖 city 成功但 weather 接口返回非 OK 的分支。
    weather_fail_session = _FakeSession(
        [
            _FakeResponse({"info": "OK", "districts": [{"adcode": "440300"}]}),
            _FakeResponse({"info": "FAIL"}),
        ]
    )
    monkeypatch.setattr(gaode_module.requests, "session", lambda: weather_fail_session)
    assert tool._run(city="深圳") == "获取深圳天气预报信息失败：天气接口返回异常"

    exception_session = _FakeSession([_FakeResponse({}, should_raise=True)])
    monkeypatch.setattr(gaode_module.requests, "session", lambda: exception_session)
    assert tool._run(city="北京") == "获取北京天气预报信息失败：RuntimeError"


def test_gaode_weather_tool_should_cover_timeout_and_missing_city(monkeypatch):
    gaode_module = importlib.import_module("internal.core.tools.builtin_tools.providers.gaode.gaode_weather")
    tool = GaodeWeatherTool()

    assert tool._run(city="") == "获取天气预报信息失败：缺少城市参数"

    class _TimeoutSession:
        def request(self, **kwargs):
            raise gaode_module.requests.Timeout("timeout")

        def close(self):
            return None

    monkeypatch.setenv("GAODE_API_KEY", "token")
    monkeypatch.setattr(gaode_module.requests, "session", lambda: _TimeoutSession())
    assert tool._run(city="上海") == "获取上海天气预报信息失败：请求超时"


def test_current_time_tool_and_factory_should_work():
    tool = CurrentTimeTool()
    result = tool._run()
    # 固定断言到前 19 位，避免时区字符串在不同环境下表现不一致。
    assert len(result[:19]) == 19
    assert result[4] == "-" and result[7] == "-"
    assert asyncio.run(tool._arun())[:19] == result[:19]
    assert isinstance(current_time(), CurrentTimeTool)


def test_builtin_tool_factories_should_construct_wrapped_tools(monkeypatch):
    google_module = importlib.import_module("internal.core.tools.builtin_tools.providers.google.google_serper")
    ddg_module = importlib.import_module("internal.core.tools.builtin_tools.providers.duckduckgo.duckduckgo_search")
    wiki_module = importlib.import_module("internal.core.tools.builtin_tools.providers.wikipedia.wikipedia_search")
    dalle_module = importlib.import_module("internal.core.tools.builtin_tools.providers.dalle.dalle3")
    captured = {}

    class _FakeGoogleWrapper:
        pass

    class _FakeGoogleRun:
        def __init__(self, **kwargs):
            captured["google"] = kwargs

    class _FakeDDGRun:
        def __init__(self, **kwargs):
            captured["ddg"] = kwargs

    class _FakeWikipediaWrapper:
        pass

    class _FakeWikipediaRun:
        def __init__(self, **kwargs):
            captured["wiki"] = kwargs

    class _FakeDalleWrapper:
        def __init__(self, **kwargs):
            captured["dalle_wrapper"] = kwargs

    class _FakeDalleTool:
        def __init__(self, **kwargs):
            captured["dalle_tool"] = kwargs

    monkeypatch.setattr(google_module, "GoogleSerperAPIWrapper", _FakeGoogleWrapper)
    monkeypatch.setattr(google_module, "GoogleSerperRun", _FakeGoogleRun)
    monkeypatch.setattr(ddg_module, "DuckDuckGoSearchRun", _FakeDDGRun)
    monkeypatch.setattr(wiki_module, "WikipediaAPIWrapper", _FakeWikipediaWrapper)
    monkeypatch.setattr(wiki_module, "WikipediaQueryRun", _FakeWikipediaRun)
    monkeypatch.setattr(dalle_module, "DallEAPIWrapper", _FakeDalleWrapper)
    monkeypatch.setattr(dalle_module, "OpenAIDALLEImageGenerationTool", _FakeDalleTool)

    google_serper()
    duckduckgo_search()
    wikipedia_search()
    dalle3(size="1024x1024")

    assert captured["google"]["args_schema"] is GoogleSerperArgsSchema
    assert captured["ddg"]["args_schema"] is DDGInput
    assert isinstance(captured["wiki"]["api_wrapper"], _FakeWikipediaWrapper)
    assert captured["dalle_wrapper"]["model"] == "dall-e-3"
    assert captured["dalle_wrapper"]["size"] == "1024x1024"
    assert captured["dalle_tool"]["args_schema"] is Dalle3ArgsSchema


def test_gaode_weather_factory_should_return_tool_instance():
    assert isinstance(gaode_weather(), GaodeWeatherTool)


def test_qwen_image_tool_should_persist_generated_image_url(monkeypatch):
    qwen_module = importlib.import_module("internal.core.tools.builtin_tools.providers.qwen.qwen_image_text_to_image")
    captured = {}

    class _PostResponse:
        @staticmethod
        def raise_for_status():
            return None

        @staticmethod
        def json():
            return {
                "images": [{"url": "https://temporary.example.com/output.png?token=1"}],
                "timings": {"inference": 12},
                "seed": 7,
            }

    monkeypatch.setenv("SILICONFLOW_API_KEY", "token")
    monkeypatch.setattr(qwen_module.requests, "post", lambda *args, **kwargs: _PostResponse())
    monkeypatch.setattr(
        qwen_module,
        "persist_remote_image",
        lambda image_url, source: captured.update({"url": image_url, "source": source}) or "https://cos.example.com/generated.png",
    )

    result = _generate_image("上海初夏旅行穿搭")

    assert captured["url"].startswith("https://temporary.example.com/output.png")
    assert captured["source"] == "qwen-image"
    assert "https://cos.example.com/generated.png" in result
    assert "图片已持久化保存" in result


def test_qwen_image_tool_should_raise_when_persistence_failed(monkeypatch):
    qwen_module = importlib.import_module("internal.core.tools.builtin_tools.providers.qwen.qwen_image_text_to_image")

    class _PostResponse:
        @staticmethod
        def raise_for_status():
            return None

        @staticmethod
        def json():
            return {
                "images": [{"url": "https://temporary.example.com/output.png?token=1"}],
            }

    monkeypatch.setenv("SILICONFLOW_API_KEY", "token")
    monkeypatch.setattr(qwen_module.requests, "post", lambda *args, **kwargs: _PostResponse())
    monkeypatch.setattr(
        qwen_module,
        "persist_remote_image",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("cos down")),
    )

    with pytest.raises(FailException, match="生成图像时出错|图像生成失败"):
        _generate_image("上海初夏旅行穿搭")


def test_multivariate_builtin_tools_should_accept_dict_invocation(monkeypatch):
    atlascloud_module = importlib.import_module(
        "internal.core.tools.builtin_tools.providers.atlascloud_video.atlascloud_seedance_2_0"
    )
    captured = {}

    monkeypatch.setattr(
        atlascloud_module,
        "submit_generation_task",
        lambda endpoint, payload, **_kwargs: captured.update(
            {"endpoint": endpoint, "payload": payload}
        )
        or "prediction-1",
    )
    monkeypatch.setattr(
        atlascloud_module,
        "wait_for_prediction",
        lambda prediction_id, **_kwargs: captured.update({"prediction_id": prediction_id})
        or ["https://temporary.example.com/video.mp4"],
    )
    monkeypatch.setattr(
        atlascloud_module,
        "persist_remote_video",
        lambda video_url, source: captured.update(
            {"video_url": video_url, "source": source}
        )
        or "https://cos.example.com/video.mp4",
    )

    atlascloud_tool = atlascloud_seedance_2_0_text_to_video()
    timezone_tool = timezone_converter()

    assert isinstance(atlascloud_tool, StructuredTool)
    assert isinstance(timezone_tool, StructuredTool)

    atlascloud_result = atlascloud_tool.invoke(
        {
            "prompt": "盗梦空间风格，城市街道像纸片一样折叠翻转，梦境与现实交织，旋转的陀螺，高楼大厦倒挂在天空中，深邃的梦境层次，电影感光影，史诗级视觉特效，超现实场景",
            "width": 1024,
            "height": 576,
            "duration": 5,
            "fps": 24,
        }
    )
    timezone_result = timezone_tool.invoke(
        {
            "time_str": "2026-05-25 08:00:00",
            "from_timezone": "Asia/Shanghai",
            "to_timezone": "UTC",
        }
    )

    assert captured["endpoint"] == "generateVideo"
    assert captured["payload"]["model"] == "bytedance/seedance-2.0/text-to-video"
    assert captured["payload"]["width"] == 1024
    assert captured["payload"]["height"] == 576
    assert captured["payload"]["duration"] == 5
    assert captured["payload"]["fps"] == 24
    assert "✓ 成功生成视频" in atlascloud_result
    assert "模型: bytedance/seedance-2.0/text-to-video" in atlascloud_result
    assert "https://cos.example.com/video.mp4" in atlascloud_result
    assert "原时间：2026-05-25 08:00:00 (Asia/Shanghai)" in timezone_result
    assert "转换后：2026-05-25 00:00:00 (UTC)" in timezone_result


def test_multivariate_builtin_tools_should_merge_factory_and_runtime_kwargs(monkeypatch):
    atlascloud_module = importlib.import_module(
        "internal.core.tools.builtin_tools.providers.atlascloud_video.atlascloud_seedance_2_0"
    )
    captured = {}

    monkeypatch.setattr(
        atlascloud_module,
        "submit_generation_task",
        lambda endpoint, payload, **_kwargs: captured.update(
            {"endpoint": endpoint, "payload": payload}
        )
        or "prediction-2",
    )
    monkeypatch.setattr(
        atlascloud_module,
        "wait_for_prediction",
        lambda prediction_id, **_kwargs: captured.update({"prediction_id": prediction_id})
        or ["https://temporary.example.com/video-2.mp4"],
    )
    monkeypatch.setattr(
        atlascloud_module,
        "persist_remote_video",
        lambda video_url, source: captured.update(
            {"video_url": video_url, "source": source}
        )
        or "https://cos.example.com/video-2.mp4",
    )

    atlascloud_tool = atlascloud_seedance_2_0_text_to_video(
        width=640,
        height=640,
        duration=7,
        fps=30,
    )
    atlascloud_result = atlascloud_tool.invoke(
        {
            "prompt": "盗梦空间风格，城市街道像纸片一样折叠翻转，梦境与现实交织，旋转的陀螺，高楼大厦倒挂在天空中，深邃的梦境层次，电影感光影，史诗级视觉特效，超现实场景",
            "width": 1024,
            "height": 576,
            "duration": 5,
            "fps": 24,
        }
    )

    assert captured["endpoint"] == "generateVideo"
    assert captured["payload"]["model"] == "bytedance/seedance-2.0/text-to-video"
    assert captured["payload"]["width"] == 1024
    assert captured["payload"]["height"] == 576
    assert captured["payload"]["duration"] == 5
    assert captured["payload"]["fps"] == 24
    assert "✓ 成功生成视频" in atlascloud_result
    assert "https://cos.example.com/video-2.mp4" in atlascloud_result
