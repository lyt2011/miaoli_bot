from ...protocols	import Parser

from typing			import Any, Dict
from ncatbot.types	import File


class FileSegmentParser(Parser):
	
	"""对 File 信息进行解析 转为字典"""
	
	async def is_accept(self, data: Any) -> bool:
		return isinstance(data, File)
	
	async def handle(self, data: Any) -> Dict[str, Any]:
		return {"file": data.url or data.file, "size": data.file_size}