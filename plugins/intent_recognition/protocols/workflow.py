from abc	import ABC, abstractmethod


class BaseWorkflow(ABC):
	
	"""命中后能提供一段工作流正文的东西"""
	
	@property
	@abstractmethod
	def content(self) -> str: ...
