from ..protocols	import Handler

from typing	import Any, Optional, Dict
from time	import time as ctime_stamp


class PrivateMessageEventHandler(Handler):
	
	"""
	我再也不相信前端传进来的任何东西了😭😭
	"""
	
	async def is_accept(self, data: Any) -> bool:
		return hasattr(data, "is_group_msg") and not data.is_group_msg()
	
	async def handle(self, data: Any) -> Optional[Dict[str, Any]]:
		
		if not hasattr(data, "sender"):
			return None
		
		if not hasattr(data, "message"):
			return None
		
		real_msg = {
			"platform": "qq",
			"created_at": data.time if hasattr(data, "time") else ctime_stamp(),
			"is_group_msg": hasattr(data, "is_group_msg") and data.is_group_msg(),
			"sender": data.sender.model_dump(),
			"segments": [msg.model_dump() for msg in data.message],
		}
		
		return real_msg