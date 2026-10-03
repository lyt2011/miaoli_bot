from pydantic	import BaseModel, Field


class PluginConfig(BaseModel):
	
	enable		: bool	= Field(default=True, description="设置插件启用状态")
	fix_message	: str	= Field(default="工具未被执行（上一轮中断或并发冲突），如需该结果请重新调用", description="合成给模型的工具结果文本")
