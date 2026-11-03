from langchain_core.tools	import tool

from pydantic	import BaseModel, Field

from miaoli_bot.api		import store_recall
from miaoli_bot.consts	import EVENT_BUFFER

from typing	import Any, Dict


class ToolSchema(BaseModel):
	count: int	= Field(default=10, description="读取多少条信息")


@tool(args_schema=ToolSchema)
async def get_qq_unread_messages(count: int) -> Dict[str, Any]:
	
	"""
	获取 QQ 未读消息
	读取之后会自动清理缓冲区 自动去掉已读取过的消息
	"""
	
	event_buffer	= store_recall(EVENT_BUFFER)
	unread_events	= event_buffer.pop(count)[::-1]
	
	messages	= [event._data.model_dump() for event in unread_events]
	metadata	= {"expectation_read": count, "actual_read": len(unread_events), "remaining": len(event_buffer)}

	return {"messages": messages, "metadata": metadata}
