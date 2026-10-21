from pydantic	import BaseModel, Field, model_validator
from typing		import Optional, Self


class SplitConfig(BaseModel):
	
	"""输出分割配置"""
	
	enable		: bool			= Field(default=True, description="是否启用分割")
	delimiter	: Optional[str]	= Field(default=None, description="分隔符")
	
	
	@model_validator(mode="after")
	def ensure_delimiter(self) -> Self:
		
		if self.enable and not self.delimiter:
			raise ValueError("启用分割时分隔符必须要有内容")
		
		return self
