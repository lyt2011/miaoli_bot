from .regex				import RegexRule
from .any_keywords		import AnyKeywordsRule
from .min_keywords		import MinKeywordsRule
from .single_keyword	import SingleKeywordRule

from pydantic			import Field

from typing				import Annotated, Union


Rule = Annotated[
	Union[AnyKeywordsRule, MinKeywordsRule, RegexRule, SingleKeywordRule],
	Field(discriminator="mode")
]


__all__ = [

	"AnyKeywordsRule",
	"MinKeywordsRule",
	"RegexRule",
	"SingleKeywordRule",
	
	"Rule",

]
