from ..stores	import SHARE_STORE
from ..consts	import NCATBOT_API

from pydantic				import BaseModel, Field
from langchain_core.tools	import tool


class ToolSchema(BaseModel):
	message_id: str = Field(..., description="需要撤回的消息ID")


@tool(args_schema=ToolSchema)
async def delete_qq_message(message_id: str) -> str:
	
	"""通过 message_id 撤回一条 QQ 信息"""
	
	nc_api = SHARE_STORE.recall(NCATBOT_API, None)
	if nc_api is None:
		return "Ncatbot api is unavailable"
	
	await nc_api.qq.messaging.delete_msg(message_id=message_id)
	
	return f"successful"