from pydantic	import BaseModel, Field, model_validator
from typing		import Self

from .database_config	import DatabaseConfig
from .help_doc_config	import HelpDocConfig

class PluginConfig(BaseModel):
	
	enable		: bool				= Field(default=False, description="是否启用 meme")
	database	: DatabaseConfig	= Field(default_factory=DatabaseConfig, description="meme 的 sql 数据库配置")
	help_doc	: HelpDocConfig		= Field(default_factory=HelpDocConfig, description="表情包扩展帮助文档配置")
	
	@model_validator(mode="after")
	def check_db_path(self) -> Self:
		
		"""可以关闭+传路径 但不能启用+不传路径"""
		
		if self.enable and not self.database.path:
			raise ValueError("不能启用 meme 但不传数据库路径")
		
		return self
	
	@model_validator(mode="after")
	def check_doc_path(self) -> Self:
		
		"""确保插件被启用时帮助文档路径已配置"""
		
		if self.enable and not self.help_doc.path:
			raise ValueError("插件被启用但帮助文档不存在")
				
		return self
