from ncatbot.types	import MessageArray, File

from ..utils	import easier_send
from ..stores	import SHARE_STORE
from ..consts	import NCATBOT_API

from typing					import Optional, Literal
from pydantic				import BaseModel, Field
from langchain_core.tools	import tool


class ToolSchema(BaseModel):
	target_id		: str				= Field(..., description="接收方ID")
	send_to_group	: bool				= Field(default=False, description="是否发送到群，布尔类型，默认私聊")
	plain_text		: Optional[str]		= Field(default=None, description="消息的文本内容 默认空")
	at_user_id		: Optional[str]		= Field(default=None, description="群聊")
	reply_message_id: Optional[str]		= Field(default=None, description="引用(回复)某条已发送的QQ信息的ID")


@tool(args_schema=ToolSchema)
async def send_message_to_qq(
	target_id		: str,
	send_to_group	: bool			= False,
	plain_text		: Optional[str] = None,
	at_user_id		: Optional[str] = None,
	reply_message_id: Optional[str] = None,
) -> str:
	
	"""
	发送一条信息到 QQ
	
	**私聊不能使用艾特 会报错**
	
	send_to_group 的值决定了 target_id 的用处
	true: target_id 将作为群号使用 给该群聊ID对应的群发消息
	false: target_id 将作为QQ号使用 给对应QQ号的用户发消息
	"""
	
	nc_api = SHARE_STORE.recall(NCATBOT_API, None)
	if nc_api is None:
		return f"Ncatbot api is unavailable"
	
	message_array: MessageArray = MessageArray()
	
	if reply_message_id:
		message_array.add_reply(reply_message_id)
	
	if at_user_id:
		message_array.add_at(at_user_id)
	
	if plain_text:
		message_array.add_text(plain_text)
	
	if not message_array:
		return f"Nothing can send"
	
	sender_result = await easier_send(
		ncatbot_api	= nc_api,
		chat_id		= target_id,
		to_group	= send_to_group,
		message		= message_array
	)
	
	return sender_result.model_dump_json()