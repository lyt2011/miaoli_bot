class FakeTool:
	def __init__(self, name: str) -> None:
		self.name = name
		

def test_tool_registry_registry() -> None:
	
	"""测试整个工具注册器"""
	
	from miaoli_bot.core	import ToolRegistry
	
	tool_registry = ToolRegistry()
	
	tool_a_name = "tool_a"
	tool_b_name = "tool_b"
	
	tool_a = FakeTool(tool_a_name)
	tool_b = FakeTool(tool_b_name)

	# 注册第一个工具
	tool_registry.register(tool_a)
	assert len(tool_registry._tools) == 1
	
	# 注册第二个工具
	tool_registry.register(tool_b)
	assert len(tool_registry._tools) == 2
	
	# 从 python 验证他们确实被注册了而且引用正确
	assert tool_registry._tools[tool_a_name] is tool_a
	assert tool_registry._tools[tool_b_name] is tool_b
	
	# 从 tool_registry 验证他们存在
	assert tool_registry.contains(tool_a)
	assert tool_registry.contains(tool_b)
	
	# 验证第二次注册相同名字的工具会被替换成新工具
	same_name_tool_a = FakeTool(tool_a_name)
	tool_registry.register(same_name_tool_a)
	assert tool_registry._tools[tool_a_name] is same_name_tool_a

def test_tool_registry_unregister() -> None:
	
	"""测试工具注册器注销逻辑正确"""
	
	from miaoli_bot.core	import ToolRegistry
	
	tool_registry = ToolRegistry()
	
	tool_a_name = "tool_a"
	tool_b_name = "tool_b"
	
	tool_a = FakeTool(tool_a_name)
	tool_b = FakeTool(tool_b_name)
	
	# 先给他们注册好
	tool_registry.register(tool_a)
	tool_registry.register(tool_b)
	
	# 验证瞎注销不会报错且幂等
	tool_registry.unregister(FakeTool("unknown_tool"))
	assert len(tool_registry._tools) == 2
	
	# 验证注销工具只会注销相同名字+相同对象的工具
	
	# 注销一个名字一样但是对象引用不一样的工具
	tool_registry.unregister(FakeTool(tool_a_name))
	assert len(tool_registry._tools) == 2 # 还是 2，虽然工具名存在但是对象不一样
	assert tool_a in list(tool_registry._tools.values()) # 验证工具 tool_a 还在
	
	# 注销名字一样 引用也一样的
	tool_registry.unregister(tool_b)
	assert len(tool_registry._tools) == 1 # 应该正确减少
	assert tool_b not in list(tool_registry._tools.values()) # tool_b 也应该不存在于字典的值里面
	
	# REVIEW: 修完这个bug记得删掉这坨bug断言
	# 注意 这里有个很牛逼的地方 算是bug吧
	# 每次注销工具的时候是以 tool.name 为键来删的
	# 所以你修改 BaseTool.name 然后删同一个对象 删不掉 (这个时候字典键的 key 还是老 key)
	
	# 这会时候 tool_registry 还残留着 tool_a
	tool_a.name = "new_name"
	tool_registry.unregister(tool_a)
	assert len(tool_registry._tools) == 1 # 应该还是一个
	assert tool_a in list(tool_registry._tools.values()) # tool_a 也确实在值里面

def test_registry_to_surface() -> None:
	
	"""验证 registry 转为 surface 的逻辑正确"""
	
	from miaoli_bot.core	import ToolRegistry
	
	tool_registry = ToolRegistry()
	
	tool_a_name = "tool_a"
	
	tool_a = FakeTool(tool_a_name)
	
	tool_registry.register(tool_a)
	
	# 转为 surface 
	# 确保俩对象的映射表不是同一个对象 但是工具数量要对的上 对象引用也要正确
	tool_surface = tool_registry.to_surface()
	assert tool_surface.tools_mapping is not tool_registry._tools
	assert len(tool_surface.tools) == len(tool_registry._tools)
	assert tool_surface.tools[0] is list(tool_registry._tools.values())[-1]

def test_surface_add() -> None:
	
	"""测试 surface 的工具增加逻辑正确"""
	
	from miaoli_bot.core	import ToolRegistry
	
	tool_registry = ToolRegistry()
	
	tool_a_name = "tool_a"
	tool_c_name = "tool_c"
	tool_d_name = "tool_d"
	
	tool_a = FakeTool(tool_a_name)
	tool_c = FakeTool(tool_c_name)
	tool_d = FakeTool(tool_d_name)
	
	# 先给他们注册好
	tool_registry.register(tool_a)
	
	# 转为 surface
	tool_surface = tool_registry.to_surface()
	
	# 添加工具 c 
	# 并验证工具只在 surface 上存在 (检测工具数量与实际对象引用)
	tool_surface.add(tool_c)
	assert tool_c in tool_surface.tools
	assert tool_c not in list(tool_registry._tools.values())
	
	# 给 registry 注册工具 d
	# 验证工具 d 仅存在于 registry 不会影响 surface
	tool_registry.register(tool_d)
	assert tool_d in list(tool_registry._tools.values())
	assert tool_d not in tool_surface.tools
