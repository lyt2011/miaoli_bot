from pydantic	import BaseModel, Field


class BaseTransport(BaseModel):
	"""transport 基类"""
	transport	: str	= Field(..., description="传输方式")
	reusable	: bool	= Field(default=False, exclude=True, description="是否可复用 (提升对于静态 mcp server 的性能)")