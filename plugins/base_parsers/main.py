from miaoli_bot.protocols	import PluginProtocol
from miaoli_bot.core		import Registry

from typing				import Any, Dict

from .segment_parsers	import (
	AtSegmentParser,
	TextSegmentParser,
	ImageSegmentParser,
	FileSegmentParser,
	ReplySegmentParser,
)
from .event_parsers	import (
	GroupMessageEventParser,
	PrivateMessageEventParser,
)
	

class BaseParsers(PluginProtocol):
	
	"""基础解析器 保证信息正常解析"""

	def __init__(self, config: Dict[str, Any], registry: Registry) -> None:
		super().__init__(config, registry)
	
	async def on_load(self) -> None:
				
		self.registry.register_segment_parser(AtSegmentParser())
		self.registry.register_segment_parser(TextSegmentParser())
		self.registry.register_segment_parser(ImageSegmentParser())
		self.registry.register_segment_parser(FileSegmentParser())
		self.registry.register_segment_parser(ReplySegmentParser())
		
		self.registry.register_event_parser(GroupMessageEventParser())
		self.registry.register_event_parser(PrivateMessageEventParser())
	
	async def on_close(self) -> None: ...