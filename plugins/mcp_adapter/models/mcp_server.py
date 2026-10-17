from pydantic	import BaseModel, Field
from typing		import Annotated, Union

from .transports	import StdioTransport, StreamableHttpTransport


Transports = Annotated[
	Union[StreamableHttpTransport, StdioTransport],
	Field(discriminator="transport"),
]


class MCPServer(BaseModel):
	
	name		: str			= Field(..., description="服务器名字")
	reusable	: bool			= Field(default=False, description="是否可复用 (提升对于静态 mcp server 的性能)")
	transport	: Transports	= Field(..., description="传输类型")
