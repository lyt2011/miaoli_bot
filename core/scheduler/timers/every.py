from typing			import Union
from dataclasses	import dataclass
from datetime		import datetime, timedelta


@dataclass(frozen=True)
class Every:
	delta: timedelta
	
	def next_fire_time(self, now: datetime, previous: Union[datetime, None]) -> Union[datetime, None]:
		
		# 对于已经运行过的使用上次运行的时间
		if previous is not None:
			return previous + self.delta
		
		return now + self.delta