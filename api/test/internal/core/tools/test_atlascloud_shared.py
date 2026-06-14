from __future__ import annotations

import json

from internal.core.tools.builtin_tools.providers.atlascloud_shared import (
    submit_generation_task,
    wait_for_prediction,
)


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload
        self.text = json.dumps(payload, ensure_ascii=False)

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_atlascloud_shared_should_use_safe_http_client_for_model_requests(monkeypatch):
    calls = []

    def _fake_safe_request(method, url, **kwargs):
        calls.append(
            {
                "method": method,
                "url": url,
                "headers": kwargs.get("headers"),
                "json": kwargs.get("json"),
                "timeout": kwargs.get("timeout"),
            }
        )

        if method == "POST":
            return _FakeResponse({"code": 0, "data": {"predictionId": "pred-1"}})

        return _FakeResponse(
            {
                "status": "completed",
                "outputs": [{"url": "https://example.com/output.png"}],
            }
        )

    monkeypatch.setenv("ATLASCLOUD_API_KEY", "token")
    monkeypatch.setenv("ATLASCLOUD_MODEL_API_BASE", "https://api.atlascloud.ai/api/v1/model")
    monkeypatch.setattr(
        "internal.core.tools.builtin_tools.providers.atlascloud_shared.safe_request",
        _fake_safe_request,
    )

    prediction_id = submit_generation_task("/image", {"prompt": "a cat"}, timeout_seconds=10)
    outputs = wait_for_prediction(prediction_id, timeout_seconds=1, poll_interval_seconds=0)

    assert prediction_id == "pred-1"
    assert outputs == ["https://example.com/output.png"]
    assert [call["method"] for call in calls] == ["POST", "GET"]
    assert calls[0]["url"] == "https://api.atlascloud.ai/api/v1/model/image"
    assert calls[0]["headers"]["Authorization"] == "Bearer token"
    assert calls[0]["json"] == {"prompt": "a cat"}
    assert calls[0]["timeout"] == 10
