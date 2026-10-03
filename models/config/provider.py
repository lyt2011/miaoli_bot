from pydantic	import BaseModel, Field
from typing		import List, Literal, Dict


Vision		= Literal["image", "video", "text", "audio"]
Protocol	= Literal["openai-completions", "openai-response"]


class LLM(BaseModel):
	protocol		: Protocol		= Field(..., description="协议")
	context_window	: int			= Field(default=128000, description="上下文窗口")
	max_tokens		: int			= Field(default=4096, description="最大输出")
	support_visions	: List[Vision]	= Field(default_factory=list, description="模型支持的模态输入", min_length=1)
	

class Provider(BaseModel):
	base_url	: str				= Field(..., description="请求的地址")
	api_key		: str				= Field(..., description="鉴权密钥")
	models		: Dict[str, LLM]	= Field(default_factory=dict, description="模型配置", min_length=1)