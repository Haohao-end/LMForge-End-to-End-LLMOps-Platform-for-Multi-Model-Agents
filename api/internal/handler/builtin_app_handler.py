from dataclasses import dataclass
from flask_login import login_required, current_user
from injector import inject

from internal.schema.builtin_app_schema import (
    GetBuiltinAppCategoriesResp,
    GetBuiltinAppsResp,
    AddBuiltinAppToSpaceReq,
)
from internal.service import BuiltinAppService
from pkg.response import success_json, validate_error_json


@inject
@dataclass
class BuiltinAppHandler:
    """LLMOps内置应用处理器"""
    builtin_app_service: BuiltinAppService

    @login_required
    def get_builtin_app_categories(self):
        """获取内置应用分类列表信息"""
        categories = self.builtin_app_service.get_categories()
        resp = GetBuiltinAppCategoriesResp(many=True)
        return success_json(resp.dump(categories))

    @login_required
    def get_builtin_apps(self):
        """获取所有内置应用列表信息"""
        builtin_apps = self.builtin_app_service.get_builtin_apps()
        resp = GetBuiltinAppsResp(many=True)
        return success_json(resp.dump(builtin_apps))

    @login_required
    def add_builtin_app_to_space(self):
        """将指定的内置应用添加到个人空间"""
        # 1.提取请求并校验
        req = AddBuiltinAppToSpaceReq()
        if not req.validate():
            return validate_error_json(req.errors)

        # 2.将指定内置应用模板添加到个人空间
        app = self.builtin_app_service.add_builtin_app_to_space(req.builtin_app_id.data, current_user)

        return success_json({"id": app.id})
