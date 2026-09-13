from ncatbot.types	import MessageArray, File

from ..utils	import easier_send
from ..stores	import SHARE_STORE
from ..consts	import NCATBOT_API

from typing	import Optional, Literal


async def send_message_to_QQ(
	recipient_id	: str,
	send_to_group	: Literal[bool]	= False,
	plain_text		: Optional[str] = None,
	attachment_path	: Optional[str] = None,
	at_user_id		: Optional[str] = None,
	reply_msg_id	: Optional[str] = None
) -> str:
	
	"""
	args:
		recipient_id: 接收方ID
		send_to_group: 是否发送给群
		plain_text: 纯文本信息
		attachment_path: 附件
		at_user_id: 艾特某个用户
		reply_msg_id: 引用(回复)某个消息
	
	# 约束
	plain_text 不能同时与 attachment_path 存在，同时传入则文本会被文件覆盖
	reply_msg_id 默认自带艾特，无需主动指定 at_user_id
	私聊不可用 at_user_id，传入则被忽略
	
	send_to_group 的值决定了 recipient_id 的用处
	True: recipient_id 将作为群号使用 给该群聊id对应的群发消息
	False: recipient_id 将作为QQ号使用 给对应QQ号的用户发消息
	"""
	
	nc_api = SHARE_STORE.recall(NCATBOT_API, None)
	if nc_api is None:
		return f"ncatbot api is unavailable"
	
	message_array: MessageArray = MessageArray()
	
	if isinstance(reply_msg_id, str) and reply_msg_id:
		message_array.add_reply(reply_msg_id)
	
	if isinstance(at_user_id, str) and at_user_id:
		message_array.add_at(at_user_id)
	
	if isinstance(plain_text, str) and plain_text:
		message_array.add_text(plain_text)
	
	if isinstance(attachment_path, str) and attachment_path:
		message_array.add_segment(File(file=attachment_path))
	
	sender_result = await easier_send(
		ncatbot_api	= nc_api,
		chat_id		= recipient_id,
		to_group	= send_to_group,
		message		= message_array
	)
	
	if hasattr(sender_result, "model_dump_json"):
		return sender_result.model_dump_json()
	
	return str(sender_result)