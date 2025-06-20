import json
import time
import uuid
from dataclasses import dataclass
from typing import Any, Generator
from uuid import UUID
from flask import request
from injector import inject
from sqlalchemy import desc
from internal.core.tools.builtin_tools.providers import BuiltinProviderManager
from internal.core.workflow import Workflow as WorkflowTool
from internal.core.workflow.entities.edge_entity import BaseEdgeData
from internal.core.workflow.entities.node_entity import NodeType, BaseNodeData
from internal.core.workflow.entities.workflow_entity import WorkflowConfig
from internal.core.workflow.nodes import (
    CodeNodeData,
    DatasetRetrievalNodeData,
    EndNodeData,
    HttpRequestNodeData,
    LLMNodeData,
    StartNodeData,
    TemplateTransformNodeData,
    ToolNodeData,
)
from internal.entity.workflow_entity import WorkflowStatus, DEFAULT_WORKFLOW_CONFIG, WorkflowResultStatus
from internal.exception import ValidateErrorException, NotFoundException, ForbiddenException, FailException
from internal.lib.helper import convert_model_to_dict
from internal.model import Account, Workflow, Dataset, ApiTool, WorkflowResult
from internal.schema.workflow_schema import CreateWorkflowReq, GetWorkflowsWithPageReq
from pkg.paginator import Paginator
from pkg.sqlalchemy import SQLAlchemy
from .base_service import BaseService


