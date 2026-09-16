from ..stores	import SHARE_STORE
from ..consts	import NCATBOT_API


async def delete_qq_message(msg_id: str) -> str:
	
	"""撤回 msg_id 对应的消息"""
	
	nc_api = SHARE_STORE.recall(NCATBOT_API, None)
	if nc_api is None:
		return "ncatbot api is unavailable"
	
	await nc_api.qq.messaging.delete_msg(message_id=msg_id)
	
	return f"successful"