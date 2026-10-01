from typing				import Any, Dict
from miaoli_bot			import Parser
from ncatbot.types.qq	import QQImage




class QQImageSegmentParser(Parser):
	
	"""对 Image 信息进行解析 转为字典"""
	
	async def is_accept(self, data: Any) -> bool:
		return isinstance(data, QQImage)
	
	async def handle(self, data: Any) -> Dict[str, Any]:
		
		image	: str	= data.url or data.file
		size	: int	= data.file_size
		is_meme	: bool	= bool(data.sub_type)
		
		return {"image": image, "size": size, "is_meme": is_meme}