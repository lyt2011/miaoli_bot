from __future__	import annotations

from ..models	import PluginTopologyRuntime

from typing		import TYPE_CHECKING, Iterable, List

if TYPE_CHECKING:
	from ..plugin	import Plugin


def topology_sort_plugins(plugins: Iterable[Plugin]) -> List[Plugin]:
	
	"""对插件进行拓扑排序"""
	
	# 通过插件名进行首次稳定排序
	rounds		= 0
	runtimes	= sorted(
		[PluginTopologyRuntime.build(plugin) for plugin in plugins],
		key = lambda r: r.name
	)
	
	# 全部都未排序时才运行
	while not all([runtime.is_sorted() for runtime in runtimes]):
		
		# 收集已空依赖但未排序的插件
		no_dep_runtimes = [
			runtime for runtime in runtimes
			if runtime.is_null_dependences() and not runtime.is_sorted()
		]
		
		if not no_dep_runtimes:
			raise RuntimeError(f"存在循环依赖或缺失依赖: {[runtime.name for runtime in runtimes if not runtime.is_sorted()]}")
		
		for no_dep_runtime in no_dep_runtimes:
			
			# 移除插件的依赖
			for runtime in runtimes:
				runtime.remove_dependence(no_dep_runtime.name)
			
			# 标注没有依赖的插件已排序
			no_dep_runtime.mark_sorted(index=rounds)
		
		rounds = rounds + 1
	
	return [runtime.plugin for runtime in sorted(runtimes, key=lambda r: r.index)]
