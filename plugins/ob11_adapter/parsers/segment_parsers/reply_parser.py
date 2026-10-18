from typing		import Any, Dict

from ..parser	import Parser


class ReplySegmentParser(Parser):
	
	"""对 Reply 信息进行解析 转为字典"""
	
	async def is_accept(self, data: Dict[str, Any]) -> bool:
		
		is_accept = (
			data.get("type") == "reply"
			and isinstance(data["data"], dict)
			and isinstance(data["data"].get("id"), str)
		)
		
		return is_accept
	
	async def handle(self, data: Dict[str, Any]) -> Dict[str, Any]:
		return {"reply": data["data"]["id"]}
