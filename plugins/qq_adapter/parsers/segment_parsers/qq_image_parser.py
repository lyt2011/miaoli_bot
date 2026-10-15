from typing		import Any, Dict

from ..parser	import Parser


class QQImageSegmentParser(Parser):
	
	"""对 Image 信息进行解析 转为字典"""
	
	async def is_accept(self, data: Dict[str, Any]) -> bool:
		
		is_accept = (
			data.get("type") == "image"
			and isinstance(data["data"], dict)
			and isinstance(data["data"].get("file"), str)
		)
		
		return is_accept
	
	async def handle(self, data: Dict[str, Any]) -> Dict[str, Any]:
		
		image	: str	= data["data"]["url"] or data["data"]["file"]
		size	: int	= data["data"]["file_size"]
		sub_tp	: int	= data["data"]["sub_type"]
		
		return {"image": image, "size": size, "sub_tp": sub_tp}
