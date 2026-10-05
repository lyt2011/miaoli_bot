from ncatbot.types			import Image, MessageArray
from pydantic				import BaseModel, Field
from langchain_core.tools	import tool
from typing					import Dict, Any

from ..consts	import PLUGIN_CONFIG
from ..core		import MemeSqlite

from miaoli_bot.utils	import fail, success, easier_send
from miaoli_bot.stores	import SHARE_STORE
from miaoli_bot.consts	import NCATBOT_API


class ToolSchema(BaseModel):
	hash	: str	= Field(..., description="表情包的 hash")
	chat_id	: str	= Field(..., description="接收方ID")
	to_group: bool	= Field(default=False, description="是否发送到群，布尔类型，默认私聊")


@tool(args_schema=ToolSchema)
async def send_meme_to_qq(
	hash	: str,
	chat_id	: str,
	to_group: bool,
) -> Dict[str, Any]:
	
	"""
	发送一个**已归档的**表情包到 QQ
	
	to_group 的值决定了 chat_id 的用途
	true: chat_id 作为群聊ID，将信息发送到 chat_id 对应的群聊
	false: chat_id 作为用户QQ号，将信息以私聊的方式发送到 chat_id 对应的用户
	"""
	
	ncatbot_api		= SHARE_STORE.recall(NCATBOT_API)
	plugin_config	= SHARE_STORE.recall(PLUGIN_CONFIG)
	
	if not plugin_config.is_enable:
		return fail("meme被禁用")
	
	try:
	
		async with MemeSqlite(plugin_config.db_path) as meme_sqlite:
			
			if not await meme_sqlite.is_hash_existing(hash):
				return fail(f"找不到 hash 为 {hash} 的表情包")
			
			meme_info	= await meme_sqlite.fetch_meme_from_hash(hash)
			base64_data	= meme_info["base64"].decode()
		
		send_result = await easier_send(
			ncatbot_api	= ncatbot_api,
			chat_id		= chat_id,
			to_group	= to_group,
			message		= MessageArray([Image(file=f"base64://{base64_data}", sub_type=1)]),
		)
	
	except Exception as e:
		return fail(f"发送失败: {type(e).__name__}: {e}")
	
	return success(send_result.model_dump())