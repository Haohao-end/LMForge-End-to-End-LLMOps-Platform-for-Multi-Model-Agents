from flask_wtf import FlaskForm
from marshmallow import Schema, fields, pre_dump
from wtforms import StringField, IntegerField
from wtforms.validators import DataRequired, Optional, NumberRange
from internal.lib.helper import datetime_to_timestamp
from internal.model import Message
from pkg.paginator import PaginatorReq


class AssistantAgentChat(FlaskForm):
    """辅助Agent会话请求结构体"""
    query = StringField("query", validators=[
        DataRequired("用户提问query不能为空")
    ])


class GetAssistantAgentMessagesWithPageReq(PaginatorReq):
    """获取辅助智能体消息列表分页请求"""
    created_at = IntegerField("created_at", default=0, validators=[
        Optional(),
        NumberRange(min=0, message="created_at游标最小值为0")
    ])


class GetAssistantAgentMessagesWithPageResp(Schema):
    """获取辅助智能体消息列表分页响应结构"""
    id = fields.UUID(dump_default="")
    conversation_id = fields.UUID(dump_default="")
    query = fields.String(dump_default="")
    answer = fields.String(dump_default="")
    total_token_count = fields.Integer(dump_default=0)
    latency = fields.Float(dump_default=0)
    agent_thoughts = fields.List(fields.Dict, dump_default=[])
    created_at = fields.Integer(dump_default=0)

    @pre_dump
    def process_data(self, data: Message, **kwargs):
        return {
            "id": data.id,
            "conversation_id": data.conversation_id,
            "query": data.query,
            "answer": data.answer,
            "total_token_count": data.total_token_count,
            "latency": data.latency,
            "agent_thoughts": [{
                "id": agent_thought.id,
                "position": agent_thought.position,
                "event": agent_thought.event,
                "thought": agent_thought.thought,
                "observation": agent_thought.observation,
                "tool": agent_thought.tool,
                "tool_input": agent_thought.tool_input,
                "latency": agent_thought.latency,
                "created_at": datetime_to_timestamp(agent_thought.created_at),
            } for agent_thought in data.agent_thoughts],
            "created_at": datetime_to_timestamp(data.created_at),
        }