@inject
@dataclass
class WorkflowService(BaseService):
    """工作流服务"""
    db: SQLAlchemy
    builtin_provider_manager: BuiltinProviderManager

    def create_workflow(self, req: CreateWorkflowReq, account: Account) -> Workflow:
        """根据传递的请求信息创建工作流"""
        # 1.根据传递的工作流工具名称查询工作流信息
        check_workflow = self.db.session.query(Workflow).filter(
            Workflow.tool_call_name == req.tool_call_name.data.strip(),
            Workflow.account_id == account.id,
        ).one_or_none()
        if check_workflow:
            raise ValidateErrorException(f"在当前账号下已创建[{req.tool_call_name.data}]工作流，不支持重名")

        # 2.调用数据库服务创建工作流
        return self.create(Workflow, **{
            **req.data,
            **DEFAULT_WORKFLOW_CONFIG,
            "account_id": account.id,
            "is_debug_passed": False,
            "status": WorkflowStatus.DRAFT.value,
            "tool_call_name": req.tool_call_name.data.strip(),
        })

    def get_workflow(self, workflow_id: UUID, account: Account) -> Workflow:
        """根据传递的工作流id，获取指定的工作流基础信息"""
        # 1.查询数据库获取工作流基础信息
        workflow = self.get(Workflow, workflow_id)

        # 2.判断工作流是否存在
        if not workflow:
            raise NotFoundException("该工作流不存在，请核实后重试")

        # 3.判断当前账号是否有权限访问该应用
        if workflow.account_id != account.id:
            raise ForbiddenException("当前账号无权限访问该应用，请核实后尝试")

        return workflow

    def delete_workflow(self, workflow_id: UUID, account: Account) -> Workflow:
        """根据传递的工作流id+账号信息，删除指定的工作流"""
        # 1.获取工作流基础信息并校验权限
        workflow = self.get_workflow(workflow_id, account)

        # 2.删除工作流
        self.delete(workflow)

        return workflow

    def update_workflow(self, workflow_id: UUID, account: Account, **kwargs) -> Workflow:
        """根据传递的工作流id+请求更新工作流基础信息"""
        # 1.获取工作流基础信息并校验权限
        workflow = self.get_workflow(workflow_id, account)

        # 2.根据传递的工具调用名字查询是否存在重名工作流
        check_workflow = self.db.session.query(Workflow).filter(
            Workflow.tool_call_name == kwargs.get("tool_call_name", "").strip(),
            Workflow.account_id == account.id,
            Workflow.id != workflow.id,
        ).one_or_none()
        if check_workflow:
            raise ValidateErrorException(f"在当前账号下已创建[{kwargs.get('tool_call_name', '')}]工作流，不支持重名")

        # 3.更新工作流基础信息
        self.update(workflow, **kwargs)

        return workflow

    def get_workflows_with_page(
            self, req: GetWorkflowsWithPageReq, account: Account
    ) -> tuple[list[Workflow], Paginator]:
        """根据传递的信息获取工作流分页列表数据"""
        # 1.构建分页器
        paginator = Paginator(db=self.db, req=req)

        # 2.构建筛选器
        filters = [Workflow.account_id == account.id]
        if req.search_word.data:
            filters.append(Workflow.name.ilike(f"%{req.search_word.data}%"))
        if req.status.data:
            filters.append(Workflow.status == req.status.data)

        # 3.分页查询数据
        workflows = paginator.paginate(
            self.db.session.query(Workflow).filter(*filters).order_by(desc("created_at"))
        )

        return workflows, paginator

    def update_draft_graph(self, workflow_id: UUID, draft_graph: dict[str, Any], account: Account) -> Workflow:
        """根据传递的工作流id+草稿图配置+账号更新工作流的草稿图"""
        # 1.根据传递的id获取工作流并校验权限
        workflow = self.get_workflow(workflow_id, account)

        # 2.校验传递的草稿图配置，因为有可能边有可能还未建立，所以需要校验关联的数据
        validate_draft_graph = self._validate_graph(draft_graph, account)

        # 3.更新工作流草稿图配置，每次修改都将is_debug_passed的值重置为False，该处可以优化对比字典里除position的其他属性
        self.update(workflow, **{
            "draft_graph": validate_draft_graph,
            "is_debug_passed": False,
        })

        return workflow

    def get_draft_graph(self, workflow_id: UUID, account: Account) -> dict[str, Any]:
        """根据传递的工作流id+账号信息，获取指定工作流的草稿配置信息"""
        # 1.根据传递的id获取工作流并校验权限
        workflow = self.get_workflow(workflow_id, account)

        # 2.提取草稿图结构信息并校验(不更新校验后的数据到数据库)
        draft_graph = workflow.draft_graph
        validate_draft_graph = self._validate_graph(draft_graph, account)

        # 3.循环遍历节点信息，为工具节点/知识库节点附加元数据
        for node in validate_draft_graph["nodes"]:
            if node.get("node_type") == NodeType.TOOL.value:
                # 4.判断工具的类型执行不同的操作
                if node.get("tool_type") == "builtin_tool":
                    # 5.节点类型为工具，则附加工具的名称、图标、参数等额外信息
                    provider = self.builtin_provider_manager.get_provider(node.get("provider_id"))
                    if not provider:
                        continue

                    # 6.获取提供者下的工具实体，并检测是否存在
                    tool_entity = provider.get_tool_entity(node.get("tool_id"))
                    if not tool_entity:
                        continue

                    # 7.判断工具的params和草稿中的params是否一致，如果不一致则全部重置为默认值（或者考虑删除这个工具的引用）
                    param_keys = set([param.name for param in tool_entity.params])
                    params = node.get("params")
                    if set(params.keys()) - param_keys:
                        params = {
                            param.name: param.default
                            for param in tool_entity.params
                            if param.default is not None
                        }

                    # 8.数据校验成功附加展示信息
                    provider_entity = provider.provider_entity
                    node["meta"] = {
                        "type": "builtin_tool",
                        "provider": {
                            "id": provider_entity.name,
                            "name": provider_entity.name,
                            "label": provider_entity.label,
                            "icon": f"{request.scheme}://{request.host}/builtin-tools/{provider_entity.name}/icon",
                            "description": provider_entity.description,
                        },
                        "tool": {
                            "id": tool_entity.name,
                            "name": tool_entity.name,
                            "label": tool_entity.label,
                            "description": tool_entity.description,
                            "params": params,
                        }
                    }
                elif node.get("tool_type") == "api_tool":
                    # 9.查询数据库获取对应的工具记录，并检测是否存在
                    tool_record = self.db.session.query(ApiTool).filter(
                        ApiTool.provider_id == node.get("provider_id"),
                        ApiTool.name == node.get("tool_id"),
                        ApiTool.account_id == account.id,
                    ).one_or_none()
                    if not tool_record:
                        continue

                    # 10.组装api工具展示信息
                    provider = tool_record.provider
                    node["meta"] = {
                        "type": "api_tool",
                        "provider": {
                            "id": str(provider.id),
                            "name": provider.name,
                            "label": provider.name,
                            "icon": provider.icon,
                            "description": provider.description,
                        },
                        "tool": {
                            "id": str(tool_record.id),
                            "name": tool_record.name,
                            "label": tool_record.name,
                            "description": tool_record.description,
                            "params": {},
                        },
                    }
                else:
                    node["meta"] = {
                        "type": "api_tool",
                        "provider": {
                            "id": "",
                            "name": "",
                            "label": "",
                            "icon": "",
                            "description": "",
                        },
                        "tool": {
                            "id": "",
                            "name": "",
                            "label": "",
                            "description": "",
                            "params": {},
                        },
                    }
            elif node.get("node_type") == NodeType.DATASET_RETRIEVAL.value:
                # 5.节点类型为知识库检索，需要附加知识库的名称、图标等信息
                datasets = self.db.session.query(Dataset).filter(
                    Dataset.id.in_(node.get("dataset_ids", [])),
                    Dataset.account_id == account.id,
                ).all()
                node["meta"] = {
                    "datasets": [{
                        "id": dataset.id,
                        "name": dataset.name,
                        "icon": dataset.icon,
                        "description": dataset.description,
                    } for dataset in datasets]
                }

        return validate_draft_graph

    def debug_workflow(self, workflow_id: UUID, inputs: dict[str, Any], account: Account) -> Generator:
        """调试指定的工作流API接口，该接口为流式事件输出"""
        # 1.根据传递的id获取工作流并校验权限
        workflow = self.get_workflow(workflow_id, account)

        # 2.创建工作流工具
        workflow_tool = WorkflowTool(workflow_config=WorkflowConfig(
            account_id=account.id,
            name=workflow.tool_call_name,
            description=workflow.description,
            nodes=workflow.draft_graph.get("nodes", []),
            edges=workflow.draft_graph.get("edges", []),
        ))

        def handle_stream() -> Generator:
            # 3.定义变量存储所有节点运行结果
            node_results = []

            # 4.添加数据库工作流运行结果记录
            workflow_result = self.create(WorkflowResult, **{
                "app_id": None,
                "account_id": account.id,
                "workflow_id": workflow.id,
                "graph": workflow.draft_graph,
                "state": [],
                "latency": 0,
                "status": WorkflowResultStatus.RUNNING.value,
            })

            # 4.调用stream服务获取工具信息
            start_at = time.perf_counter()
            try:
                for chunk in workflow_tool.stream(inputs):
                    # 5.chunk的格式为:{"node_name": WorkflowState}，所以需要取出节点响应结构的第1个key
                    first_key = next(iter(chunk))

                    # 6.取出各个节点的运行结果
                    node_result = chunk[first_key]["node_results"][0]
                    node_result_dict = convert_model_to_dict(node_result)
                    node_results.append(node_result_dict)

                    # 7.组装响应数据并流式事件输出
                    data = {
                        "id": str(uuid.uuid4()),
                        **node_result_dict,
                    }
                    yield f"event: workflow\ndata: {json.dumps(data)}\n\n"

                # 7.流式输出完毕后，将结果存储到数据库中
                self.update(workflow_result, **{
                    "status": WorkflowResultStatus.SUCCEEDED.value,
                    "state": node_results,
                    "latency": (time.perf_counter() - start_at),
                })
                self.update(workflow, **{
                    "is_debug_passed": True,
                })
            except Exception:
                self.update(workflow_result, **{
                    "status": WorkflowResultStatus.FAILED.value,
                    "state": node_results,
                    "latency": (time.perf_counter() - start_at)
                })

        return handle_stream()

    def publish_workflow(self, workflow_id: UUID, account: Account) -> Workflow:
        """根据传递的工作流id，发布指定的工作流"""
        # 1.根据传递的id获取工作流并校验权限
        workflow = self.get_workflow(workflow_id, account)

        # 2.校验工作流是否调试通过
        if workflow.is_debug_passed is False:
            raise FailException("该工作流未调试通过，请调试通过后发布")

        # 3.使用WorkflowConfig二次校验，如果校验失败则不发布
        try:
            WorkflowConfig(
                account_id=account.id,
                name=workflow.tool_call_name,
                description=workflow.description,
                nodes=workflow.draft_graph.get("nodes", []),
                edges=workflow.draft_graph.get("edges", []),
            )
        except Exception:
            self.update(workflow, **{
                "is_debug_passed": False,
            })
            raise ValidateErrorException("工作流配置校验失败，请核实后重试")

        # 4.更新工作流的发布状态
        self.update(workflow, **{
            "graph": workflow.draft_graph,
            "status": WorkflowStatus.PUBLISHED.value,
            "is_debug_passed": False,
        })

        return workflow

    def cancel_publish_workflow(self, workflow_id: UUID, account: Account) -> Workflow:
        """取消发布指定的工作流"""
        # 1.根据传递的id获取工作流并校验权限
        workflow = self.get_workflow(workflow_id, account)

        # 2.校验工作流是否为已发布的状态
        if workflow.status != WorkflowStatus.PUBLISHED.value:
            raise FailException("该工作流未发布无法取消发布")

        # 3.更新发布状态并删除运行图草稿配置
        self.update(workflow, **{
            "graph": {},
            "status": WorkflowStatus.DRAFT.value,
            "is_debug_passed": False,
        })

        return workflow

    def _validate_graph(self, graph: dict[str, Any], account: Account) -> dict[str, Any]:
        """校验工作流图结构，包括节点和边的验证"""
        # 提取节点和边数据
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])

        # 节点类型与数据类映射
        node_data_classes = {
            NodeType.START.value: StartNodeData,
            NodeType.END.value: EndNodeData,
            NodeType.LLM.value: LLMNodeData,
            NodeType.TEMPLATE_TRANSFORM.value: TemplateTransformNodeData,
            NodeType.DATASET_RETRIEVAL.value: DatasetRetrievalNodeData,
            NodeType.CODE.value: CodeNodeData,
            NodeType.TOOL.value: ToolNodeData,
            NodeType.HTTP_REQUEST.value: HttpRequestNodeData,
        }

        # 校验节点
        node_data_dict: dict[UUID, BaseNodeData] = {}
        start_nodes = 0
        end_nodes = 0

        for node in nodes:
            try:
                if not isinstance(node, dict):
                    raise ValidateErrorException("节点数据必须是字典类型")

                node_type = node.get("node_type", "")
                if not node_type:
                    raise ValidateErrorException("节点缺少类型定义")

                # 特殊处理工具节点
                if node_type == NodeType.TOOL.value:
                    node = self._prepare_tool_node(node)

                node_data_cls = node_data_classes.get(node_type)
                if not node_data_cls:
                    raise ValidateErrorException(f"不支持的节点类型: {node_type}")

                # 验证节点数据
                node_data = node_data_cls(**node)

                # 检查节点ID唯一性
                if node_data.id in node_data_dict:
                    raise ValidateErrorException(f"重复的节点ID: {node_data.id}")

                # 检查节点标题唯一性
                if any(n.title == node_data.title for n in node_data_dict.values()):
                    raise ValidateErrorException(f"重复的节点标题: {node_data.title}")

                # 特殊节点数量检查
                if node_type == NodeType.START.value:
                    start_nodes += 1
                    if start_nodes > 1:
                        raise ValidateErrorException("工作流只能有一个开始节点")

                elif node_type == NodeType.END.value:
                    end_nodes += 1
                    if end_nodes > 1:
                        raise ValidateErrorException("工作流只能有一个结束节点")

                elif node_type == NodeType.DATASET_RETRIEVAL.value:
                    # 验证知识库权限
                    datasets = self.db.session.query(Dataset).filter(
                        Dataset.id.in_(node_data.dataset_ids),
                        Dataset.account_id == account.id,
                    ).all()
                    node_data.dataset_ids = [str(d.id) for d in datasets]

                node_data_dict[node_data.id] = node_data

            except Exception as e:
                print(f"节点验证失败 - ID: {node.get('id')}, 类型: {node_type}, 错误: {str(e)}")
                continue

        # 校验边
        edge_data_dict: dict[UUID, BaseEdgeData] = {}
        for edge in edges:
            try:
                if not isinstance(edge, dict):
                    raise ValidateErrorException("边数据必须是字典类型")

                edge_data = BaseEdgeData(**edge)

                # 检查边ID唯一性
                if edge_data.id in edge_data_dict:
                    raise ValidateErrorException(f"重复的边ID: {edge_data.id}")

                # 检查边连接的节点是否存在
                if edge_data.source not in node_data_dict:
                    raise ValidateErrorException(f"源节点不存在: {edge_data.source}")

                if edge_data.target not in node_data_dict:
                    raise ValidateErrorException(f"目标节点不存在: {edge_data.target}")

                # 检查边是否重复
                if any(
                        e.source == edge_data.source and e.target == edge_data.target
                        for e in edge_data_dict.values()
                ):
                    raise ValidateErrorException("重复的边连接")

                edge_data_dict[edge_data.id] = edge_data

            except Exception as e:
                print(f"边验证失败 - ID: {edge.get('id')}, 错误: {str(e)}")
                continue

        return {
            "nodes": [convert_model_to_dict(node) for node in node_data_dict.values()],
            "edges": [convert_model_to_dict(edge) for edge in edge_data_dict.values()],
        }

    def _prepare_tool_node(self, node: dict) -> dict:
        """预处理工具节点数据，确保所有必需字段存在"""
        # 从meta中获取tool_type，如果不存在则默认为builtin_tool
        tool_type = node.get("meta", {}).get("type", "builtin_tool")

        # 设置默认值
        node.setdefault("tool_type", tool_type)
        node.setdefault("provider_id", "default_provider")
        node.setdefault("tool_id", "default_tool")
        node.setdefault("params", {})
        node.setdefault("inputs", [])
        node.setdefault("outputs", [])
        node.setdefault("meta", {})

        # 确保outputs至少有默认值
        if not node["outputs"]:
            node["outputs"] = [{
                "name": "text",
                "type": "string",
                "value": {"type": "generated"}
            }]

        return node