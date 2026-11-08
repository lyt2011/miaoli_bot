from pydantic	import BaseModel, Field

from .llm_config			import LLMConfig
from .channel_setting		import ChannelSetting
from .sub_plugin_config		import SubPluginConfig
from .checkpointer_config	import CheckpointerConfig


class PluginConfig(BaseModel):
	
	llm			: LLMConfig				= Field(..., description="大语言模型配置")
	checkpointer: CheckpointerConfig	= Field(default_factory=CheckpointerConfig, description="check_pointer 数据库配置")
	sub_plugin	: SubPluginConfig		= Field(default_factory=SubPluginConfig, description="插件配置")
	channel		: ChannelSetting		= Field(default_factory=ChannelSetting, description="渠道设置")
