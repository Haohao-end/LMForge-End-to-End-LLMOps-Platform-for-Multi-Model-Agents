from langchain_community.chat_models.tongyi import ChatTongyi
from internal.core.language_model.entities.model_entity import BaseLanguageModel


class Chat(ChatTongyi, BaseLanguageModel):
    """通义千问聊天模型"""
    pass
