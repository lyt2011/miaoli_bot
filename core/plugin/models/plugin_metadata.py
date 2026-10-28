from typing		import List
from pydantic	import BaseModel, Field

from .dependence	import Dependence


class PluginMetadata(BaseModel):
	
	name		: str				= Field(..., description="插件名")
	entry_class	: str				= Field(..., description="入口类名", min_length=1)
	description	: str				= Field(default="", description="插件描述")
	dependences	: List[Dependence]	= Field(default_factory=list, description="插件依赖")
