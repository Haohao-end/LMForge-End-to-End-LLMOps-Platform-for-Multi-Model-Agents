
import ast
import time
from typing import Optional
from langchain_core.runnables import RunnableConfig
from internal.core.workflow.entities.node_entity import NodeResult, NodeStatus
from internal.core.workflow.entities.variable_entity import VARIABLE_TYPE_DEFAULT_VALUE_MAP
from internal.core.workflow.entities.workflow_entity import WorkflowState
from internal.core.workflow.nodes import BaseNode
from internal.core.workflow.utils.helper import extract_variables_from_state
from internal.exception import FailException
from .code_entity import CodeNodeData


class CodeNode(BaseNode):
    """Python代码运行节点"""
    node_data: CodeNodeData

    def invoke(self, state: WorkflowState, config: Optional[RunnableConfig] = None) -> WorkflowState:
        """Python代码运行节点，执行的代码函数名字必须为main，并且参数名为params，有且只有一个参数，不允许有额外的其他语句"""
        # 1.从状态中提取输入数据
        start_at = time.perf_counter()
        inputs_dict = extract_variables_from_state(self.node_data.inputs, state)

        # todo:2.执行Python代码，该方法目前可以执行任意的Python代码，所以非常危险，后期需要单独将这部分功能迁移到沙箱中或者指定容器中运行和项目分离
        result = self._execute_function(self.node_data.code, params=inputs_dict)

        # 3.检测函数的返回值是否为字典
        if not isinstance(result, dict):
            raise FailException("main函数的返回值必须是一个字典")

        # 4.提取输出数据
        outputs_dict = {}
        outputs = self.node_data.outputs
        for output in outputs:
            # 5.提取输出数据(非严格校验)
            outputs_dict[output.name] = result.get(
                output.name,
                VARIABLE_TYPE_DEFAULT_VALUE_MAP.get(output.type),
            )

        # 6.构建状态数据并返回
        return {
            "node_results": [
                NodeResult(
                    node_data=self.node_data,
                    status=NodeStatus.SUCCEEDED.value,
                    inputs=inputs_dict,
                    outputs=outputs_dict,
                    latency=(time.perf_counter() - start_at),
                )
            ]
        }

    @classmethod
    def _execute_function(cls, code: str, *args, **kwargs):
        """执行Python函数代码"""
        try:
            # 1.解析代码为AST(抽象语法树)
            tree = ast.parse(code)

            # 2.定义变量用于检查是否找到main函数
            main_func = None

            # 3.循环遍历语法树
            for node in tree.body:
                # 4.判断节点类型是否为函数
                if isinstance(node, ast.FunctionDef):
                    # 5.检查函数名称是否为main
                    if node.name == "main":
                        if main_func:
                            raise FailException("代码中只能有一个main函数")

                        # 6.检测main函数的参数是否为params，如果不是则抛出错误
                        if len(node.args.args) != 1 or node.args.args[0].arg != "params":
                            raise FailException("main函数必须只有一个参数，且参数为params")

                        main_func = node
                    else:
                        # 7.其他函数的情况，直接抛出错误
                        raise FailException("代码中不能包含其他函数，只能有main函数")
                else:
                    # 8.非函数的情况，直接抛出错误
                    raise FailException("代码中只能包含函数定义，不允许其他语句存在")

            # 9.判断下是否找到main函数
            if not main_func:
                raise FailException("代码中必须包含名为main的函数")

            # 10.代码通过AST校验，执行代码
            local_vars = {}
            exec(code, {}, local_vars)

            # 11.调用并执行main函数
            if "main" in local_vars and callable(local_vars["main"]):
                return local_vars["main"](*args, **kwargs)
            else:
                raise FailException("main函数必须是一个可调用的函数")
        except Exception as e:
            raise FailException("Python代码执行出错")
