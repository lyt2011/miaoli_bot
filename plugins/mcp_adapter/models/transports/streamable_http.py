from pydantic	import Field, model_validator
from typing		import Any, Dict, Literal, Self, Union

from .base_transport	import BaseTransport


class StreamableHttpTransport(BaseTransport):
	
	transport: Literal["streamable_http"] = Field(default="streamable_http", description="默认 streamable_http 协议")
	
	url		: str				= Field(..., description="url 就是 url")
	headers	: Dict[str, Any]	= Field(default_factory=dict, description="扩展请求头")
	timeout	: Union[float, int]	= Field(default=30.0, description="调用超时")
	
	
	@model_validator(mode="after")
	def align_timeout_type(self) -> Self:
		
		"""
		官方的类型是 Union[timedelta, float]
		为了方便传参干脆把模型改成 Union[float, int]
		不过在这里转换 int -> float 对齐官方类型
		"""
		
		self.timeout = float(self.timeout)
		
		return self
