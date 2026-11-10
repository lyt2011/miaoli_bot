from miaoli_bot.core	import SHARE_STORE

from typing		import Iterator

import pytest


@pytest.fixture(autouse=True)
def clean_store() -> Iterator[None]:
	"""每个测试前后都清空共享容器"""
	SHARE_STORE.clear()
	yield
	SHARE_STORE.clear()
