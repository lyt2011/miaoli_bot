from ..protocols	import Handler

from typing	import Any, Optional, Dict
from time	import time as ctime_stamp


class GroupMessageEventHandler(Handler):
	
	async def is_accept(self, data: Any) -> bool:
		return hasattr(data, "is_group_msg") and data.is_group_msg()
	
	async def handle(self, data: Any) -> Optional[Dict[str, Any]]:
		
		if not hasattr(data, "sender"):
			return None
		
		if not hasattr(data, "message"):
			return None
		
		if not hasattr(data, "group_id"):
			return None
		
		if not hasattr(data, "group_name"):
			return None
		
		real_msg = {
			"platform": "qq",
			"created_at": data.time if hasattr(data, "time") else ctime_stamp(),
			"is_group_msg": hasattr(data, "is_group_msg") and data.is_group_msg(),
			"group_id": data.group_id,
			"group_name": data.group_name,
			"segments": [msg.model_dump() for msg in data.message],
			"sender": data.sender.model_dump(),
		}
		
		return real_msg