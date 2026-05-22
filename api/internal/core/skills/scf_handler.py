from __future__ import annotations

import json
import traceback
from typing import Any

_REAL_IMPORT = __import__
_ALLOWED_IMPORTS = {
    "__future__",
    "collections",
    "contextlib",
    "datetime",
    "hashlib",
    "html",
    "importlib",
    "io",
    "json",
    "os",
    "pathlib",
    "re",
    "shlex",
    "tempfile",
    "textwrap",
    "traceback",
    "typing",
    "urllib",
}


def _safe_import(name, globals=None, locals=None, fromlist=(), level=0):
    root_name = str(name or "").split(".", 1)[0]
    if root_name not in _ALLOWED_IMPORTS:
        raise ImportError(f"Import {name!r} is not allowed")
    return _REAL_IMPORT(name, globals, locals, fromlist, level)


def _safe_builtins() -> dict[str, Any]:
    return {
        "__build_class__": __build_class__,
        "__import__": _safe_import,
        "abs": abs,
        "all": all,
        "any": any,
        "AttributeError": AttributeError,
        "BaseException": BaseException,
        "callable": callable,
        "classmethod": classmethod,
        "bool": bool,
        "dict": dict,
        "enumerate": enumerate,
        "Exception": Exception,
        "float": float,
        "getattr": getattr,
        "hasattr": hasattr,
        "int": int,
        "ImportError": ImportError,
        "IndexError": IndexError,
        "isinstance": isinstance,
        "issubclass": issubclass,
        "len": len,
        "list": list,
        "KeyError": KeyError,
        "max": max,
        "min": min,
        "open": open,
        "object": object,
        "NotImplementedError": NotImplementedError,
        "print": print,
        "range": range,
        "property": property,
        "RuntimeError": RuntimeError,
        "setattr": setattr,
        "set": set,
        "sorted": sorted,
        "staticmethod": staticmethod,
        "str": str,
        "sum": sum,
        "super": super,
        "TypeError": TypeError,
        "type": type,
        "tuple": tuple,
        "ValueError": ValueError,
        "vars": vars,
        "zip": zip,
    }


def _load_body(event: dict[str, Any]) -> dict[str, Any]:
    body_raw = event.get("body", {})
    if isinstance(body_raw, str):
        if not body_raw.strip():
            return {}
        return json.loads(body_raw)
    if isinstance(body_raw, dict):
        return body_raw
    return {}


def _build_default_sync_code(payload: dict[str, Any]) -> str:
    source_key = str(payload.get("source_key") or payload.get("skill", {}).get("source_key") or "").strip()
    version = payload.get("version")
    return (
        "def sync_package(payload):\n"
        "    return {\n"
        f"        'synced': True,\n"
        f"        'source_key': {source_key!r},\n"
        f"        'version': {version!r},\n"
        "    }\n"
    )


def main_handler(event, context):
    try:
        body = _load_body(event if isinstance(event, dict) else {})
        action = str(body.get("action") or "").strip()
        code = str(body.get("code") or "").strip()
        func_name = str(body.get("func_name") or "").strip()
        args = body.get("args", [])
        kwargs = body.get("kwargs", {})

        if not code and action == "sync_package":
            code = _build_default_sync_code(body)
            func_name = func_name or "sync_package"
            if not args:
                args = [body.get("skill") or body]

        if not code:
            return {
                "statusCode": 200,
                "body": json.dumps(
                    {
                        "error": "Missing code",
                    },
                    ensure_ascii=False,
                ),
            }

        if not func_name:
            return {
                "statusCode": 200,
                "body": json.dumps(
                    {
                        "error": "Missing func_name",
                    },
                    ensure_ascii=False,
                ),
            }

        if not isinstance(args, list):
            args = [args]
        if not isinstance(kwargs, dict):
            kwargs = {}

        exec_globals: dict[str, Any] = {
            "__builtins__": _safe_builtins(),
            "__name__": "__scf_handler__",
        }
        exec(code, exec_globals, exec_globals)

        if func_name in exec_globals and callable(exec_globals[func_name]):
            result = exec_globals[func_name](*args, **kwargs)
            return {
                "statusCode": 200,
                "body": json.dumps(
                    {
                        "result": result,
                    },
                    ensure_ascii=False,
                    default=str,
                ),
            }

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "error": "Function not found or not callable",
                },
                ensure_ascii=False,
            ),
        }
    except Exception as exc:
        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "error": str(exc),
                    "traceback": traceback.format_exc(),
                },
                ensure_ascii=False,
                default=str,
            ),
        }
