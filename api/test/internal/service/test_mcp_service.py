from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from sqlalchemy.exc import ProgrammingError

from internal.exception import NotFoundException
from internal.service.mcp_service import McpService


@contextmanager
def _null_context():
    yield


def _field(value):
    return SimpleNamespace(data=value)


def _req(*, current_page=1, page_size=20, search_word="", category=""):
    return SimpleNamespace(
        current_page=_field(current_page),
        page_size=_field(page_size),
        search_word=_field(search_word),
        category=_field(category),
    )


def _build_catalog_provider(
    *,
    name="weather_gateway",
    label="天气 MCP",
    description="提供天气查询",
    icon="",
    background="#DBEAFE",
    category="productivity",
    transport="streamable_http",
    url="https://mcp.example.com",
    command="",
    headers=None,
    tool_names=None,
    args=None,
    env=None,
    timeout_seconds=30,
    source_type="catalog",
    source_key="@modelscope/weather_gateway",
    source_url="https://www.modelscope.cn/mcp/servers/@modelscope/weather_gateway",
    created_at=1744848000,
    is_public=True,
):
    return SimpleNamespace(
        name=name,
        provider_entity=SimpleNamespace(
            name=name,
            label=label,
            description=description,
            icon=icon,
            background=background,
            category=category,
            transport=transport,
            url=url,
            command=command,
            headers=list(headers or []),
            tool_names=list(tool_names or []),
            args=list(args or []),
            env=dict(env or {}),
            timeout_seconds=timeout_seconds,
            source_type=source_type,
            source_key=source_key,
            source_url=source_url,
            created_at=created_at,
            is_public=is_public,
        ),
    )


def _build_service(*, table_exists: bool, catalog_providers=None):
    catalog_providers = list(catalog_providers or [_build_catalog_provider()])
    provider_map = {provider.name: provider for provider in catalog_providers}
    db = SimpleNamespace(
        session=SimpleNamespace(
            query=lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("unexpected db query")),
        ),
        auto_commit=_null_context,
    )
    service = McpService(
        db=db,
        mcp_provider_manager=SimpleNamespace(
            get_providers=lambda: catalog_providers,
            get_provider=lambda provider_name: provider_map.get(provider_name),
        ),
        icon_generator_service=SimpleNamespace(generate_icon=lambda *_args, **_kwargs: "icon"),
    )
    service._has_mcp_provider_table = lambda: table_exists  # type: ignore[method-assign]
    return service


