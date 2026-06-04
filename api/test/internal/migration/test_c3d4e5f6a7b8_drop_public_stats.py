from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_module():
    module_path = (
        Path(__file__).resolve().parents[3]
        / "internal"
        / "migration"
        / "versions"
        / "c3d4e5f6a7b8_drop_public_stats.py"
    )
    spec = importlib.util.spec_from_file_location("c3d4e5f6a7b8_drop_public_stats", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _FakeInspector:
    def __init__(self, tables: set[str], columns_by_table: dict[str, list[str]]):
        self._tables = tables
        self._columns_by_table = columns_by_table

    def has_table(self, table_name: str) -> bool:
        return table_name in self._tables

    def get_columns(self, table_name: str):
        return [{"name": column_name} for column_name in self._columns_by_table.get(table_name, [])]


class _FakeOp:
    def __init__(self):
        self.calls = []
        self._bind = object()

    def get_bind(self):
        return self._bind

    def drop_table(self, table_name, if_exists=False):
        self.calls.append(("drop_table", table_name, if_exists))

    def drop_index(self, index_name, table_name=None, if_exists=None):
        self.calls.append(("drop_index", index_name, table_name, if_exists))

    def drop_column(self, table_name, column_name):
        self.calls.append(("drop_column", table_name, column_name))


def test_upgrade_should_skip_missing_like_count_index_and_drop_existing_public_stats(monkeypatch):
    module = _load_module()
    fake_op = _FakeOp()
    fake_inspector = _FakeInspector(
        tables={"workflow", "app", "workflow_like", "workflow_favorite", "app_like", "app_favorite"},
        columns_by_table={
            "workflow": ["fork_count", "like_count", "view_count"],
            "app": ["fork_count", "like_count", "view_count"],
        },
    )

    monkeypatch.setattr(module, "op", fake_op)
    monkeypatch.setattr(module.sa, "inspect", lambda _bind: fake_inspector)

    module.upgrade()

    assert fake_op.calls == [
        ("drop_table", "workflow_favorite", True),
        ("drop_table", "workflow_like", True),
        ("drop_table", "app_favorite", True),
        ("drop_table", "app_like", True),
        ("drop_index", "workflow_like_count_idx", "workflow", True),
        ("drop_column", "workflow", "fork_count"),
        ("drop_column", "workflow", "like_count"),
        ("drop_column", "workflow", "view_count"),
        ("drop_index", "app_like_count_idx", "app", True),
        ("drop_column", "app", "fork_count"),
        ("drop_column", "app", "like_count"),
        ("drop_column", "app", "view_count"),
    ]


def test_upgrade_should_skip_missing_workflow_columns(monkeypatch):
    module = _load_module()
    fake_op = _FakeOp()
    fake_inspector = _FakeInspector(
        tables={"workflow", "app"},
        columns_by_table={
            "workflow": ["view_count"],
            "app": ["fork_count", "like_count", "view_count"],
        },
    )

    monkeypatch.setattr(module, "op", fake_op)
    monkeypatch.setattr(module.sa, "inspect", lambda _bind: fake_inspector)

    module.upgrade()

    assert ("drop_column", "workflow", "view_count") in fake_op.calls
    assert ("drop_column", "workflow", "fork_count") not in fake_op.calls
    assert ("drop_column", "workflow", "like_count") not in fake_op.calls
