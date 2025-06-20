from langchain_community.chat_models.baidu_qianfan_endpoint import QianfanChatEndpoint

from internal.core.language_model.entities.model_entity import BaseLanguageModel


class Chat(QianfanChatEndpoint, BaseLanguageModel):
    """百度千帆聊天模型"""
    pass
