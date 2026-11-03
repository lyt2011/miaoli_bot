from ..core		import SHARE_STORE
from ..consts	import INVOKE_LOCK, MAIN_READY

import asyncio


def get_invoke_lock() -> asyncio.Lock:
	"""获取执行锁 锁与 miaoli_bot.main 共享"""
	return SHARE_STORE.recall(INVOKE_LOCK)

async def wait_main_ready() -> None:
	"""等待主包完全加载"""
	await SHARE_STORE.recall(MAIN_READY).wait()