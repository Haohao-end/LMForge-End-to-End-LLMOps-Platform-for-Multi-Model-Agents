"""百度云函数 CFC 沙箱后端（E2B 协议兼容）。

百度 CFC 代码沙箱实现了 E2B 协议，通过 e2b-code-interpreter SDK 接入。
每次 Agent 调用 execute() 时，会在沙箱内执行真实的 Python/Shell 命令，
并返回 stdout/stderr 输出，实现安全隔离的代码执行能力。

注意：
    upstream e2b-code-interpreter 对 API key 形态做了本地校验，只接受
    `e2b_...` 前缀。百度 CFC 使用的是 `bce-v3/...` 凭证，因此这里在
    进入 Sandbox.create() 前会针对百度 CFC 场景临时绕过该本地校验，让
    SDK 继续把请求发到兼容的远端沙箱。

环境变量（在 .env 中配置）：
    E2B_DOMAIN                 : 百度 CFC 沙箱域名，如 sandbox-execute.bj.baidubce.com
    E2B_API_KEY                : 百度 CFC API Key（BCE v3 格式）
    SANDBOX_TEMPLATE_ALIAS      : 主模板名，建议指向 2C / 2048 MiB 的低成本模板
    SANDBOX_FALLBACK_TEMPLATE_ALIAS:
                                 : 主模板失败时的备用模板名，默认回退到 code-interpreter-v1

使用示例：
    backend = BaiduCfcSandboxBackend()
    result = backend.execute("python3 -c 'print(1+1)'")
    print(result.output)  # '2'
"""
from __future__ import annotations

import logging
import os
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING

try:
    from deepagents.backends.sandbox import BaseSandbox
    from deepagents.backends.protocol import ExecuteResponse, FileDownloadResponse, FileUploadResponse
except ImportError:
    class BaseSandbox:
        """deepagents 未安装时的轻量占位基类，仅用于本地导入与单测。"""

    @dataclass
    class ExecuteResponse:
        output: str = ""
        exit_code: int = 1
        truncated: bool = False
        error: str | None = None

    @dataclass
    class FileUploadResponse:
        path: str
        error: str | None = None

    @dataclass
    class FileDownloadResponse:
        path: str
        content: bytes | None = None
        error: str | None = None

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 600  # 单次命令默认超时（秒）
_SANDBOX_LIFETIME = 1800  # 沙箱最长存活时间（秒）
_DEFAULT_FALLBACK_TEMPLATE_ALIAS = "code-interpreter-v1"


def _normalize_optional_string(value: str | None) -> str | None:
    """把空字符串和空白字符串统一规整成 None。"""
    normalized = (value or "").strip()
    return normalized or None


