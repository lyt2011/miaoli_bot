from ..stores		import SHARE_STORE
from ..protocols	import ChainProtocol
from ..models		import DispatchResult, ParseResult
from ..consts		import EVENT_PARSER, SEGMENT_PARSER

from typing	import Any, Optional, List


async def parse_event(
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
		
	parser = parser or SHARE_STORE.recall(EVENT_PARSER, None)
	if parser is None:
		return None
	
	return await parser.dispatch(event)

async def parse_segment(
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
	
	parser = parser or SHARE_STORE.recall(SEGMENT_PARSER, None)
	if parser is None:
		return None
	
	return await parser.dispatch(segment)

async def parse_message(
	event			: Any,
	segments		: List[Any],
	event_parser	: Optional[ChainProtocol] = None,
	segment_parser	: Optional[ChainProtocol] = None,
) -> ParseResult:
	
	"""
	并合 parse_segment 与 parse_event
	提供便捷的解析接口
	"""
	
	# 显式获取 event_parser 与 segment_parser 便于控制逻辑
	event_parser	= event_parser or SHARE_STORE.recall(EVENT_PARSER, None)
	segment_parser	= segment_parser or SHARE_STORE.recall(SEGMENT_PARSER, None)
	
	event_result	: Optional[Any]	= None
	segment_results	: List[Any]		= []
	
	if event_parser is not None:
		
		event_result = await parse_event(event, parser=event_parser)
		if event_result is not None:
			event_result = event_result.result # 拿 DispatchResult 的 result
	
	if segment_parser is not None:
		
		for segment in segments:
			
			segment_result = await parse_segment(segment, parser=segment_parser)
			if segment_result is not None:
				segment_results.append(segment_result.result) # 拿 DispatchResult 的 result
	
	return ParseResult(event=event_result, segments=segment_results)