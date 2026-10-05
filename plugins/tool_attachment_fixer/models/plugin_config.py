from typing		import List
from pydantic	import BaseModel, Field

class PluginConfig(BaseModel):
	
	enable: bool = Field(default=True, description="设置插件启用状态")
	
	models		: List[str]	= Field(default_factory=list, description="目标模型")
	replace_text: str		= Field(default="该工具产生附件已被添加进入上下文中。", description="用于修复工具结果的content的文本")
