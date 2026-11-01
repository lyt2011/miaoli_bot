from miaoli_pipeline.core	import GraphPipeline

from ..core		import SHARE_STORE
from ..consts	import GRAPH_PIPELINE


def get_pipeline() -> GraphPipeline:
	"""取图管线"""
	return SHARE_STORE.recall(GRAPH_PIPELINE)
