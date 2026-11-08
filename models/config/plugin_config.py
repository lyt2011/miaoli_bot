from pydantic	import BaseModel, Field

from .llm_config			import LLMConfig
from .tick_config			import TickConfig
from .graph_config			import GraphConfig
from .channel_config		import ChannelConfig
from .sub_plugin_config		import SubPluginConfig
from .checkpointer_config	import CheckpointerConfig


class PluginConfig(BaseModel):
	
	llm			: LLMConfig				= Field(..., description="大语言模型配置")
	tick		: TickConfig			= Field(default_factory=TickConfig, description="主动唤醒配置")
	graph		: GraphConfig			= Field(default_factory=GraphConfig, description="跑图配置")
	checkpointer: CheckpointerConfig	= Field(default_factory=CheckpointerConfig, description="check_pointer 数据库配置")
	sub_plugin	: SubPluginConfig		= Field(default_factory=SubPluginConfig, description="插件配置")
	channel		: ChannelConfig			= Field(default_factory=ChannelConfig, description="渠道设置")
