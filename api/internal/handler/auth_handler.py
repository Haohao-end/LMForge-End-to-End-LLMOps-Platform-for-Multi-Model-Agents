from dataclasses import dataclass
from injector import inject
from flask_login import login_required, logout_user
from pkg.response import success_message, validate_error_json, success_json
from internal.schema.auth_schema import PasswordLoginResp, PasswordLoginReq
from internal.service import AccountService

@inject
@dataclass
class AuthHandler:
    """LLMOps平台自有授权认证处理器"""
    account_service: AccountService
    def password_login(self):
        """账号密码登陆"""
        # 1.提取请求并校验数据
        req = PasswordLoginReq()
        if not req.validate():
            raise validate_error_json(req.errors)

        # 2.调用服务登陆账号
        credential = self.account_service.password_login(req.email.data, req.password.data)

        # 3.创建响应结构并返回
        resp = PasswordLoginResp()

        return success_json(resp.dump(credential))


    @login_required
    def logout(self):
        """退出登陆 用于提示前端清除授权凭证"""
        logout_user()
        return success_message("退出登陆成功")
