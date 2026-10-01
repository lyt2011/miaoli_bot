from pydantic	import BaseModel, Field, model_validator
from typing		import Union, Optional, Self


class OutputConfig(BaseModel):
	split_separator		: Optional[str]		= Field(default=None, description="输出分隔符")
	typing_speed		: Union[int, float]	= Field(default=0.01, description="打字时间 (一个字)")
	typing_speed_offset	: Union[int, float]	= Field(default=0, description="打字速度偏移")
	
	@model_validator(mode="after")
	def ensure_separator(self) -> Self:
		
		if isinstance(self.split_separator, str) and not self.split_separator:
			raise ValueError("分割符必须大于1个字符 或不填写 split_separator")
		
		return self