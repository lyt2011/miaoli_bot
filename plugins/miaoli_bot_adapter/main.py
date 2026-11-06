from miaoli_bot.core	import PluginProtocol
from miaoli_bot.consts	import NORMAL, ON_TURN_START
from miaoli_bot.api		import store_set, get_handler_registry

from .models	import PluginConfig
from .nodes		import inject_soul, inject_output_protocol
from .consts	import PLUGIN_CONFIG, RAW_CONFIG, WORKSPACE


class MiaoliBotAdapter(PluginProtocol):
	
	"""把 miaoli_bot 的内部数据适配成图节点可直接消费的形状"""
	
	def __init__(self, *args, **kwargs) -> None:
		super().__init__(*args, **kwargs)
		
		self.undo_list = []
	
	async def on_load(self) -> None:
		
		config = PluginConfig.model_validate(self.config)
		
		registry = get_handler_registry()
		
		self.undo_list.append(store_set(RAW_CONFIG, self.config))
		self.undo_list.append(store_set(PLUGIN_CONFIG, config))
		self.undo_list.append(store_set(WORKSPACE, self.workspace))
		
		# 不启用直接跳过节点与工具注册
		if not config.enable:
			return None
		
		self.undo_list.append(
			registry.on(ON_TURN_START, inject_soul, priority=NORMAL + 1),
		)
		self.undo_list.append(
			registry.on(ON_TURN_START, inject_output_protocol, priority=NORMAL + 1),
		)
	
	async def on_close(self) -> None:
		
		for undo in self.undo_list:
			undo()
