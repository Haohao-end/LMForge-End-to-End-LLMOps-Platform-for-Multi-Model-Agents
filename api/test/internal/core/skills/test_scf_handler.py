from __future__ import annotations

import json

from internal.core.skills.scf_handler import main_handler


def _decode(response: dict) -> dict:
    assert response["statusCode"] == 200
    return json.loads(response["body"])


def test_scf_handler_should_execute_code_payload():
    response = main_handler(
        {
            "body": {
                "action": "execute_skill",
                "code": "def analyze_request(params):\n    return {'summary': params['request']}\n",
                "func_name": "analyze_request",
                "args": [{"request": "hello"}],
                "kwargs": {},
            }
        },
        None,
    )

    assert _decode(response)["result"] == {"summary": "hello"}


def test_scf_handler_should_allow_imports_for_code_analysis():
    response = main_handler(
        {
            "body": {
                "action": "execute_skill",
                "code": (
                    "from pathlib import Path\n\n"
                    "def analyze_request(params):\n"
                    "    path = Path(params['path'])\n"
                    "    return {'suffix': path.suffix, 'name': path.name}\n"
                ),
                "func_name": "analyze_request",
                "args": [{"path": "app/src/views/SkillPage.vue"}],
                "kwargs": {},
            }
        },
        None,
    )

    decoded = _decode(response)
    assert decoded["result"] == {"suffix": ".vue", "name": "SkillPage.vue"}


def test_scf_handler_should_allow_future_import_and_class_definition():
    response = main_handler(
        {
            "body": {
                "action": "execute_skill",
                "code": (
                    "from __future__ import annotations\n\n"
                    "class Box:\n"
                    "    def __init__(self, value):\n"
                    "        self.value = value\n\n"
                    "class Child(Box):\n"
                    "    def __init__(self, value):\n"
                    "        super().__init__(value)\n\n"
                    "def analyze_request(params):\n"
                    "    box = Child(params['request'])\n"
                    "    return {'summary': box.value}\n"
                ),
                "func_name": "analyze_request",
                "args": [{"request": "hello"}],
                "kwargs": {},
            }
        },
        None,
    )

    assert _decode(response)["result"] == {"summary": "hello"}


def test_scf_handler_should_support_sync_package_without_explicit_code():
    response = main_handler(
        {
            "body": {
                "action": "sync_package",
                "skill": {"source_key": "code_workbench"},
                "version": {"version": 1},
            }
        },
        None,
    )

    decoded = _decode(response)
    assert decoded["result"]["synced"] is True
    assert decoded["result"]["source_key"] == "code_workbench"
