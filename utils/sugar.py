from ncatbot.types.napcat.message	import SendMessageResult

from ..consts	import GROUP_PREFIX, PRIVATE_PREFIX, NCATBOT_API

from typing	import Any, Dict, List, Literal, Optional, Union


def concatenate_id(session_id: str, is_group: bool) -> str:
	"""根据id来源拼接为 来源前缀+id"""
	return f"{GROUP_PREFIX if is_group else PRIVATE_PREFIX}{session_id}"


async def easier_send(
	mode		: Literal["group", "private"],
	chat_id		: Union[str, int],
	ob11_message: List[Dict[str, Any]],
	ncatbot_api	: Optional[Any]	= None
) -> SendMessageResult:
	
	"""更便捷的消息发送 api"""
	
	# 延迟导入 避开 core -> plugin -> utils 的循环
	from ..core	import SHARE_STORE
	
	# 可替换的 ncatbot api 便于测试
	ncatbot_api = ncatbot_api or SHARE_STORE.recall(NCATBOT_API)
	
	if mode == "group":
		coro = (ncatbot_api.qq.messaging.
			send_group_msg(group_id=chat_id, message=ob11_message))
	
	else:
		coro = (ncatbot_api.qq.messaging.
			send_private_msg(user_id=chat_id, message=ob11_message))
	
	return await coro
