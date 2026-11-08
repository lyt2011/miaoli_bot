from pydantic	import BaseModel, Field


class ChannelConfig(BaseModel):
	
	atimeout: float	= Field(default=30.0, description="获取新信息的超时时间")
