from pydantic	import BaseModel, Field, DirectoryPath

from typing	import Dict, List


class SubPluginConfig(BaseModel):
	
	"""子插件配置"""
	
	enable		: bool					= Field(default=False, description="是否加载插件")
	load_from	: List[DirectoryPath]	= Field(default_factory=list, description="插件加载目录")
	overwrite	: Dict[str, dict]		= Field(default_factory=dict, description="覆写子插件配置")
