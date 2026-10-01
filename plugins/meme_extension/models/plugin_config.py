from pydantic	import BaseModel, Field, model_validator
from typing		import Optional, Self


class PluginConfig(BaseModel):
	is_enable	: bool			= Field(default=False, description="是否启用 meme")
	db_path		: Optional[str]	= Field(default=None, description="meme 的 sql 数据库路径")
	
	@model_validator(mode="after")
	def check_path(self) -> Self:
		
		"""
		可以关闭+传路径
		但不能启用+不传路径
		"""
		
		if self.is_enable is True and not self.db_path:
			raise ValueError("不能启用 meme 但不传数据库路径")
		
		return self