from pydantic	import BaseModel, Field


class BaseTransport(BaseModel):
	"""transport 基类"""
	transport	: str	= Field(..., description="传输方式")
