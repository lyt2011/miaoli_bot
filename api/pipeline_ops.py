from miaoli_pipeline.core	import GraphPipeline

from ..consts	import GRAPH_PIPELINE
from ..stores	import SHARE_STORE


def get_pipeline() -> GraphPipeline:
	"""取图管线"""
	return SHARE_STORE.recall(GRAPH_PIPELINE)
