from pydantic	import Field

from .file_workflow	import FileWorkflow

from typing	import Annotated, Union


Workflow = Annotated[
	Union[FileWorkflow],
	Field(discriminator="mode")
]


__all__ = [

	"FileWorkflow",
	
	"Workflow",

]
