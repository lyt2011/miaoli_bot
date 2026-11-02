from ..core		import SHARE_STORE
from ..consts	import INVOKE_LOCKS

import asyncio


def get_invoke_lock(thread_id: str) -> asyncio.Lock:
	"""获取执行锁 锁与 miaoli_bot.main 共享"""
	return SHARE_STORE.recall(INVOKE_LOCKS)[thread_id] # defaultdict
