from miaoli_bot.core	import PluginProtocol
from miaoli_bot.consts	import NORMAL, ON_AGENT_START
from miaoli_bot.api		import store_recall, store_set, register_tool, get_handler_registry

from .models	import PluginConfig
from .nodes		import inject_helper
from .tools		import deepseek_search, lang_search
from .consts	import PLUGIN_CONFIG, RAW_CONFIG, CLIENT_SESSION

import aiohttp


TOOL_MAPPING = {
	"langsearch": lang_search,
	"deepseek": deepseek_search,
}


class WebSearch(PluginProtocol):
	
	"""联网搜索工具"""
	
	def __init__(self, *args, **kwargs) -> None:
		super().__init__(*args, **kwargs)
		
		self.undo_list = []
	
	async def on_load(self) -> None:
		
		config = PluginConfig.model_validate(self.config)
		
		self.undo_list.append(store_set(PLUGIN_CONFIG, config))
		self.undo_list.append(store_set(RAW_CONFIG, self.config))
		self.undo_list.append(store_set(CLIENT_SESSION, aiohttp.ClientSession()))
		
		# 不启用直接跳过工具与节点注册
		if not config.enable:
			return None
		
		# 根据实际需求注册工具
		self.undo_list.append(register_tool(TOOL_MAPPING[config.adapter]))
		
		# 把使用说明写进提示词段 提高搜索倾向
		self.undo_list.append(get_handler_registry().on(ON_AGENT_START, inject_helper, priority=NORMAL))
	
	async def on_close(self) -> None:
		
		client_session = store_recall(CLIENT_SESSION)
		
		for undo in self.undo_list:
			undo()
		
		# 丢完再关闭 防止中途报错导致键残留
		await client_session.close()
