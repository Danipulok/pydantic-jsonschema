from dataclasses import dataclass


@dataclass
class SchemaError(Exception):
    """Base schema exception."""

    message: str

    def __post_init__(self) -> None:
        super().__init__(self.message)

    def __str__(self) -> str:
        return repr(self)


@dataclass
class ParsingError(SchemaError):
    """Schema parsing failed."""


@dataclass
class SchemaReferenceError(SchemaError):
    """Reference resolution failed."""

    path: list[str]


# Keep old name for backwards compatibility
ReferenceError = SchemaReferenceError
