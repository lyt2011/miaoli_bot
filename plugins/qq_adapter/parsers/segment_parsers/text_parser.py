from typing		import Any, Dict

from ..parser	import Parser


class TextSegmentParser(Parser):
	
	"""对 PlainText 信息进行解析 转为字典"""
	
	async def is_accept(self, data: Dict[str, Any]) -> bool:
		
		is_accept = (
			data.get("type") == "text"
			and isinstance(data["data"], dict)
			and isinstance(data["data"].get("text"), str)
		)
		
		return is_accept
	
	async def handle(self, data: Dict[str, Any]) -> Dict[str, Any]:
		return {"text": data["data"]["text"]}
