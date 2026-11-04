from miaoli_bot.core	import PluginProtocol
from miaoli_bot.consts	import NORMAL, ON_BEFORE_REQUEST
from miaoli_bot.api		import store_drop, store_set, get_handler_registry

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
		
		store_set(PLUGIN_CONFIG, config)
		store_set(RAW_CONFIG, self.config)
		
		self.undo_list = []  # 关闭时 on_close 也要能遍历
		# 不启用直接跳过节点注册
		if not config.enable:
			return None
		
		# 必须早于 prompt_builder 的 NORMAL + 1（数值大者先跑），否则拼装时读不到本轮增删的段
		self.undo_list = [
			registry.on(ON_BEFORE_REQUEST, recognize_intent, priority=NORMAL + 2),
		]
	
	async def on_close(self) -> None:
		
		for undo in self.undo_list:
			undo()
		
		store_drop(PLUGIN_CONFIG)
		store_drop(RAW_CONFIG)
