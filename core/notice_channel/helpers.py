from ...protocols	import BaseChannel, BaseChannelMessage

from typing		import List, Optional, Tuple

import asyncio
import logging


LOGGER = logging.getLogger("ChannelSurface")


async def _drain_c(c: BaseChannel, timeout: float) -> Optional[Tuple[BaseChannel, List[BaseChannelMessage]]]:
			
	"""返回 (渠道实例: 渠道消息列表) 元组 方便组装字典"""
	
	try:
	
		_messages = await (asyncio
			.wait_for(c.drain(), timeout=timeout))
		
		# 校验信息来源
		for message in _messages:
			if message.platform not in c.platforms:
				LOGGER.warning(f"渠道 {c.name} "
					f"得到了一个未支持的渠道信息 platform={message.platform}")
			
		# 过滤非支持渠道的消息
		messages = [message for message in _messages if message.platform in c.platforms]
	
	except asyncio.TimeoutError:
		LOGGER.warning(f"渠道 "
			f"{c.name} 拉取信息超时: {timeout}")
	
	except Exception as e:
		LOGGER.exception(f"渠道 {c.name} "
			f"拉取信息异常: {type(e).__name__}: {e}")
	
	else:
		return c, messages
	
	return None