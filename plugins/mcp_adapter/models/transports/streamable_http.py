from pydantic	import Field

from .base_transport	import BaseTransport

from typing	import Any, Dict, Literal


class StreamableHttpTransport(BaseTransport):
	
	transport: Literal["streamable_http"] = Field(default="streamable_http", description="默认 streamable_http 协议")
	
	url		: str				= Field(..., description="url 就是 url")
	headers	: Dict[str, Any]	= Field(default_factory=dict, description="扩展请求头")

	timeout: float	= Field(default=30.0, description="调用超时")
