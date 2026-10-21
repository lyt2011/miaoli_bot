from pydantic	import BaseModel, Field
from typing		import Union


class TypingConfig(BaseModel):
	
	"""
	打字速度配置
	0速度和 enable = False 的效果一样
	"""
	
	enable		: bool				= Field(default=True, description="是否启用打字速度")
	base_speed	: Union[int, float]	= Field(default=0, description="单个字的打字速度")
	speed_offset: Union[int, float]	= Field(default=0, description="速度偏移")
	
