from typing		import Any, Dict
from datetime	import datetime

from ..parser		import Parser
from ...utils		import parse_segments


class GroupMessageEventParser(Parser):
	
	"""群消息事件解析器"""
	
	async def is_accept(self, data: Dict[str, Any]) -> bool:
		
		is_accept = (
			data.get("message_type") == "group"
			and isinstance(data["group_name"], str)
			and isinstance(data["group_id"], (int, str))
			and isinstance(data["sender"], dict)
			and isinstance(data["message"], list)
		)
		
		return is_accept
	
	async def handle(self, data: Dict[str, Any]) -> Dict[str, Any]:
		
		event_data: Dict[str, Any] = {
			"platform"	: "qq",
			"from_group": True,
			"created_at": datetime.now().isoformat(timespec="seconds"),
			"group_name": data["group_name"],
			"group_id"	: data["group_id"],
			"sender"	: data["sender"],
			"messages"	: await parse_segments(data["message"]),
		}
		
		return event_data
