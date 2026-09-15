from ...protocols	import Parser

from typing			import Any, Dict, Any
from ncatbot.types	import Image


class ImageSegmentParser(Parser):
	
	"""对 Image 信息进行解析 转为字典"""
	
	async def is_accept(self, data: Any) -> bool:
		return isinstance(data, Image)
	
	async def handle(self, data: Any) -> Dict[str, Any]:
		return {"image": data.url or data.file, "size": data.file_size}