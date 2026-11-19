"""Type-specific keywords on a schema whose `type` does not pin their type.

JSON Schema numeric, string, array and object keywords assert only on instances of their own
type; every other instance passes them (`bool` is not a number).
See: https://json-schema.org/draft/2020-12/json-schema-validation#section-6
"""

from decimal import Decimal, localcontext
from typing import Final, override

from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler, TypeAdapter, ValidationError
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema, ErrorDetails, InitErrorDetails, core_schema

from pydantic_jsonschema.schema import DataType

from ._base import AnnotationApplicator, AnnotationType

__all__ = ["IfType"]

_INSTANCE_TYPES: Final[dict[DataType, tuple[type, ...]]] = {
    DataType.NUMBER: (int, float, Decimal),
    DataType.STRING: (str,),
    DataType.ARRAY: (list,),
    DataType.OBJECT: (dict,),
}


class IfType(AnnotationApplicator):
    """Validate inputs of one JSON type against a branch annotation, and pass every other input.

    Carried by a schema whose host type does not pin the keywords' type (no `type`, a `type` list,
    `enum`, `anyOf`). The branch only checks the input: the host type still produces the value. It
    may hold a `ForwardRef` (a `$ref` to a definition still being built), resolved against the
    bound namespace on first use.
    """

    def __init__(
        self,
        *,
        data_type: DataType,
        branch: AnnotationType,
        integer_branch: AnnotationType | None = None,
        integer_precision_margin: int = 0,
    ) -> None:
        """Initialize with the JSON type checked and the annotation its instances must validate.

        :param data_type: `number`, `string`, `array` or `object`: the instances the branch checks.
        :param branch: The annotation typed to `data_type`, carrying the keywords.
        :param integer_branch: For `number`, the annotation an `int` validates against instead, so
            it compares exactly rather than rounded to a `float`.
        :param integer_precision_margin: The digits a `decimal` quotient needs beyond the `int`'s
            own for `multipleOf` to divide exactly.
        """
        super().__init__()

        self._instance_types: tuple[type, ...] = _INSTANCE_TYPES[data_type]
        self._branch: AnnotationType = branch
        self._integer_branch: AnnotationType | None = integer_branch
        self._integer_precision_margin: int = integer_precision_margin
        self._adapter: TypeAdapter[AnnotationType] | None = None
        self._integer_adapter: TypeAdapter[AnnotationType] | None = None

    @override
    def __get_pydantic_core_schema__(
        self,
        source_type: AnnotationType,
        handler: GetCoreSchemaHandler,
    ) -> CoreSchema:
        """Wrap the host schema with the type check (on the raw input)."""
        return core_schema.no_info_wrap_validator_function(self._validate, handler(source_type))

    @override
    def __get_pydantic_json_schema__(
        self,
        schema: CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        """Dump the host schema with the branch keywords, without the branch's `type`."""
        keywords = self._branch_schema(self._get_adapter(), handler=handler)
        keywords.pop("type", None)
        return {**handler(schema), **keywords}

    def _get_adapter(self) -> TypeAdapter[AnnotationType]:
        """Build the branch adapter on first use (caches across calls).

        :returns: A `TypeAdapter` for the branch annotation.
        """
        if self._adapter is None:
            self._adapter = self._build_adapter(self._branch)
        return self._adapter

    def _check(self, value: AnnotationType, /) -> None:
        """Validate an input of the branch's type against the branch.

        :param value: A value of the branch's type.
        """
        if self._integer_branch is None or not isinstance(value, int):
            self._get_adapter().validate_python(value)
            return

        if self._integer_adapter is None:
            self._integer_adapter = self._build_adapter(self._integer_branch)

        # The default context rounds at 28 digits, so `multipleOf` misjudges a longer quotient.
        #  https://github.com/pydantic/pydantic/blob/ea492e04654ab7f7a1f9287ea912419452ead4dd/pydantic-core/src/validators/decimal.rs#L253-L260
        precision: int = Decimal(value).adjusted() + 1 + self._integer_precision_margin

        try:
            with localcontext(prec=precision):
                self._integer_adapter.validate_python(value)
        # A `Decimal` bound in `ctx` breaks `json.dumps(error.errors())`.
        except ValidationError as er:
            line_errors = [_with_float_context(error) for error in er.errors()]
            raise ValidationError.from_exception_data(er.title, line_errors) from None

    def _is_checked(self, value: AnnotationType, /) -> bool:
        """Tell whether the value is of the branch's type (a `bool` is no number)."""
        return isinstance(value, self._instance_types) and not isinstance(value, bool)

    # Pydantic calls a wrap validator positionally.
    def _validate(  # noqa: PLR0917
        self,
        value: AnnotationType,
        handler: core_schema.ValidatorFunctionWrapHandler,
    ) -> AnnotationType:
        """Check an input of the branch's type against the branch, then delegate to the host.

        An input of another type is checked once the host has produced it, when the host coerced it
        into the branch's type (`"3"` into `3`).

        :param value: Raw input value.
        :param handler: Wrapped host-type validator.
        :returns: The validated value.
        """
        if self._is_checked(value):
            self._check(value)
            return handler(value)

        result = handler(value)
        if self._is_checked(result):
            self._check(result)
        return result


def _with_float_context(error: ErrorDetails, /) -> InitErrorDetails:
    """Rebuild an error of the `Decimal` branch with its `Decimal` bounds as `float`s."""
    return InitErrorDetails(
        type=error["type"],
        loc=error["loc"],
        input=error["input"],
        ctx={key: float(bound) for key, bound in error.get("ctx", {}).items()},
    )
