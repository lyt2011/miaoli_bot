from typing		import Any, Dict

from ..parser	import Parser


class FileSegmentParser(Parser):
	
	"""对 File 信息进行解析 转为字典"""
	
	async def is_accept(self, data: Dict[str, Any]) -> bool:
		
		is_accept = (
			data.get("type") == "file"
			and isinstance(data["data"], dict)
			and isinstance(data["data"].get("file"), str)
		)
		
		return is_accept
	
	async def handle(self, data: Dict[str, Any]) -> Dict[str, Any]:
		return {"file": data["data"]["url"] or data["data"]["file"], "size": data["data"]["file_size"]}
