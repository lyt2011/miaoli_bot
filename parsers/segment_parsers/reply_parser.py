from ...protocols	import Parser

from typing			import Any, Dict, Any
from ncatbot.types	import Reply


class ReplySegmentParser(Parser):
	
	"""对 Reply 信息进行解析 转为字典"""
	
	async def is_accept(self, data: Any) -> bool:
		return isinstance(data, Reply)
	
	async def handle(self, data: Any) -> Dict[str, Any]:
		return {"reply": data.id}