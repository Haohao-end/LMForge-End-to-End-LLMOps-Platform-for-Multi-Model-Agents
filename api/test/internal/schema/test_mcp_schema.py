from __future__ import annotations

from internal.schema.mcp_schema import CreateMcpProviderReq, UpdateMcpProviderReq


def _validate_form(form_request, form_cls, *, data=None):
    with form_request(data=data):
        form = form_cls(meta={"csrf": False})
        return form.validate(), form


def test_create_mcp_provider_req_should_allow_public_http_url(form_request):
    ok, form = _validate_form(
        form_request,
        CreateMcpProviderReq,
        data={
            "name": "weather",
            "label": "weather",
            "description": "weather api",
            "transport": "streamable_http",
            "url": "https://mcp.example.com",
        },
    )

    assert ok, form.errors


def test_create_mcp_provider_req_should_reject_private_http_url(form_request):
    ok, form = _validate_form(
        form_request,
        CreateMcpProviderReq,
        data={
            "name": "weather",
            "label": "weather",
            "description": "weather api",
            "transport": "streamable_http",
            "url": "http://127.0.0.1",
        },
    )

    assert not ok
    assert "url" in form.errors


def test_create_mcp_provider_req_should_reject_private_hostname(form_request):
    ok, form = _validate_form(
        form_request,
        CreateMcpProviderReq,
        data={
            "name": "weather",
            "label": "weather",
            "description": "weather api",
            "transport": "http",
            "url": "https://private.example.com",
        },
    )

    assert not ok
    assert "url" in form.errors


def test_create_mcp_provider_req_should_allow_stdio_without_url(form_request):
    ok, form = _validate_form(
        form_request,
        CreateMcpProviderReq,
        data={
            "name": "local-tool",
            "label": "local-tool",
            "description": "stdio tool",
            "transport": "stdio",
            "url": "",
        },
    )

    assert ok, form.errors


def test_update_mcp_provider_req_should_inherit_url_validation(form_request):
    ok, form = _validate_form(
        form_request,
        UpdateMcpProviderReq,
        data={
            "name": "weather",
            "label": "weather",
            "description": "weather api",
            "transport": "streamable_http",
            "url": "http://169.254.169.254/latest/meta-data/",
        },
    )

    assert not ok
    assert "url" in form.errors
