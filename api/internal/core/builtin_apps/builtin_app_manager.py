import os
import yaml
from injector import inject, singleton
from pydantic import BaseModel, Field
from internal.core.builtin_apps.entities.builtin_app_entity import BuiltinAppEntity
from internal.core.builtin_apps.entities.category_entity import CategoryEntity


@inject
@singleton
class BuiltinAppManager(BaseModel):
    """内置应用管理器"""
    builtin_app_map: dict[str, BuiltinAppEntity] = Field(default_factory=dict)
    categories: list[CategoryEntity] = Field(default_factory=list)

    def __init__(self, **kwargs):
        """构造函数，初始化对应的builtin_app_map"""
        super().__init__(**kwargs)
        self._init_categories()
        self._init_builtin_app_map()

    def get_builtin_app(self, builtin_app_id: str) -> BuiltinAppEntity:
        """根据传递的id获取内置工具信息"""
        return self.builtin_app_map.get(builtin_app_id, None)

    def get_builtin_apps(self) -> list[BuiltinAppEntity]:
        """获取内置应用实体列表信息"""
        return [builtin_app_entity for builtin_app_entity in self.builtin_app_map.values()]

    def get_categories(self) -> list[CategoryEntity]:
        """获取内置应用实体分类列表信息"""
        return self.categories

    def _init_builtin_app_map(self):
        """内置工具管理器初始化时初始化所有内置工具信息"""
        # 1.检测builtin_app_map是否为空
        if self.builtin_app_map:
            return

        # 2.获取当前文件夹/类所在的文件夹路径
        current_path = os.path.abspath(__file__)
        parent_path = os.path.dirname(current_path)
        builtin_apps_yaml_path = os.path.join(parent_path, "builtin_apps")

        # 3.循环遍历builtin_apps_yaml_path读取底下的所有yaml文件
        for filename in os.listdir(builtin_apps_yaml_path):
            if filename.endswith(".yaml") or filename.endswith(".yml"):
                file_path = os.path.join(builtin_apps_yaml_path, filename)

                # 4.读取yaml数据
                with open(file_path, encoding="utf-8") as f:
                    builtin_app = yaml.safe_load(f)

                # 5.初始化内置应用数据并添加到字典中
                builtin_app["language_model_config"] = builtin_app.pop("model_config")
                self.builtin_app_map[builtin_app.get("id")] = BuiltinAppEntity(**builtin_app)

    def _init_categories(self):
        """初始化内置工具分类列表信息"""
        # 1.检测数据是否已经处理
        if self.categories:
            return

        # 2.获取当前文件夹/类所在的文件夹路径
        current_path = os.path.abspath(__file__)
        parent_path = os.path.dirname(current_path)
        categories_yaml_path = os.path.join(parent_path, "categories", "categories.yaml")

        # 3.读取yaml数据
        with open(categories_yaml_path, encoding="utf-8") as f:
            categories = yaml.safe_load(f)

        # 4.循环遍历所有分类数据并初始化
        for category in categories:
            self.categories.append(CategoryEntity(**category))
