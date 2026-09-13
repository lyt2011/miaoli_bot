from ...protocols	import Parser

from typing			import Any, Dict
from ncatbot.types	import PlainText


class TextSegmentParser(Parser):
	
	async def is_accept(self, data: Any) -> bool:
		return isinstance(data, PlainText)
	
	async def handle(self, data: Any) -> Dict[str, Any]:
		return {"text": data.text}