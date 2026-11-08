from pydantic	import BaseModel, Field


class GraphConfig(BaseModel):
	
	atimeout: float	= Field(default=60.0, description="跑图的超时时间")
