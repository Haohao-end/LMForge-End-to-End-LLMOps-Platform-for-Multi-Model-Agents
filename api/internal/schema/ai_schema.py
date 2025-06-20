from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.validators import DataRequired, UUID, Length

class OptimizePromptReq(FlaskForm):
    """优化预设prompt请求结构体"""
    prompt = StringField("prompt", validators=[
        DataRequired("预设prompt不能为空"),
        Length(max=2000, message="预设prompt的长度不能超过2000个字符")
    ])

class GenerateSuggestedQuestionsReq(FlaskForm):
    """生成建议问题列表请求结构体"""
    message_id = StringField("message_id", validators=[
        DataRequired("消息id不能为空"),
        UUID(message="消息id格式必须为uuid")
    ])



