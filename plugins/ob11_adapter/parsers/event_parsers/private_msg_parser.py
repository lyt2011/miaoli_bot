from typing		import Any, Dict
from datetime	import datetime

from ..parser		import Parser
from ...utils		import parse_segments


class PrivateMessageEventParser(Parser):
	
	"""私聊消息事件解析器"""
	
	async def is_accept(self, data: Dict[str, Any]) -> bool:
		
		is_accept = (
			data.get("message_type") == "private"
			and isinstance(data["sender"], dict)
			and isinstance(data["message"], list)
		)
		
		return is_accept
	
	async def handle(self, data: Dict[str, Any]) -> Dict[str, Any]:
		
		event_data: Dict[str, Any] = {
			"platform"	: "qq",
			"from_group": False,
			"created_at": datetime.now().isoformat(timespec="seconds"),
			"sender"	: data["sender"],
			"messages"	: await parse_segments(data["message"]),
		}
		
		return event_data
