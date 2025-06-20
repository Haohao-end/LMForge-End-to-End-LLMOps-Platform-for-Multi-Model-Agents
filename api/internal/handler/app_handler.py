import uuid
from dataclasses import dataclass
from uuid import UUID
from flask import request
from flask_login import login_required, current_user
from injector import inject
from internal.schema.app_schema import (
    CreateAppReq,
    UpdateAppReq,
    GetAppsWithPageReq,
    GetAppsWithPageResp,
    GetAppResp,
    GetPublishHistoriesWithPageReq,
    GetPublishHistoriesWithPageResp,
    FallbackHistoryToDraftReq,
    UpdateDebugConversationSummaryReq,
    DebugChatReq,
    GetDebugConversationMessagesWithPageReq,
    GetDebugConversationMessagesWithPageResp
)
from internal.service import AppService, RetrievalService
from pkg.paginator import PageModel
from pkg.response import validate_error_json, success_json, success_message, compact_generate_response
from internal.core.language_model import LanguageModelManager

@inject
@dataclass
class AppHandler:
    """应用控制器"""
    app_service: AppService
    retrieval_service: RetrievalService
    language_model_manager: LanguageModelManager

    @login_required
    def create_app(self):
        """调用服务创建新的APP记录"""
        # 1.提取请求并校验
        req = CreateAppReq()
        if not req.validate():
            return validate_error_json(req.errors)

        # 2.调用服务创建应用信息
        app = self.app_service.create_app(req, current_user)

        # 3.返回创建成功响应提示
        return success_json({"id": app.id})

    @login_required
    def get_app(self, app_id: UUID):
        """获取指定的应用基础信息"""
        app = self.app_service.get_app(app_id, current_user)
        resp = GetAppResp()
        return success_json(resp.dump(app))

    @login_required
    def update_app(self, app_id: UUID):
        """根据传递的信息更新指定的应用"""
        # 1.提取数据并校验
        req = UpdateAppReq()
        if not req.validate():
            raise validate_error_json(req.errors)

        # 2.调用服务更新数据
        self.app_service.update_app(app_id, current_user, **req.data)

        return success_message("修改Agent智能体应用成功")

    @login_required
    def copy_app(self, app_id: UUID):
        """根据传递的应用id快速拷贝该应用"""
        app = self.app_service.copy_app(app_id, current_user)

        return success_json({"id": app.id})

    @login_required
    def delete_app(self, app_id: UUID):
        """根据传递的信息删除指定的应用"""
        self.app_service.delete_app(app_id, current_user)
        return success_message("删除Agent智能体应用成功")

    @login_required
    def get_apps_with_page(self):
        """获取当前登录账号的应用分页列表数据"""
        # 1.提取数据并校验
        req = GetAppsWithPageReq(request.args)
        if not req.validate():
            return validate_error_json(req.errors)

        # 2.调用服务获取列表数据以及分页器
        apps, paginator = self.app_service.get_apps_with_page(req, current_user)

        # 3.构建响应结构并返回
        resp = GetAppsWithPageResp(many=True)

        return success_json(PageModel(list=resp.dump(apps), paginator=paginator))



    @login_required
    def get_draft_app_config(self, app_id: UUID):
        """根据传递的应用id获取应用的最新草稿配置"""
        draft_config = self.app_service.get_draft_app_config(app_id, current_user)
        return success_json(draft_config)

    @login_required
    def update_draft_app_config(self, app_id: UUID):
        """根据传递的应用id+草稿配置更新应用的最新草稿配置"""
        # 1.获取草稿请求json数据
        draft_app_config = request.get_json(force=True, silent=True) or {}

        # 2.调用服务更新应用的草稿配置
        self.app_service.update_draft_app_config(app_id, draft_app_config, current_user)

        return success_message("更新应用草稿配置成功")

    @login_required
    def publish(self, app_id: UUID):
        """根据传递的应用id发布/更新特定的草稿配置信息"""
        self.app_service.publish_draft_app_config(app_id, current_user)
        return success_message("发布/更新应用配置成功")

    @login_required
    def cancel_publish(self, app_id: UUID):
        """根据传递的应用id 取消发布指定的应用配置信息"""
        self.app_service.cancel_publish_app_config(app_id, current_user)
        return success_message("取消发布应用配置成功")

    @login_required
    def get_publish_histories_with_page(self, app_id: UUID):
        """根据传递的应用id获取应用发布历史列表"""
        # 1.获取请求数据并校验
        req = GetPublishHistoriesWithPageReq(request.args)
        if not req.validate():
            raise validate_error_json(req.errors)

        # 2.调用服务获取分页列表数据
        app_config_versions, paginator = self.app_service.get_publish_histories_with_page(app_id, req, current_user)

        # 3.创建响应解构并返回
        resp = GetPublishHistoriesWithPageResp(many=True)

        return success_json(PageModel(list=resp.dump(app_config_versions), paginator=paginator))

    @login_required
    def fallback_history_to_draft(self, app_id: UUID):
        """根据传递的应用id+历史配置版本id，退回指定版本到草稿中"""
        # 1.提取数据并校验
        req = FallbackHistoryToDraftReq()
        if not req.validate():
            return validate_error_json(req.errors)

        # 2.调用服务回退指定版本到草稿
        self.app_service.fallback_history_to_draft(app_id, req.app_config_version_id.data, current_user)

        return success_message("回退历史配置至草稿成功")

    @login_required
    def get_debug_conversation_summary(self, app_id: UUID):
        """根据传递的应用id获取调试会话长期记忆"""
        summary = self.app_service.get_debug_conversation_summary(app_id, current_user)
        return success_json({"summary": summary})

    @login_required
    def update_debug_conversation_summary(self, app_id: UUID):
        """根据传递的应用id+摘要信息调试会话长期记忆"""
        # 1.提取数据并校验
        req = UpdateDebugConversationSummaryReq()
        if not req.validate():
            raise validate_error_json(req.errors)

        # 2.调用服务更新调试会话长期记忆
        self.app_service.update_debug_conversation_summary(app_id, req.summary.data, current_user)

        return success_message("更新AI应用长期记忆成功")

    @login_required
    def delete_debug_conversation(self, app_id: UUID):
        """根据传递的应用id 清空该应用的调试会话记录"""
        self.app_service.delete_debug_conversation(app_id, current_user)

        return success_message("清空应用调试会话记录成功")

    @login_required
    def debug_chat(self, app_id: UUID):
        """根据传递的应用id+query,发起调试对话"""
        # 1.提取数据并校验数据
        req = DebugChatReq()
        if not req.validate():
            raise validate_error_json(req.errors)

        # 2.调试服务发起会话调试
        response = self.app_service.debug_chat(app_id, req.query.data, current_user)

        return compact_generate_response(response)

    @login_required
    def stop_debug_chat(self, app_id: UUID, task_id: UUID):
        """根据传递的应用id+任务id停止某个应用的指定调试会话"""
        self.app_service.stop_debug_chat(app_id, task_id, current_user)
        return success_message("停止应用调试会话成功")

    @login_required
    def get_published_config(self, app_id: UUID):
        """根据传递的应用id获取应用的发布配置信息"""
        published_config = self.app_service.get_published_config(app_id, current_user)
        return success_json(published_config)

    @login_required
    def regenerate_web_app_token(self, app_id: UUID):
        """根据传递的应用id重新生成WebApp凭证标识"""
        token = self.app_service.regenerate_web_app_token(app_id, current_user)
        return success_json({"token": token})

    @login_required
    def get_debug_conversation_messages_with_page(self, app_id: UUID):
        """根据传递的应用id 获取该应用的调试会话分页列表记录"""
        # 1.提取请求并校验数据
        req = GetDebugConversationMessagesWithPageReq(request.args)
        if not req.validate():
            raise validate_error_json(req.errors)

        # 2.调用服务获取数据
        messages, paginator = self.app_service.get_debug_conversation_messages_with_page(app_id, req, current_user)

        # 3.创建响应结构
        resp = GetDebugConversationMessagesWithPageResp(many=True)

        return success_json(PageModel(list=resp.dump(messages), paginator=paginator))

    @login_required
    def ping(self):
        provider = self.language_model_manager.get_provider("openai")
        model_entity = provider.get_model_entity("gpt-4o-mini")
        model_class = provider.get_model_class(model_entity.model_type)
        llm = model_class(**{
            **model_entity.attributes,
            "features": model_entity.features,
            "metadata": model_entity.metadata,
        })
        return success_json({
            "content": llm.invoke("你好").content,
            "features": llm.features,
            "metadata": llm.metadata,
        })