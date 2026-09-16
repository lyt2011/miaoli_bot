from ncatbot						import api as nc_api
from ncatbot.types.napcat.message	import SendMessageResult
from ncatbot.types					import MessageArray

from typing	import Union


async def private_easier_send(	
	ncatbot_api	: nc_api,
	chat_id		: str,
	message		: Union[str, MessageArray],
) -> SendMessageResult:
	
	"""
	封装了过长的函数路径
	改为便捷的 private_easier_send
	"""
	
	send_funcion	= ncatbot_api.qq.messaging.send_private_msg
	messages_array	= message.to_list() if isinstance(message, MessageArray) else message
	sender_coro		= send_funcion(user_id=chat_id, message=messages_array)
	
	return await sender_coro

async def group_easier_send(
	ncatbot_api	: nc_api,
	chat_id		: str,
	message		: Union[str, MessageArray]
) -> SendMessageResult:
	
	"""
	封装了过长的函数路径
	改为便捷的 group_easier_send
	"""
	
	send_funcion	= ncatbot_api.qq.messaging.send_group_msg
	messages_array	= message.to_list() if isinstance(message, MessageArray) else message
	sender_coro		= send_funcion(group_id=chat_id, message=messages_array)
	
	return await sender_coro

async def easier_send(
	ncatbot_api	: nc_api,
	chat_id		: Union[str, int],
	message		: Union[str, MessageArray],
	to_group	: bool = False
) -> SendMessageResult:
	
	"""
	把 group_easier_send 与 private_easier_send 合并为一个方法
	通过 to_group 开关显式区分
	更好的参数可读性与兼容性
	"""
	
	send_func	= group_easier_send if to_group else private_easier_send
	send_coro	= send_func(ncatbot_api=ncatbot_api, chat_id=chat_id, message=message)
	
	return await send_coro