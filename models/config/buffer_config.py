from pydantic	import BaseModel, Field


class BufferConfig(BaseModel):
	
	size: int = Field(default=30, description="事件缓冲区容量")