class _Query:
    def __init__(
        self,
        *,
        one_or_none_result=None,
        all_result=None,
        scalar_result=None,
        count_result=0,
    ):
        self._one_or_none_result = one_or_none_result
        self._all_result = all_result if all_result is not None else []
        self._scalar_result = scalar_result
        self._count_result = count_result
        self.c = SimpleNamespace(app_id="app_id")
        self.filter_args = ()
        self.order_by_args = ()

    def filter(self, *args, **_kwargs):
        self.filter_args = args
        return self

    def join(self, *_args, **_kwargs):
        return self

    def outerjoin(self, *_args, **_kwargs):
        return self

    def order_by(self, *args, **_kwargs):
        self.order_by_args = args
        return self

    def options(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def group_by(self, *_args, **_kwargs):
        return self

    def subquery(self):
        return self

    def one_or_none(self):
        return self._one_or_none_result

    def first(self):
        return self._one_or_none_result

    def all(self):
        return self._all_result

    def scalar(self):
        return self._scalar_result

    def count(self):
        return self._count_result


def test_get_public_mcp_providers_with_page_should_fallback_to_catalog_when_table_missing():
    service = _build_service(table_exists=False)

    providers, paginator = service.get_public_mcp_providers_with_page(_req(page_size=20))

    assert len(providers) == 1
    assert providers[0]["name"] == "weather_gateway"
    assert paginator.total_record == 1
    assert paginator.total_page == 1


def test_get_mcp_providers_with_page_should_return_empty_when_table_missing():
    service = _build_service(table_exists=False)

    providers, paginator = service.get_mcp_providers_with_page(_req(page_size=20), SimpleNamespace(id="account"))

    assert providers == []
    assert paginator.total_record == 0
    assert paginator.total_page == 0


def test_get_public_mcp_providers_with_page_should_support_catalog_integer_timestamps():
    service = _build_service(table_exists=False)

    providers, paginator = service.get_public_mcp_providers_with_page(_req(page_size=20))

    assert len(providers) == 1
    assert providers[0]["published_at"] == 1744848000
    assert providers[0]["created_at"] == 1744848000
    assert paginator.total_record == 1
    assert paginator.total_page == 1


def test_get_public_mcp_providers_with_page_should_filter_out_unbindable_catalog_entries():
    visible_provider = _build_catalog_provider()
    hidden_provider = _build_catalog_provider(
        name="stdio_gateway",
        label="不可绑定 MCP",
        description="只支持 stdio，不能直接绑定",
        transport="stdio",
        url="",
        command="npx stdio-gateway",
        source_key="@modelscope/stdio_gateway",
        source_url="https://www.modelscope.cn/mcp/servers/@modelscope/stdio_gateway",
        created_at=1744849000,
    )
    service = _build_service(table_exists=False, catalog_providers=[visible_provider, hidden_provider])

    providers, paginator = service.get_public_mcp_providers_with_page(_req(page_size=20))

    assert len(providers) == 1
    assert providers[0]["name"] == visible_provider.name
    assert providers[0]["is_bindable"] is True
    assert paginator.total_record == 1
    assert paginator.total_page == 1


def test_get_public_mcp_provider_should_raise_for_unbindable_catalog_provider():
    hidden_provider = _build_catalog_provider(
        name="stdio_gateway",
        label="不可绑定 MCP",
        description="只支持 stdio，不能直接绑定",
        transport="stdio",
        url="",
        command="npx stdio-gateway",
        source_key="@modelscope/stdio_gateway",
        source_url="https://www.modelscope.cn/mcp/servers/@modelscope/stdio_gateway",
        created_at=1744849000,
    )
    service = _build_service(table_exists=False, catalog_providers=[hidden_provider])

    with pytest.raises(NotFoundException, match="MCP 不存在或未公开"):
        service.get_public_mcp_provider(hidden_provider.name)


def test_get_public_mcp_provider_should_raise_for_unbindable_public_db_provider():
    provider_id = "123e4567-e89b-12d3-a456-426614174000"
    public_provider = SimpleNamespace(
        id=provider_id,
        name="stdio_gateway",
        label="不可绑定 MCP",
        icon="",
        description="只支持 stdio，不能直接绑定",
        category="productivity",
        transport="stdio",
        url="",
        command="npx stdio-gateway",
        headers=[],
        tool_names=[],
        args=[],
        env={},
        timeout_seconds=30,
        source_type="custom",
        source_key="",
        source_url="",
        account=None,
        published_at=1744849000,
        created_at=1744849000,
        updated_at=1744849000,
        is_public=True,
    )
    service = _build_service(
        table_exists=True,
        catalog_providers=[_build_catalog_provider()],
    )
    service.db.session = SimpleNamespace(
        query=lambda *_args, **_kwargs: _Query(one_or_none_result=public_provider),
    )

    with pytest.raises(NotFoundException, match="MCP 不存在或未公开"):
        service.get_public_mcp_provider(f"db::{provider_id}")


def test_get_mcp_providers_with_page_should_return_empty_when_paginate_raises_missing_table():
    service = _build_service(table_exists=True)

    class _QueryWithMissingTable:
        def filter(self, *_args, **_kwargs):
            return self

        def order_by(self, *_args, **_kwargs):
            return self

        def paginate(self, *_args, **_kwargs):
            raise ProgrammingError("select 1", {}, SimpleNamespace(pgcode="42P01"))

    service.db.session = SimpleNamespace(query=lambda *_args, **_kwargs: _QueryWithMissingTable())

    providers, paginator = service.get_mcp_providers_with_page(_req(page_size=20), SimpleNamespace(id="account"))

    assert providers == []
    assert paginator.total_record == 0
    assert paginator.total_page == 0
