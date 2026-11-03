def test_workspace_injector() -> None:
	
	"""测试工作目录注入器"""
	
	from miaoli_bot.utils import inject_workspace
	
	assert inject_workspace("$workspace/plugins", "a") == "a/plugins"
	assert inject_workspace(["$workspace/plugins"], "a") == ["a/plugins"]
	assert inject_workspace({"test": "$workspace/plugins"}, "a") == {"test": "a/plugins"}

def test_id_concatenate() -> None:
	
	"""测试 id 连接"""
	
	from miaoli_bot.utils	import concatenate_id
	from miaoli_bot.consts	import GROUP_PREFIX, PRIVATE_PREFIX
	
	assert concatenate_id("123", is_group=True) == f"{GROUP_PREFIX}123"
	assert concatenate_id("abc", is_group=False) == f"{PRIVATE_PREFIX}abc"