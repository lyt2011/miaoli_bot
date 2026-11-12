from langgraph._internal._typing	import MISSING

from .section_patch	import SectionPatch

from typing	import Any, Self


class UntrackedSectionPatch(SectionPatch):
	
	"""不落盘的 SectionPatch"""
	
	def checkpoint(self) -> Any:
		return MISSING
	
	def copy(self) -> Self:
		
		channel = self.__class__(self.typ, self.key)
		
		if self.value is not MISSING:
			channel.value = dict(self.value)
		
		return channel
