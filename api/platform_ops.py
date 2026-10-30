import asyncio

from typing	import Any

from ..consts	import INVOKE_LOCKS, NCATBOT_API
from ..stores	import SHARE_STORE


def get_ncatbot_api() -> Any:
	"""获取 ncatbot 的 api 句柄 用于底层平台操作"""
	return SHARE_STORE.recall(NCATBOT_API)

def get_invoke_lock(thread_id: str) -> asyncio.Lock:
	"""获取执行锁 锁与 miaoli_bot.main 共享"""
	return SHARE_STORE.recall(INVOKE_LOCKS)[thread_id] # defaultdict
