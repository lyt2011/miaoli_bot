"""GraphPipeline 的增量折叠与返回值判定辅助函数。"""

from langgraph.types				import Overwrite
from langgraph._internal._typing	import MISSING
from langgraph.channels.base		import BaseChannel
from langgraph.errors				import EmptyChannelError

from ..protocols	import BaseNodeAction

from contextlib	import suppress
from typing		import Any, Dict, Mapping, Optional, Sequence, Union

# 处理器的返回值：Action / 纯增量 dict / None（无操作）
ActionResult = Optional[Union[BaseNodeAction, Dict[str, Any]]]


def merge_into_state(state: Mapping[str, Any], delta: Mapping[str, Any], channels: Mapping[str, Any]) -> Dict[str, Any]:
	
	"""
	把 delta 合并进 state 得到新状态
	OverWrite 在此被展开/消费
	"""
	
	merged	= dict(state)
	
	for key, value in delta.items():
		
		# 替换语义 直接换值
		if isinstance(value, Overwrite):
			merged[key] = value.value
			continue
		
		channel	= channels.get(key)
		
		# 无通道 直接赋值
		if channel is None:
			merged[key] = value
			continue
		
		merged[key] = apply_deltas(channel, merged.get(key, MISSING), [value])
	
	return merged

def merge_into_updates(accumulated: Mapping[str, Any], delta: Mapping[str, Any], channels: Mapping[str, Any]) -> Dict[str, Any]:
	
	"""把同一个事件里多个处理器的产出折叠成一份增量"""
	
	merged	= dict(accumulated)
	
	for key, value in delta.items():
		
		channel	= channels.get(key)
		
		# 无通道 直接赋值
		if channel is None:
			merged[key] = value
			continue
		
		old	= merged.get(key, MISSING)
		
		# 新来的要替换 -> 它已吸收此前的增量 直接接管
		if isinstance(value, Overwrite):
			merged[key] = value
			continue
		
		# 之前是替换 -> 新增量叠在替换结果之上 包装保留
		if isinstance(old, Overwrite):
			merged[key] = Overwrite(apply_deltas(channel, MISSING, [old.value, value]))
			continue
		
		merged[key] = apply_deltas(channel, old, [value])
	
	return merged

def is_none_action(action: ActionResult) -> bool:
	return action is None

def is_update_action(action: ActionResult) -> bool:
	
	"""裸 dict 或 action 自带的 updates"""
	
	is_dict	= isinstance(action, dict)
	is_duck	= hasattr(action, "updates") and isinstance(action.updates, dict)
	
	return is_dict or is_duck

def apply_deltas(channel: BaseChannel, base: Any, deltas: Sequence[Any]) -> Any:
	
	new = channel.from_checkpoint(base)
	new.update(deltas)
	
	with suppress(EmptyChannelError):
		return new.get()
	
	return MISSING
