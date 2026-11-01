from dataclasses	import dataclass
from datetime		import datetime
from typing			import Union


@dataclass(frozen=True)
class Once:
	when: datetime
	
	def next_fire_time(self, now: datetime, previous: Union[datetime, None]) -> Union[datetime, None]:
		"""只运行一次 previous，有值说明运行过了"""
		return self.when if previous is None else None