from pydantic	import BaseModel, Field, model_validator
from typing		import Optional, Literal, Self


SUPPORT_ENCODER	= Literal["o200k_base", "cl100k_base"]


class CalculateConfig(BaseModel):
	
	"""
	base代表使用我硬编码在代码里的公式进行估算
	package代表使用外部包进行估算
	"""
	
	mode		: Literal["base", "tiktoken"]	= Field(default="base", description="估算方式")
	encoder		: Optional[SUPPORT_ENCODER]		= Field(default=None, description="要使用的编码器")
	
	
	@model_validator(mode="after")
	def check_tiktoken(self) -> Self:
		
		if self.mode == "tiktoken" and not self.encoder:
			raise ValueError(f"使用 {self.mode} 时必须填 encoder")
		
		return self