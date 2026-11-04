from pydantic	import BaseModel, Field

from typing	import List, Literal


Vision	= Literal["image", "video", "text", "audio"]
Client	= Literal["openai", "deepseek", "anthropic"]


class LLM(BaseModel):
	
	"""大模型信息配置"""
	
	name			: str			= Field(..., description="模型名称")
	context_window	: int			= Field(..., description="上下文窗口", ge=65535)
	max_tokens		: int			= Field(..., description="最大输出", ge=2048)
	support_visions	: List[Vision]	= Field(..., description="模型支持的模态输入", min_length=1)

class Provider(BaseModel):
	
	"""供应商配置"""
	
	name	: str		= Field(..., description="供应商名字")	
	base_url: str		= Field(..., description="请求的地址")
	api_key	: str		= Field(..., description="鉴权密钥")
	client	: Client	= Field(..., description="客户端配置 决定使用的适配器")
	models	: List[LLM]	= Field(default_factory=list, description="模型配置")
