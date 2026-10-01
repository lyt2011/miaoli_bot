from pydantic	import BaseModel, Field
from typing		import List, Literal


Vision		= Literal["image", "video", "tool_calling", "text", "audio"]
Protocol	= Literal["openai-completion", "openai-response"]


class LLM(BaseModel):
	name			: str			= Field(..., description="用于请求的模型名")
	context_window	: int			= Field(default=128000, description="上下文窗口")
	max_tokens		: int			= Field(default=4096, description="最大输出")
	visions			: List[Vision]	= Field(default_factory=list, description="模型支持的模态输入")
	protocol		: Protocol		= Field(default="OpenAI", description="协议")

class Provider(BaseModel):
	name		: str		= Field(..., description="供应商名字")
	base_url	: str		= Field(..., description="请求的地址 不会拼路径")
	api_key		: str		= Field(..., description="鉴权密钥")
	models		: List[LLM] = Field(default_factory=list, description="模型列表")