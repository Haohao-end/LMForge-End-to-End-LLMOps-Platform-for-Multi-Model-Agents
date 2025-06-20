import uuid
from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField
from wtforms.validators import DataRequired, UUID, Optional, ValidationError

class OpenAPIChatReq(FlaskForm):
    """开放API聊天接口请求结构体"""
    app_id = StringField("app_id", validators=[
        DataRequired("应用id不能为空"),
        UUID("应用id格式必须为UUID"),
    ])
    end_user_id = StringField("end_user_id", default="", validators=[
        Optional(),
        UUID("终端用户id必须为UUID"),
    ])
    conversation_id = StringField("conversation_id", default="")
    query = StringField("query", default="", validators=[
        DataRequired("用户提问query不能为空"),
    ])
    stream = BooleanField("stream", default=True)

    def validate_conversation_id(self, field: StringField) -> None:
        """自定义校验conversation_id函数"""
        # 1.检测是否传递数据，如果传递了，则类型必须为UUID
        if field.data:
            try:
                uuid.UUID(field.data)
            except Exception as _:
                raise ValidationError("会话id格式必须为UUID")

            # 2.终端用户id是不是为空
            if not self.end_user_id.data:
                raise ValidationError("传递会话id则终端用户id不能为空")
