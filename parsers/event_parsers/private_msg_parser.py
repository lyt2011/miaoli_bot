from ...protocols	import Parser

from typing				import Any, Optional, Dict
from datetime			import datetime
from ncatbot.event.qq	import PrivateMessageEvent


class PrivateMessageEventParser(Parser):
	
	async def is_accept(self, data: Any) -> bool:
		return isinstance(data, PrivateMessageEvent)
	
	async def handle(self, data: PrivateMessageEvent) -> Dict[str, Any]:
		
		event_data = {
			"platform"	: "qq",
			"from_group": False,
			"created_at": datetime.now(),
			"sender"	: data.sender.model_dump(),
		}
		
		return event_data