from ..consts	import PLUGIN_CONFIG
from ..stores	import SHARE_STORE
from ..utils	import fail

from pydantic				import BaseModel, Field
from langchain_core.tools	import tool
from typing					import Literal


GET_MEME_WAYS = Literal["file", "uuid"]


class ToolSchema(BaseModel):
	meme	: str			= Field(..., description="表情包的路径或uuid")
	chat_id	: str			= Field(..., description="接收方ID")
	to_group: bool			= Field(default=False, description="是否发送到群，布尔类型，默认私聊")
	by		: GET_MEME_WAYS	= Field(default="file", description="系统获取表情包的方式 默认file(通过文件)")


@tool(args_schema=ToolSchema)
async def send_meme_to_qq(
	meme	: str,
	chat_id	: str,
	to_group: bool			= False,
	by		: GET_MEME_WAYS	= "file",
) -> str:
	
	"""
	发送一个表情包到 QQ
	**表情包是图片或gif，但图片或gif不一定是表情包**
	
	to_group 的值决定了 chat_id 的用途
	true: chat_id 作为群聊ID，将信息发送到 chat_id 对应的群聊
	false: chat_id 作为用户QQ号，将信息以私聊的方式发送到 chat_id 对应的用户
	
	by 的值决定系统对于了 meme 参数的使用方式
	file: 系统将 meme 参数作为路径，获取表情包(图片)并发送，不归档也能用这个
	uuid: 系统将 meme 参数作为uuid，在已归档的表情包中获取并发送，必须归档才能用这个
	"""
	
	plugin_config	= SHARE_STORE.recall(PLUGIN_CONFIG, None)
	meme_config		= getattr(plugin_config, "meme_config", None)
	if meme_config is None:
		return fail("meme被禁用")
	
	return fail("工具未写完")