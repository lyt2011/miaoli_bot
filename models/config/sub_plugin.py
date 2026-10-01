from pydantic	import BaseModel, Field
from typing		import Optional
from pathlib	import Path


class SubPluginConfig(BaseModel):
	is_enable: bool				= Field(default=False, description="是否加载插件")
	load_from: Optional[Path]	= Field(default=None, description="插件加载目录")