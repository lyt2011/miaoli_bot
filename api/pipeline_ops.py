from ..consts	import GRAPH_PIPELINE
from ..core		import SHARE_STORE, GraphPipeline, safe_run_graph


def get_pipeline() -> GraphPipeline:
	"""取图管线"""
	return SHARE_STORE.recall(GRAPH_PIPELINE)

__all__ = [

	"get_pipeline",
	"safe_run_graph",

]
