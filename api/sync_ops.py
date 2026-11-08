from ..core		import SHARE_STORE
from ..consts	import INVOKE_LOCKS, MAIN_READY, RUN_REQUESTED

import asyncio


def get_invoke_lock(thread_id: str) -> asyncio.Lock:
	"""获取指定线程的执行锁 锁与 miaoli_bot.main 共享"""
	return SHARE_STORE.recall(INVOKE_LOCKS)[thread_id]

def please_run_graph() -> None:
	"""请求主包跑一次图 没有返回"""
	SHARE_STORE.recall(RUN_REQUESTED).set()

async def wait_main_ready() -> None:
	"""等待主包完全加载"""
	await SHARE_STORE.recall(MAIN_READY).wait()