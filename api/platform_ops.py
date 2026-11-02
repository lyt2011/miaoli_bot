from ..core		import SHARE_STORE
from ..consts	import NCATBOT_API

from typing	import Any


def get_ncatbot_api() -> Any:
	"""获取 ncatbot 的 api 句柄 用于底层平台操作"""
	return SHARE_STORE.recall(NCATBOT_API)
