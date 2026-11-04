def test_node_priorities() -> None:
	
	"""
	测试节点优先级顺序
	保证高优先级不小于等于低优先级
	"""
	
	from miaoli_bot.consts	import (
		MAXIMUM, HIGHEST, HIGH,
		MEDIUM, NORMAL, LOW, 
		LOWEST, TRIVIAL, MINIMUM
	)
	
	assert MAXIMUM > HIGHEST
	assert HIGHEST > HIGH
	assert HIGH > MEDIUM
	assert MEDIUM > NORMAL
	assert NORMAL > LOW
	assert LOW > LOWEST
	assert LOWEST > TRIVIAL
	assert TRIVIAL > MINIMUM
