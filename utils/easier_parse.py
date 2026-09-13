from ..stores		import SHARE_STORE
from ..protocols	import ChainProtocol
from ..models		import DispatchResult
from ..consts		import EVENT_PARSER, SEGMENT_PARSE

from typing	import Any, Optional


async def parse_event(
	self,
	event	: Any, *,
	parser	: Optional[ChainProtocol] = None,
) -> Optional[DispatchResult]:
	
	"""
	解析 event 的快捷方法
	通过从 SHARE_STORE 中获取 event 解析器 (或从参数 parser 中)
	并通过解析链解析 event
	
	解析器获取失败时返回 None
	解析器解析成功时返回 DispatchResult
	"""
	
	if parser is None:
		
		parser = SHARE_STORE.recall(EVENT_PARSER, None)
		if parser is None:
			return None
	
	return await parser.dispatch(event)

async def parse_segment(
	self,
	segment	: Any, *,
	parser	: Optional[ChainProtocol] = None,
) -> Optional[DispatchResult]:
	
	"""
	解析 segment 的快捷方法
	通过从 SHARE_STORE 中获取 segment 解析器 (或从参数 parser 中)
	并通过解析链解析 segment
	
	解析器获取失败时返回 None
	解析器解析成功时返回 DispatchResult
	"""
	
	if parser is None:
		
		parser = SHARE_STORE.recall(SEGMENT_PARSE, None)
		if parser is None:
			return None
	
	return await parser.dispatch(segment)