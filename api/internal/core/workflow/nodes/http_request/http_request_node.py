import time
from typing import Optional
from internal.core.workflow.nodes import BaseNode
from langchain_core.runnables import RunnableConfig
from internal.core.workflow.entities.node_entity import NodeResult, NodeStatus
from internal.core.workflow.entities.workflow_entity import WorkflowState
from internal.core.workflow.utils.helper import extract_variables_from_state
from internal.lib.safe_http_client import safe_request
from .http_request_entity import (
    HttpRequestInputType,
    HttpRequestMethod,
    HttpRequestNodeData,
)

DEFAULT_HTTP_REQUEST_TIMEOUT_SECONDS = 30


class HttpRequestNode(BaseNode):
    """HTTP请求节点"""
    node_data: HttpRequestNodeData

    def invoke(self, state: WorkflowState, config: Optional[RunnableConfig] = None) -> WorkflowState:
        """HTTP请求节点调用函数，像指定的URL发起请求并获取相应"""
        # 1.提取节点输入变量字典
        start_at = time.perf_counter()
        _inputs_dict = extract_variables_from_state(self.node_data.inputs, state)

        # 2.提取数据，涵盖params、headers、body的数据
        inputs_dict = {
            HttpRequestInputType.PARAMS: {},
            HttpRequestInputType.HEADERS: {},
            HttpRequestInputType.BODY: {}
        }
        for input in self.node_data.inputs:
            inputs_dict[input.meta.get("type")][input.name] = _inputs_dict.get(input.name)

        # 3.根据传递的method+url发起请求
        request_kwargs = {
            "headers": inputs_dict[HttpRequestInputType.HEADERS],
            "params": inputs_dict[HttpRequestInputType.PARAMS],
            "timeout": DEFAULT_HTTP_REQUEST_TIMEOUT_SECONDS,
        }
        if self.node_data.method == HttpRequestMethod.GET:
            response = safe_request(
                self.node_data.method.value,
                self.node_data.url,
                **request_kwargs,
            )
        else:
            # 4.其他请求方法需携带body参数
            response = safe_request(
                self.node_data.method.value,
                self.node_data.url,
                data=inputs_dict[HttpRequestInputType.BODY],
                **request_kwargs,
            )

        # 5.获取响应文本和状态码
        text = response.text
        status_code = response.status_code

        # 6.提取并构建输出数据结构
        outputs = {"text": text, "status_code": status_code}

        # 7.构建响应状态并返回
        return {
            "node_results": [
                NodeResult(
                    node_data=self.node_data,
                    status=NodeStatus.SUCCEEDED.value,
                    inputs=inputs_dict,
                    outputs=outputs,
                    latency=(time.perf_counter() - start_at),
                )
            ]
        }
