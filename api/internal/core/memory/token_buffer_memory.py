import tiktoken
from typing import List
from sqlalchemy import desc
from dataclasses import dataclass
from pkg.sqlalchemy import SQLAlchemy
from internal.model import Conversation, Message
from internal.entity.conversation_entity import MessageStatus
from langchain_core.messages import AnyMessage, HumanMessage, AIMessage, trim_messages, get_buffer_string


@dataclass
class TokenBufferMemory:
    db: SQLAlchemy
    conversation: Conversation
    encoding_name: str = "cl100k_base"  # 默认 OpenAI 编码

    def count_tokens(self, text: str) -> int:
        """计算 token 数量（确保输入是字符串）"""
        if not isinstance(text, str):
            text = str(text)  # 强制转换非字符串类型
        encoding = tiktoken.get_encoding(self.encoding_name)
        return len(encoding.encode(text))

    def get_history_prompt_messages(
            self,
            max_token_limit: int = 2000,
            message_limit: int = 10,
    ) -> List[AnyMessage]:
        """获取历史消息，并基于 token 数量裁剪"""
        if not self.conversation:
            return []

        # 查询消息（过滤无效状态）
        messages = self.db.session.query(Message).filter(
            Message.conversation_id == self.conversation.id,
            Message.answer != "",
            Message.is_deleted == False,
            Message.status.in_([MessageStatus.NORMAL.value, MessageStatus.STOP.value, MessageStatus.TIMEOUT.value]),
        ).order_by(desc("created_at")).limit(message_limit).all()
        messages = list(reversed(messages))

        # 转换消息并过滤无效内容
        prompt_messages = []
        for message in messages:
            if not message.query or not isinstance(message.query, str):
                continue  # 跳过无效 query
            if not message.answer or not isinstance(message.answer, str):
                continue  # 跳过无效 answer
            prompt_messages.extend([
                HumanMessage(content=message.query),
                AIMessage(content=message.answer),
            ])

        # 裁剪消息（确保 token 不超限）
        return trim_messages(
            messages=prompt_messages,
            max_tokens=max_token_limit,
            token_counter=self.count_tokens,
            strategy="last",
            start_on="human",
            end_on="ai",
        )

    def get_history_prompt_text(self, human_prefix: str = "Human", ai_prefix: str = "AI", **kwargs) -> str:
        """获取历史消息的文本形式"""
        messages = self.get_history_prompt_messages(**kwargs)
        return get_buffer_string(messages, human_prefix, ai_prefix)