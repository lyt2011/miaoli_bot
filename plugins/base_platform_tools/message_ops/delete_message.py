from miaoli_bot.stores	import SHARE_STORE
from miaoli_bot.consts	import NCATBOT_API
from miaoli_bot.utils	import custom, fail

from pydantic				import BaseModel, Field
from typing					import Dict, Any
from langchain_core.tools	import tool


class ToolSchema(BaseModel):
	message_id: str = Field(..., description="需要撤回的消息ID")


@tool(args_schema=ToolSchema)
async def delete_qq_message(message_id: str) -> Dict[str, Any]:

	"""通过 message_id 撤回一条 QQ 信息"""

	ncatbot_api = SHARE_STORE.recall(NCATBOT_API)
	
	try:
		await ncatbot_api.qq.messaging.delete_msg(message_id=message_id)
	
	except Exception as e:
		return fail(f"撤回失败: {type(e).__name__}: {e}")

	return custom(status=True)
