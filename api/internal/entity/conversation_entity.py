from pydantic import BaseModel, Field
from enum import Enum
# 摘要汇总模板
SUMMARIZER_TEMPLATE = """逐步总结提供的对话内容，在之前的总结基础上继续添加并返回一个新的总结。

EXAMPLE
当前总结:
人类询问 AI 对人工智能的看法。AI 认为人工智能是一股向善的力量。

新的会话:
Human: 为什么你认为人工智能是一股向善的力量？
AI: 因为人工智能将帮助人类发挥他们全部的潜力。

新的总结:
人类询问AI对人工智能的看法，AI认为人工智能是一股向善的力量，因为它将帮助人类发挥全部潜力。
END OF EXAMPLE

当前总结:
{summary}

新的会话:
{new_lines}

新的总结:"""

# 会话名字提示模板
CONVERSATION_NAME_TEMPLATE = "请从用户传递的内容中提取出对应的主题"

# 建议问题提示词模板
SUGGESTED_QUESTIONS_TEMPLATE = "请根据传递的历史信息预测人类最后可能会问的三个问题"

class ConversationInfo(BaseModel):
    """你需要将用户的输入分解为“主题”和“意图”，以便准确识别用户输入的类型。
    注意：用户的语言可能是多样性的，可以是英文、中文、日语、法语等。
    确保你的输出与用户的语言尽可能一致并简短！

    示例1：
    用户输入: hi, my name is LiHua.
    {
        "language_type": "用户的输入是纯英文",
        "reasoning": "输出语言必须是英文",
        "subject": "Users greet me"
    }

    示例2:
    用户输入: hello
    {
        "language_type": "用户的输入是纯英文",
        "reasoning": "输出语言必须是英文",
        "subject": "Greeting myself"
    }

    示例3:
    用户输入: www.wsj.com讲了什么
    {
        "language_type": "用户输入是中英文混合",
        "reasoning": "英文部分是URL，主要意图还是使用中文表达的，所以输出语言必须是中文",
        "subject": "询问网站www.wsj.com"
    }

    示例4:
    用户输入: why小红的年龄is老than小明?
    {
        "language_type": "用户输入是中英文混合",
        "reasoning": "英文部分是口语化输入，主要意图是中文，且中文占据更大的实际意义，所以输出语言必须是中文",
        "subject": "询问小红和小明的年龄"
    }

    示例5:
    用户输入: yo, 你今天怎么样?
    {
        "language_type": "用户输入是中英文混合",
        "reasoning": "英文部分是口语化输入，主要意图是中文，所以输出语言必须是中文",
        "subject": "询问我今天的状态"
    }"""
    language_type: str = Field(description="用户输入语言的语言类型声明")
    reasoning: str = Field(description="对用户输入的文本进行语言判断的推理过程，类型为字符串")
    subject: str = Field(description=(
        "对用户的输入进行简短的总结，提取输入的“意图”和“主题”，"
        "输出语言必须和输入语言保持一致，尽可能简单明了，"
        "尤其是用户问题针对模型本身时，可以通过适当的方式加入趣味性。"
    ))

class SuggestedQuestions(BaseModel):
    """请帮我预测人类最可能会问的三个问题，并且每个问题都保持在50个字符以内。
    生成的内容必须是指定模式的JSON格式数组: ["问题1", "问题2", "问题3"]"""
    questions: list[str] = Field(description="建议问题列表，类型为字符串数组")

class InvokeFrom(str, Enum):
    """会话调用来源"""
    SERVICE_API = "service_api"  # 开放api服务调用
    WEB_APP = "web_app"  # web应用
    DEBUGGER = "debugger"  # 调试页面
    ASSISTANT_AGENT = "assistant_agent"  # 辅助Agent调用


class MessageStatus(str, Enum):
    """会话状态"""
    NORMAL = "normal"  # 正常
    STOP = "stop"  # 停止
    TIMEOUT = "timeout"  # 超时
    ERROR = "error"  # 出错


