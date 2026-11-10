from pydantic	import BaseModel, Field

from pathlib	import Path
from typing		import Optional


class PluginConfig(BaseModel):
	
	"""时间注入配置"""
	
	enable		: bool				= Field(default=True, description="设置插件启用状态")
	interval	: float				= Field(default=60.0, description="注入的间隔，单位秒")
	template	: Optional[Path]	= Field(default=None, description="提示词模板文件路径，留空则使用内置模板")
	encoding	: str				= Field(default="utf-8", description="读取模板文件时使用的编码")
