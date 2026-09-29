from ncatbot.types	import Image, MessageArray

from ..consts	import PLUGIN_CONFIG, NCATBOT_API
from ..stores	import SHARE_STORE
from ..utils	import fail, success, MemeSqlite, easier_send
from ..errors	import APIUnavailableError

from pydantic				import BaseModel, Field
from langchain_core.tools	import tool
from typing					import Dict, Any


class ToolSchema(BaseModel):
	hash	: str	= Field(..., description="表情包的 hash")
	chat_id	: str	= Field(..., description="接收方ID")
	to_group: bool	= Field(default=False, description="是否发送到群，布尔类型，默认私聊")


@tool(args_schema=ToolSchema)
async def send_meme_to_qq(
	hash	: str,
	chat_id	: str,
	to_group: bool	= False,
) -> Dict[str, Any]:
	
	"""
	发送一个**已归档的**表情包到 QQ
	
	to_group 的值决定了 chat_id 的用途
	true: chat_id 作为群聊ID，将信息发送到 chat_id 对应的群聊
	false: chat_id 作为用户QQ号，将信息以私聊的方式发送到 chat_id 对应的用户
	"""
	
	nc_api = SHARE_STORE.recall(NCATBOT_API, None)
	if nc_api is None:
		raise APIUnavailableError("Ncatbot api is unavailable")
	
	plugin_config	= SHARE_STORE.recall(PLUGIN_CONFIG, None)
	meme_config		= getattr(plugin_config, "meme_config", None)
	if meme_config is None or not meme_config.is_enable:
		return fail("meme被禁用")
	
	async with MemeSqlite(meme_config.db_path) as meme_sqlite:
		
		if not await meme_sqlite.is_hash_existing(hash):
			return fail(f"找不到 hash 为 {hash} 的表情包")
		
		meme_info	= await meme_sqlite.fetch_meme_from_hash(hash)
		base64_data	= meme_info["base64"].decode()
	
	message		= MessageArray([Image(file=f"base64://{base64_data}", sub_type=1)])
	send_result = await easier_send(
		ncatbot_api	= nc_api,
		chat_id		= chat_id,
		to_group	= to_group,
		message		= message,
	)
	
	return success(send_result.model_dump())