class BaiduCfcSandboxBackend(BaseSandbox):
    """百度云函数 CFC 代码沙箱后端。

    继承 BaseSandbox：ls / read / write / edit / grep / glob 全部通过
    execute() 调用 shell 命令实现，本类只需实现三个核心方法：
        - execute()        — 在沙箱内执行 shell 命令
        - upload_files()   — 向沙箱写入文件
        - download_files() — 从沙箱读取文件
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        domain: str | None = None,
        template_alias: str | None = None,
        fallback_template_alias: str | None = None,
        timeout: int = _DEFAULT_TIMEOUT,
        sandbox_timeout: int = _SANDBOX_LIFETIME,
    ) -> None:
        """初始化并创建百度 CFC 沙箱实例。

        Args:
            api_key:        百度 CFC API Key。None 时从 E2B_API_KEY 环境变量读取。
            domain:         百度 CFC 域名。None 时从 E2B_DOMAIN 环境变量读取。
            template_alias: 沙箱模板名。None 时从 SANDBOX_TEMPLATE_ALIAS 环境变量读取。
            fallback_template_alias:
                            模板创建失败时的备用模板名。None 时从
                            SANDBOX_FALLBACK_TEMPLATE_ALIAS 环境变量读取。
            timeout:        单次命令执行超时（秒），默认 60。
            sandbox_timeout:沙箱最长存活时间（秒），默认 300。
        """
        self._api_key = (api_key or os.environ.get("E2B_API_KEY", "")).strip()
        self._domain = (domain or os.environ.get("E2B_DOMAIN", "")).strip()
        self._template_alias = _normalize_optional_string(
            template_alias or os.environ.get("SANDBOX_TEMPLATE_ALIAS")
        )
        self._fallback_template_alias = _normalize_optional_string(
            fallback_template_alias or os.environ.get("SANDBOX_FALLBACK_TEMPLATE_ALIAS")
        )
        self._timeout = timeout
        self._sandbox_timeout = sandbox_timeout
        self._sandbox_id_val = f"baidu-cfc-{uuid.uuid4().hex[:8]}"
        self._active_template_alias: str | None = None
        self._sbx = None  # e2b Sandbox 实例，延迟创建

        if not self._api_key:
            raise ValueError("E2B_API_KEY 未配置，请在 .env 中设置")
        if not self._domain:
            raise ValueError("E2B_DOMAIN 未配置，请在 .env 中设置")

    # ------------------------------------------------------------------ #
    #  内部：懒加载沙箱实例                                               #
    # ------------------------------------------------------------------ #

    def _get_sandbox(self):
        """懒加载并返回 e2b Sandbox 实例。首次调用时创建，后续复用。"""
        if self._sbx is None:
            self._sbx = self._create_sandbox()
        return self._sbx

    def ensure_ready(self) -> None:
        """强制创建沙箱，用于在深度思考启动阶段提前验证模板可用性。"""
        self._get_sandbox()

    def _get_template_candidates(self) -> list[str]:
        """返回可尝试的模板名列表。"""
        if not self._template_alias:
            return []

        candidates = [self._template_alias]
        fallback_template_alias = self._fallback_template_alias or _DEFAULT_FALLBACK_TEMPLATE_ALIAS
        if fallback_template_alias and fallback_template_alias not in candidates:
            candidates.append(fallback_template_alias)
        return candidates

    def _should_bypass_upstream_api_key_validation(self) -> bool:
        """判断是否需要绕过 upstream E2B 的本地 API key 形态校验。"""
        api_key = self._api_key.strip()
        domain = self._domain.strip().lower()
        if not api_key or not domain:
            return False
        if api_key.startswith("e2b_"):
            return False
        return "baidubce.com" in domain

    @contextmanager
    def _patched_upstream_api_key_validation(self):
        """在百度 CFC 场景下临时绕过 upstream E2B 的本地 key 校验。"""
        if not self._should_bypass_upstream_api_key_validation():
            yield False
            return

        try:
            import e2b.api as e2b_api  # noqa: PLC0415
        except Exception as exc:  # pragma: no cover - 仅用于极端依赖缺失场景
            logger.warning("无法导入 upstream E2B API 校验模块，继续尝试创建沙箱: %s", exc)
            yield False
            return

        original_validate_api_key = getattr(e2b_api, "validate_api_key", None)
        if not callable(original_validate_api_key):
            yield False
            return

        def _noop_validate_api_key(*_args, **_kwargs):
            return None

        e2b_api.validate_api_key = _noop_validate_api_key
        try:
            logger.info(
                "百度 CFC 沙箱将临时绕过 upstream E2B API key 校验: domain=%s",
                self._domain,
            )
            yield True
        finally:
            e2b_api.validate_api_key = original_validate_api_key

    def _create_sandbox(self):
        """创建 e2b_code_interpreter Sandbox 实例（指向百度 CFC）。"""
        # 设置 E2B SDK 所需的环境变量（SDK 从 env 读取配置）
        os.environ["E2B_API_KEY"] = self._api_key.strip()
        os.environ["E2B_DOMAIN"] = self._domain.strip()

        try:
            with self._patched_upstream_api_key_validation():
                from e2b_code_interpreter import Sandbox  # noqa: PLC0415
                template_candidates = self._get_template_candidates()

                if not template_candidates:
                    sbx = Sandbox.create(timeout=self._sandbox_timeout)
                    logger.info("百度 CFC 沙箱创建成功: sandbox_id=%s", sbx.sandbox_id)
                    self._sandbox_id_val = sbx.sandbox_id
                    self._active_template_alias = None
                    return sbx

                last_error: Exception | None = None
                for index, template_alias in enumerate(template_candidates):
                    try:
                        sbx = Sandbox.create(template=template_alias, timeout=self._sandbox_timeout)
                        logger.info(
                            "百度 CFC 沙箱创建成功: template=%s sandbox_id=%s",
                            template_alias,
                            sbx.sandbox_id,
                        )
                        self._sandbox_id_val = sbx.sandbox_id
                        self._active_template_alias = template_alias
                        return sbx
                    except Exception as e:
                        last_error = e
                        if index < len(template_candidates) - 1:
                            logger.warning(
                                "百度 CFC 沙箱模板创建失败，准备尝试 fallback: template=%s, error=%s",
                                template_alias,
                                e,
                            )
                        else:
                            logger.error("百度 CFC 沙箱创建失败: template=%s, error=%s", template_alias, e)

                if last_error is not None:
                    raise last_error
                raise RuntimeError("百度 CFC 沙箱创建失败：未能获得有效的模板候选项")
        except Exception as e:
            logger.error("百度 CFC 沙箱创建失败: %s", e)
            raise

    # ------------------------------------------------------------------ #
    #  SandboxBackendProtocol 必须实现的属性                              #
    # ------------------------------------------------------------------ #

    @property
    def id(self) -> str:
        """返回沙箱唯一标识符。"""
        return self._sandbox_id_val

    # ------------------------------------------------------------------ #
    #  BaseSandbox 必须实现的三个抽象方法                                 #
    # ------------------------------------------------------------------ #

    def execute(self, command: str, *, timeout: int | None = None) -> ExecuteResponse:
        """在百度 CFC 沙箱内执行 shell 命令。

        Args:
            command: 完整的 shell 命令字符串，例如 "ls -la /workspace"。
            timeout: 本次执行超时（秒）。None 时使用实例默认值。

        Returns:
            ExecuteResponse，包含：
                output    — 合并后的 stdout + stderr 输出
                exit_code — 进程退出码（0 表示成功）
                truncated — 输出是否被截断
        """
        effective_timeout = timeout if timeout is not None else self._timeout

        try:
            sbx = self._get_sandbox()
            # e2b commands.run 执行 shell 命令
            result = sbx.commands.run(command, timeout=effective_timeout)

            output_parts = []
            if result.stdout:
                output_parts.append(result.stdout)
            if result.stderr:
                stderr_lines = result.stderr.strip().split("\n")
                output_parts.extend(f"[stderr] {line}" for line in stderr_lines if line)

            output = "\n".join(output_parts) if output_parts else "<no output>"
            exit_code = result.exit_code if result.exit_code is not None else 0

            # 超大输出截断（保护上下文窗口）
            MAX_BYTES = 100_000
            truncated = False
            if len(output) > MAX_BYTES:
                output = output[:MAX_BYTES] + f"\n\n... 输出已截断（超过 {MAX_BYTES} 字节）"
                truncated = True

            logger.debug("execute 完成: exit_code=%s, output_len=%d", exit_code, len(output))
            return ExecuteResponse(output=output, exit_code=exit_code, truncated=truncated)

        except Exception as e:
            logger.error("execute 执行失败: command=%r, error=%s", command, e)
            return ExecuteResponse(
                output=f"沙箱执行错误 ({type(e).__name__}): {e}",
                exit_code=1,
                truncated=False,
            )

    def upload_files(self, files: list[tuple[str, bytes]]) -> list[FileUploadResponse]:
        """向百度 CFC 沙箱上传文件。

        Args:
            files: [(路径, 字节内容), ...] 列表

        Returns:
            每个文件对应一个 FileUploadResponse
        """
        responses: list[FileUploadResponse] = []
        try:
            sbx = self._get_sandbox()
        except Exception as e:
            return [FileUploadResponse(path=path, error=str(e)) for path, _ in files]

        for path, content in files:
            try:
                sbx.files.write(path, content)
                responses.append(FileUploadResponse(path=path))
                logger.debug("upload_files 成功: %s (%d bytes)", path, len(content))
            except Exception as e:
                logger.error("upload_files 失败: path=%s, error=%s", path, e)
                responses.append(FileUploadResponse(path=path, error=str(e)))

        return responses

    def download_files(self, paths: list[str]) -> list[FileDownloadResponse]:
        """从百度 CFC 沙箱下载文件。

        Args:
            paths: 文件绝对路径列表

        Returns:
            每个文件对应一个 FileDownloadResponse
        """
        responses: list[FileDownloadResponse] = []
        try:
            sbx = self._get_sandbox()
        except Exception as e:
            return [FileDownloadResponse(path=p, content=None, error=str(e)) for p in paths]

        for path in paths:
            try:
                content: bytes = sbx.files.read(path, format="bytes")
                responses.append(FileDownloadResponse(path=path, content=content))
                logger.debug("download_files 成功: %s (%d bytes)", path, len(content))
            except Exception as e:
                logger.error("download_files 失败: path=%s, error=%s", path, e)
                responses.append(FileDownloadResponse(path=path, content=None, error=str(e)))

        return responses

    # ------------------------------------------------------------------ #
    #  生命周期管理                                                        #
    # ------------------------------------------------------------------ #

    def close(self) -> None:
        """关闭并销毁沙箱实例，释放资源。"""
        if self._sbx is not None:
            try:
                self._sbx.kill()
                logger.info("百度 CFC 沙箱已关闭: %s", self._sandbox_id_val)
            except Exception as e:
                logger.warning("关闭沙箱时出错: %s", e)
            finally:
                self._sbx = None

    def __enter__(self) -> "BaiduCfcSandboxBackend":
        return self

    def __exit__(self, *_) -> None:
        self.close()
