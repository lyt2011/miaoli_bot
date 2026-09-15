from ..stores	import SHARE_STORE
from ..consts	import NCATBOT_API

from typing	import Dict, Any


async def query_qq_message_id(msg_id: int) -> str:
	
	"""
	查询 msg_id 对应的 **完整信息**
	**完整信息**指: 未经过特殊处理或解析的 OB11 协议信息
	查询的结果将转为 json 字符串，并作为工具调用结果返回
	"""
	
	nc_api = SHARE_STORE.recall(NCATBOT_API, None)
	if nc_api is None:
		return "ncatbot api is unavailable"
	
	msg_data = await nc_api.qq.query.get_msg(msg_id)
	
	return msg_data.model_dump_json()