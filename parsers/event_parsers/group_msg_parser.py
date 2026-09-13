from ...protocols	import Parser

from typing				import Any, Optional, Dict
from datetime			import datetime
from ncatbot.event.qq	import GroupMessageEvent


class GroupMessageEventParser(Parser):
	
	async def is_accept(self, data: Any) -> bool:
		return isinstance(data, GroupMessageEvent)
	
	async def handle(self, data: GroupMessageEvent) -> Dict[str, Any]:
		
		event_data = {
			"platform"	: "qq",
			"from_group": True,
			"created_at": datetime.now().isoformat(timespec="seconds"),
			"group_name": data.group_name,
			"group_id"	: data.group_id,
			"sender"	: data.sender.model_dump(),
		}
		
		return event_data