from ..consts	import GRAPH_PIPELINE
from ..core		import SHARE_STORE, GraphPipeline


def get_pipeline() -> GraphPipeline:
	"""取图管线"""
	return SHARE_STORE.recall(GRAPH_PIPELINE)
