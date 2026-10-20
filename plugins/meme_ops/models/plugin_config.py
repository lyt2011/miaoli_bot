from pydantic	import BaseModel, Field, model_validator
from typing		import Optional, Self
from pathlib	import Path


class PluginConfig(BaseModel):
	
	enable	: bool			= Field(default=False, description="是否启用 meme")
	helper_path	: Optional[str]	= Field(default=None, description="表情包扩展帮助文档文件")
	encoding	: str			= Field(default="utf-8", description="文件编码")
	db_path		: Optional[str]	= Field(default=None, description="meme 的 sql 数据库路径")
		
	@property
	def helper(self) -> str:
		return Path(self.helper_path).read_text(encoding=self.encoding)
	
	@model_validator(mode="after")
	def check_db_path(self) -> Self:
		
		"""可以关闭+传路径 但不能启用+不传路径"""
		
		if self.enable is True and not self.db_path:
			raise ValueError("不能启用 meme 但不传数据库路径")
		
		return self
	
	@model_validator(mode="after")
	def init_helper(self) -> Self:
		
		"""确保插件被启用时帮助文档路径已配置"""
		
		if self.enable and not self.helper_path:
			raise ValueError("插件被启用但帮助文档不存在")
				
		return self