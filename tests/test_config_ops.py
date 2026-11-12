def test_workspace_injector() -> None:
	
	"""测试工作目录注入器"""
	
	from miaoli_bot.utils	import inject_workspace
	
	assert inject_workspace("$workspace/plugins", "a") == "a/plugins"
	assert inject_workspace(["$workspace/plugins"], "a") == ["a/plugins"]
	assert inject_workspace({"test": "$workspace/plugins"}, "a") == {"test": "a/plugins"}
	assert inject_workspace({"$workspace": "$workspace/plugins"}, "a") == {"$workspace": "a/plugins"}
	assert inject_workspace({"first": {"second": "$workspace/plugins"}}, "a") == {"first": {"second": "a/plugins"}}
