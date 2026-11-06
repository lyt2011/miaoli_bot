from miaoli_bot.core	import PluginProtocol
from miaoli_bot.consts	import NORMAL, ON_TURN_START
from miaoli_bot.api		import store_set, get_handler_registry

from .models	import PluginConfig
from .nodes		import recognize_intent
from .consts	import PLUGIN_CONFIG, RAW_CONFIG


class IntentRecognition(PluginProtocol):
	
	"""识别用户意图，据此增删提示词段"""
	
	def __init__(self, *args, **kwargs) -> None:
		super().__init__(*args, **kwargs)
		
		self.undo_list = []
	
	async def on_load(self) -> None:
		
		config = PluginConfig.model_validate(self.config)
		
		registry = get_handler_registry()
		
		self.undo_list.append(store_set(PLUGIN_CONFIG, config))
		self.undo_list.append(store_set(RAW_CONFIG, self.config))
		
		# 不启用直接跳过节点注册
		if not config.enable:
			return None
		
		# 必须早于 prompt_builder 的 NORMAL + 1（数值大者先跑），否则拼装时读不到本轮增删的段
		self.undo_list.append(
			registry.on(ON_TURN_START, recognize_intent, priority=NORMAL),
		)
	
	async def on_close(self) -> None:
		
		for undo in self.undo_list:
			undo()
