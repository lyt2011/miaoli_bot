from typing	import Any

from ..consts	import NCATBOT_API
from ..stores	import SHARE_STORE


def get_ncatbot_api() -> Any:
	"""获取 ncatbot 的 api 句柄 用于底层平台操作"""
	return SHARE_STORE.recall(NCATBOT_API)
