from ncatbot.types	import MessageArray

from ..utils	import easier_send, fail, success
from ..stores	import SHARE_STORE
from ..consts	import NCATBOT_API
from ..errors	import APIUnavailableError

from typing					import Optional, Dict, Any
from pydantic				import BaseModel, Field
from langchain_core.tools	import tool


class ToolSchema(BaseModel):
	chat_id			: str				= Field(..., description="接收方ID")
	to_group		: bool				= Field(default=False, description="是否发送到群，布尔类型，默认私聊")
	plain_text		: Optional[str]		= Field(default=None, description="消息的文本内容 默认空")
	at_user_id		: Optional[str]		= Field(default=None, description="群聊")
	reply_message_id: Optional[str]		= Field(default=None, description="引用(回复)某条已发送的QQ信息的ID")


@tool(args_schema=ToolSchema)
async def send_message_to_qq(
	chat_id			: str,
	to_group		: bool			= False,
	plain_text		: Optional[str] = None,
	at_user_id		: Optional[str] = None,
	reply_message_id: Optional[str] = None,
) -> Dict[str, Any]:
	
	"""
	发送一条信息到 QQ
	
	私聊不能使用艾特，会被静默跳过，不报错
	
	to_group 的值决定了 chat_id 的用途
	true: chat_id 作为群聊ID，将信息发送到 chat_id 对应的群聊
	false: chat_id 作为用户QQ号，将信息以私聊的方式发送到 chat_id 对应的用户
	"""
	
	nc_api = SHARE_STORE.recall(NCATBOT_API, None)
	if nc_api is None:
		raise APIUnavailableError("Ncatbot api is unavailable")
	
	message_array: MessageArray = MessageArray()
	
	if reply_message_id:
		message_array.add_reply(reply_message_id)
	
	if plain_text:
		message_array.add_text(plain_text)
	
	if at_user_id and to_group:
		message_array.add_at(at_user_id)
	
	if not message_array:
		return fail("Nothing can send")
	
	send_result = await easier_send(
		ncatbot_api	= nc_api,
		chat_id		= chat_id,
		to_group	= to_group,
		message		= message_array
	)
	
	return success(send_result.model_dump())