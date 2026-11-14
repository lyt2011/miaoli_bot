from langchain_core.language_models	import BaseChatModel
from langchain_core.messages		import AIMessage, BaseMessage

from ...errors	import MaxRetryLimitError
from .utils		import is_retriable

from typing	import List, Tuple

import logging


LOGGER = logging.getLogger("CallLLM")


async def call_llm(
	messages: List[BaseMessage],
	client	: BaseChatModel,
	*,
	max_retry: int = 0
) -> Tuple[int, List[Exception], AIMessage]:
	
	"""
	带重试的 LLM 调用 达到最大次数会抛出 MaxRetryLimitError
	返回三元组 (尝试次数, 途中出现的所有错误, 最终回复)
	"""
	
	# 当前第 n 次 错误记录
	cur_times	= 0
	exceptions	= []
	
	while True:
		
		cur_times = cur_times + 1
		
		LOGGER.info(f"第 {cur_times} 次尝试请求"
			f" LLM: 已积累 {len(exceptions)} 个错误")
				
		try:
			out = await client.ainvoke(messages)
		
		except Exception as exc:
			
			exceptions.append(exc)
			
			LOGGER.exception("LLM 调用出现错误: "
				f"{type(exc).__name__}: {exc}")
			
			# 对于次数达到最大限制 或错误不可继续 再次抛出
			if cur_times >= max_retry or not is_retriable(exc):
				raise MaxRetryLimitError(
					exceptions=exceptions, times=cur_times) from exc
			
			LOGGER.info(f"错误可重试 继续尝试请求 next={cur_times + 1}")
		
		else:
			break
	
	return cur_times, exceptions, out