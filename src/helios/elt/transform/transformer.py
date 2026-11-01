from typing import Protocol

from helios.elt.transform.models.transformation_result import TransformationResult


class Transformer(Protocol):
    """Protocol for a data transformer."""

    def transform(self, commit: bool = True) -> TransformationResult:
        """Perform the transformation using the given database connector."""
        ...
