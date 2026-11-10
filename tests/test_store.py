import pytest


def test_set_and_recall() -> None:
	
	"""测试容器的存与取"""
	
	from miaoli_bot.core	import ShareStore
	
	# 每个测试自己造一个空容器 不依赖全局单例
	store = ShareStore()
	
	# 建立初始数据
	key = "a object"
	obj = object()
	
	# 设置初始键
	store.set(key, obj)
	
	# 测试键存在 / 数据不会被篡改
	assert store.contains(key)
	assert store.recall(key) is obj
	
	# 测试 default 参数作用 / 不会影响正确的键
	assert store.recall("invalid key", default=None) is None
	assert store.recall(key, default=None) is obj
	
	# 测试错误的键能正确报错
	with pytest.raises(KeyError):
		store.recall("invalid key")

def test_store_clean() -> None:
	
	"""测试容器清理相关功能"""
	
	from miaoli_bot.core	import ShareStore
	
	store = ShareStore()
	
	# 初始数据
	key = "a object"
	obj = object()
	
	# 初始键值
	store.set(key, obj)
	
	# 拿到原始容器字典引用
	dict_ref = store._store
	
	# 执行清理
	store.clear()
	
	# 不应该为原始对象 且 容器是空的
	assert store._store is not dict_ref
	assert not store._store
	assert store.is_empty()

def test_store_data() -> None:
	
	"""测试容器数据正确"""
	
	from miaoli_bot.core	import ShareStore
	
	store = ShareStore()
	
	# 初始数据
	key = "a object"
	obj = object()
	
	# 初始键值
	store.set(key, obj)
	
	# 容器应该只有一个键和值
	assert len(store.keys()) == 1
	assert len(store.values()) == 1
	
	# 且对象引用正确
	assert list(store.keys())[0] is key
	assert list(store.values())[0] is obj

def test_store_ref() -> None:
	
	"""测试容器引用的不是类变量而是实例变量"""
	
	from miaoli_bot.core	import ShareStore
	
	key = "a key"
	obj = object()
	
	a, b = ShareStore(), ShareStore()
	a.set(key, obj)
	
	# 容器内 _store 变量不能是同一个对象
	assert a._store is not b._store
	# a.set 不会影响到另一个 b 对象
	assert a.contains(key) and not b.contains(key)
