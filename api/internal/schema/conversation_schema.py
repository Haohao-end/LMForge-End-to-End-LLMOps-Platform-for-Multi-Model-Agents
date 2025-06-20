from flask_wtf import FlaskForm
from marshmallow import Schema, fields, pre_dump
from wtforms import IntegerField, StringField, BooleanField
from wtforms.validators import Optional, NumberRange, DataRequired, Length
from internal.lib.helper import datetime_to_timestamp
from internal.model import Message
from pkg.paginator import PaginatorReq


class GetConversationMessagesWithPageReq(PaginatorReq):
    """获取指定会话消息列表分页数据请求结构"""
    created_at = IntegerField("created_at", default=0, validators=[
        Optional(),
        NumberRange(min=0, message="created_at游标最小值为0")
    ])


class GetConversationMessagesWithPageResp(Schema):
    """获取指定会话消息列表分页数据响应结构"""
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


class UpdateConversationNameReq(FlaskForm):
    """更新会话名字请求结构体"""
    name = StringField("name", validators=[
        DataRequired(message="会话名字不能为空"),
        Length(max=100, message="会话名字长度不能超过100个字符")
    ])


class UpdateConversationIsPinnedReq(FlaskForm):
    """更新会话置顶选项请求请求结构体"""
    is_pinned = BooleanField("is_pinned", default=False)
