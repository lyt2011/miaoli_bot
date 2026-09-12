from ncatbot.event.qq	import MessageEvent
from typing				import Optional


def get_id_from_event(event: MessageEvent) -> Optional[str]:
	
	"""
	从 MessageEvent (及他的子类) 中获取 id **有执行顺序**
	GroupMessageEvent -> group_id
	PrivateMessageEvent -> sender.user_id
	"""
	
	if hasattr(event, "group_id"):
		return event.group_id
	
	if hasattr(event, "sender"):
		if hasattr(event.sender, "user_id"):
			return event.sender.user_id
	
	return None