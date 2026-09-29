from ..stores	import SHARE_STORE
from ..consts	import NCATBOT_API
from ..errors	import APIUnavailableError
from ..utils	import success

from pydantic				import BaseModel, Field
from typing					import Dict, Any
from langchain_core.tools	import tool


class ToolSchema(BaseModel):
	message_id: str = Field(..., description="目标信息ID")


@tool(args_schema=ToolSchema)
async def query_qq_message_id(message_id: str) -> Dict[str, Any]:
	
	"""
	查询 message_id 对应的 未经过特殊处理或解析的 OB11 协议信息
	查询的结果将转为 json 字符串，并作为工具调用结果返回
	"""
	
	nc_api = SHARE_STORE.recall(NCATBOT_API, None)
	if nc_api is None:
		raise APIUnavailableError("Ncatbot api is unavailable")
	
	msg_data = await nc_api.qq.query.get_msg(message_id)
	
	return success(msg_data.model_dump())