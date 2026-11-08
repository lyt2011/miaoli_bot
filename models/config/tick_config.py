from pydantic	import BaseModel, Field


class TickConfig(BaseModel):
	
	interval: float	= Field(default=60.0, gt=0, description="主动唤醒间隔（秒）")
