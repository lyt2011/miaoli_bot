from miaoli_bot.core	import PluginProtocol
from miaoli_bot.api		import get_handler_registry
from miaoli_bot.consts	import NORMAL, ON_BEFORE_REQUEST

from .nodes	import build_prompt


class PromptBuilder(PluginProtocol):
	
	"""把 state 里的提示词段拼成一条系统消息，插到消息列表最前面"""
	
	def __init__(self, *args, **kwargs) -> None:
		super().__init__(*args, **kwargs)
		
		self.undo_list = []
	
	async def on_load(self) -> None:
		
		registry = get_handler_registry()
		
		self.undo_list = [
			registry.on(ON_BEFORE_REQUEST, build_prompt, priority=NORMAL + 1),
		]
	
	async def on_close(self) -> None:
		
		for undo in self.undo_list:
			undo()
