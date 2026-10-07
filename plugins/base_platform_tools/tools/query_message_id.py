from miaoli_bot.stores	import SHARE_STORE
from miaoli_bot.consts	import NCATBOT_API
from miaoli_bot.utils	import success, fail

from pydantic				import BaseModel, Field
from typing					import Dict, Any
from langchain_core.tools	import tool


class ToolSchema(BaseModel):
	message_id: str = Field(..., description="目标信息ID")


@tool(args_schema=ToolSchema)
async def query_qq_message_id(message_id: str) -> Dict[str, Any]:

	"""
	查询 message_id 对应的 QQ 消息
	查询的结果将转为 json 字符串，并作为工具调用结果返回
	"""

	ncatbot_api = SHARE_STORE.recall(NCATBOT_API)
	
	try:
		msg_data = await ncatbot_api.qq.query.get_msg(message_id)
	
	except Exception as e:
		return fail(f"查询失败: {type(e).__name__}: {e}")

	return success(msg_data.model_dump())
