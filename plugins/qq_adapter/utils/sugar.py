from miaoli_bot.stores	import SHARE_STORE
from ..consts			import SEGMENT_PARSER

from typing	import Any, Dict, List


async def parse_segments(segments: List[Any]) -> List[Dict[str, Any]]:
	
	"""切割解析消息段"""
	
	segment_parser	= SHARE_STORE.recall(SEGMENT_PARSER)
	output_segments	= []
	
	for seg in segments:
		
		# 尝试解析 如果没有结果就跳过
		parse_result = await segment_parser.dispatch(seg)
		if parse_result.result is None:
			continue
		
		output_segments.append(parse_result.result)
	
	return output_segments
