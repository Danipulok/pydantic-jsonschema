"""Tests for the `formats` parameter."""

from datetime import UTC, datetime
from ipaddress import IPv4Address
from typing import TYPE_CHECKING, Annotated, Any, TypeAliasType, override
from uuid import UUID

import pytest
from inline_snapshot import snapshot
from pydantic import GetCoreSchemaHandler, ValidationError
from pydantic.functional_validators import AfterValidator
from pydantic_core import CoreSchema, core_schema

from pydantic_jsonschema import (
    to_model,
)
from pydantic_jsonschema.exceptions import SchemaConversionError
from pydantic_jsonschema.formats import UUID as UUID_FORMAT
from pydantic_jsonschema.formats import DateTime, Email, IPv4, Uri
from pydantic_jsonschema.schema import Schema
from tests.conftest import dump_errors

if TYPE_CHECKING:
    from tests.conftest import SchemaRaw

__all__: list[str] = []


class TestFormats:
    """Tests for `formats` support: custom format types and built-in aliases."""

    def test_annotated_validator_basic(self) -> None:
        """Test basic Annotated type as validator."""

        def validate_positive(value: int) -> int:
            if value <= 0:
                msg = "Must be positive"
                raise ValueError(msg)
            return value

        PositiveInt = Annotated[int, AfterValidator(validate_positive)]  # noqa: N806

        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {"count": {"type": "integer", "format": "positive"}},
            "required": ["count"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema, formats={"positive": PositiveInt})

        instance = model(count=5)
        assert instance.model_dump() == snapshot({"count": 5})

        with pytest.raises(ValidationError) as exc_info:
            model(count=-1)

        assert dump_errors(exc_info.value) == snapshot(
            [
                {
                    "type": "value_error",
                    "loc": ("count",),
                    "msg": "Value error, Must be positive",
                    "input": -1,
                }
            ]
        )

    def test_annotated_validator_with_transformation(self) -> None:
        """Test Annotated type with value transformation."""

        def double(value: int) -> int:
            return value * 2

        def check_even(value: int) -> int:
            if value % 2 != 0:
                msg = "Must be even"
                raise ValueError(msg)
            return value

        DoubledEvenInt = Annotated[int, AfterValidator(double), AfterValidator(check_even)]  # noqa: N806

        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {"count": {"type": "integer", "format": "doubled-even"}},
            "required": ["count"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema, formats={"doubled-even": DoubledEvenInt})

        instance = model(count=3)
        assert instance.model_dump() == snapshot({"count": 6})

        instance = model(count=4)
        assert instance.model_dump() == snapshot({"count": 8})

    def test_annotated_str_validator(self) -> None:
        """Test an `Annotated` string type as a format."""

        def validate_email_simple(value: str) -> str:
            if "@" not in value:
                msg = "Invalid email"
                raise ValueError(msg)
            return value

        EmailSimple = Annotated[str, AfterValidator(validate_email_simple)]  # noqa: N806

        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {"email": {"type": "string", "format": "email-simple"}},
            "required": ["email"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema, formats={"email-simple": EmailSimple})

        instance = model(email="test@example.com")
        assert instance.model_dump() == snapshot({"email": "test@example.com"})

        with pytest.raises(ValidationError) as exc_info:
            model(email="invalid")

        assert dump_errors(exc_info.value) == snapshot(
            [
                {
                    "type": "value_error",
                    "loc": ("email",),
                    "msg": "Value error, Invalid email",
                    "input": "invalid",
                }
            ]
        )

    def test_mixed_validators(self) -> None:
        """Test multiple format types in one schema."""

        def validate_positive(value: int) -> int:
            if value <= 0:
                msg = "Must be positive"
                raise ValueError(msg)
            return value

        def validate_uppercase(value: str) -> str:
            if not value.isupper():
                msg = "Must be uppercase"
                raise ValueError(msg)
            return value

        PositiveInt = Annotated[int, AfterValidator(validate_positive)]  # noqa: N806
        Uppercase = Annotated[str, AfterValidator(validate_uppercase)]  # noqa: N806

        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "count": {"type": "integer", "format": "positive"},
                "code": {"type": "string", "format": "uppercase"},
            },
            "required": ["count", "code"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(
            schema,
            formats={"positive": PositiveInt, "uppercase": Uppercase},
        )

        instance = model(count=5, code="ABC")
        assert instance.model_dump() == snapshot({"count": 5, "code": "ABC"})

        with pytest.raises(ValidationError) as exc_info:
            model(count=-1, code="ABC")

        assert dump_errors(exc_info.value) == snapshot(
            [
                {
                    "type": "value_error",
                    "loc": ("count",),
                    "msg": "Value error, Must be positive",
                    "input": -1,
                }
            ]
        )

        with pytest.raises(ValidationError) as exc_info:
            model(count=5, code="abc")

        assert dump_errors(exc_info.value) == snapshot(
            [
                {
                    "type": "value_error",
                    "loc": ("code",),
                    "msg": "Value error, Must be uppercase",
                    "input": "abc",
                }
            ]
        )

    def test_validator_as_type_class(self) -> None:
        """Test validator as type class."""

        class CustomType:
            def __init__(self, value: str) -> None:
                if not value.startswith("custom:"):
                    msg = "Must start with 'custom:'"
                    raise ValueError(msg)
                self.value = value

            @override
            def __str__(self) -> str:
                return self.value

            @classmethod
            def __get_pydantic_core_schema__(
                cls,
                source_type: Any,  # noqa: ANN401
                handler: GetCoreSchemaHandler,
            ) -> CoreSchema:
                return core_schema.no_info_after_validator_function(
                    cls,
                    handler(str),
                    serialization=core_schema.plain_serializer_function_ser_schema(
                        lambda x: x.value,
                        return_schema=core_schema.str_schema(),
                    ),
                )

        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "field": {"type": "string", "format": "custom"},
            },
            "required": ["field"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema, formats={"custom": CustomType})

        instance = model(field="custom:value")
        assert instance.model_dump() == snapshot(
            {
                "field": "custom:value",
            }
        )

    def test_native_python_types_as_validators(self) -> None:
        """Test native Python types (datetime, UUID, etc.) as format validators."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "created_at": {"type": "string", "format": "date-time"},
                "email": {"type": "string", "format": "email"},
                "id": {"type": "string", "format": "uuid"},
                "ip": {"type": "string", "format": "ipv4"},
            },
            "required": ["created_at", "email", "id", "ip"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(
            schema,
            formats={
                "date-time": datetime,
                "email": Email,
                "uuid": UUID_FORMAT,
                "ipv4": IPv4Address,
            },
        )

        annotations = model.model_fields

        assert annotations["created_at"].annotation is datetime
        assert annotations["email"].annotation is str
        assert annotations["id"].annotation is UUID
        assert annotations["ip"].annotation is IPv4Address

        instance = model(
            created_at="2024-01-15T10:30:00",
            email="test@example.com",
            id="550e8400-e29b-41d4-a716-446655440000",
            ip="192.168.1.1",
        )

        assert isinstance(instance.created_at, datetime)  # type: ignore[attr-defined]
        assert isinstance(instance.email, str)  # type: ignore[attr-defined]
        assert isinstance(instance.id, UUID)  # type: ignore[attr-defined]
        assert isinstance(instance.ip, IPv4Address)  # type: ignore[attr-defined]

    def test_schema_format_email(self) -> None:
        """Test SchemaFormat EMAIL validator with to_model."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "email": {"type": "string", "format": "email"},
            },
            "required": ["email"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema, formats={"email": Email})

        instance = model(email="alice@example.com")
        assert instance.model_dump() == snapshot(
            {
                "email": "alice@example.com",
            }
        )

        with pytest.raises(ValidationError):
            model(email="not-an-email")

    def test_schema_format_date_time(self) -> None:
        """Test SchemaFormat DATE_TIME validator with to_model."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "created_at": {"type": "string", "format": "date-time"},
            },
            "required": ["created_at"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema, formats={"date-time": DateTime})

        instance = model(created_at="2024-01-15T10:30:00Z")

        assert instance.model_dump() == snapshot(
            {
                "created_at": datetime(
                    year=2024,
                    month=1,
                    day=15,
                    hour=10,
                    minute=30,
                    tzinfo=UTC,
                ),
            }
        )

        with pytest.raises(ValidationError):
            model(created_at="not-a-datetime")

    def test_schema_format_uuid(self) -> None:
        """Test SchemaFormat UUID validator with to_model."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "id": {"type": "string", "format": "uuid"},
            },
            "required": ["id"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema, formats={"uuid": UUID_FORMAT})

        instance = model(id="550e8400-e29b-41d4-a716-446655440000")
        assert instance.model_dump() == snapshot(
            {
                "id": UUID("550e8400-e29b-41d4-a716-446655440000"),
            }
        )

        with pytest.raises(ValidationError):
            model(id="not-a-uuid")

    def test_schema_format_ipv4(self) -> None:
        """Test SchemaFormat IPV4 validator with to_model."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "ip": {"type": "string", "format": "ipv4"},
            },
            "required": ["ip"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema, formats={"ipv4": IPv4})

        instance = model(ip="192.168.1.1")
        assert instance.model_dump() == snapshot(
            {
                "ip": IPv4Address("192.168.1.1"),
            }
        )

        with pytest.raises(ValidationError):
            model(ip="999.999.999.999")

    def test_schema_format_uri(self) -> None:
        """Test SchemaFormat URI validator with to_model."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "website": {"type": "string", "format": "uri"},
            },
            "required": ["website"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema, formats={"uri": Uri})

        instance = model(website="https://example.com")
        assert instance.model_dump() == snapshot(
            {
                "website": "https://example.com",
            }
        )

        with pytest.raises(ValidationError):
            model(website="example.com")

    def test_schema_format_multiple_formats(self) -> None:
        """Test multiple SchemaFormat validators in one model."""
        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {
                "email": {"type": "string", "format": "email"},
                "website": {"type": "string", "format": "uri"},
                "created_at": {"type": "string", "format": "date-time"},
                "id": {"type": "string", "format": "uuid"},
                "ip": {"type": "string", "format": "ipv4"},
            },
            "required": ["email", "website", "created_at", "id", "ip"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(
            schema,
            formats={
                "email": Email,
                "uri": Uri,
                "date-time": DateTime,
                "uuid": UUID_FORMAT,
                "ipv4": IPv4,
            },
        )

        instance = model(
            email="alice@example.com",
            website="https://example.com",
            created_at="2024-01-15T10:30:00Z",
            id="550e8400-e29b-41d4-a716-446655440000",
            ip="192.168.1.1",
        )

        assert instance.model_dump() == snapshot(
            {
                "email": "alice@example.com",
                "website": "https://example.com",
                "created_at": datetime(
                    year=2024,
                    month=1,
                    day=15,
                    hour=10,
                    minute=30,
                    tzinfo=UTC,
                ),
                "id": UUID("550e8400-e29b-41d4-a716-446655440000"),
                "ip": IPv4Address("192.168.1.1"),
            }
        )


class TestFormatAcceptedForms:
    """A `formats` entry must be a type or `Annotated` type; any other form is rejected."""

    @pytest.mark.parametrize(
        ("format_type", "value", "expected"),
        [
            pytest.param(
                Annotated[str, AfterValidator(str.upper)],
                "abc",
                "ABC",
                id="raw-annotated",
            ),
            pytest.param(IPv4Address, "1.2.3.4", IPv4Address("1.2.3.4"), id="plain-class"),
            pytest.param(Email, "alice@example.com", "alice@example.com", id="type-alias"),
        ],
    )
    def test_accepted_forms(
        self,
        format_type: type | TypeAliasType,
        value: str,
        expected: IPv4Address | str,
    ) -> None:
        """Each accepted form (raw `Annotated`, plain class, PEP 695 alias) is applied."""
        schema = Schema.model_validate(
            {
                "type": "object",
                "properties": {"field": {"type": "string", "format": "custom"}},
                "required": ["field"],
            }
        )
        model = to_model(schema, formats={"custom": format_type})

        assert model(field=value).model_dump() == {"field": expected}

    def test_bare_callable_rejected(self) -> None:
        """A bare callable (not a type / `Annotated`) is rejected with a clear error."""

        def normalize(value: str) -> str:
            return value.strip()

        schema = Schema.model_validate(
            {
                "type": "object",
                "properties": {"code": {"type": "string", "format": "code"}},
                "required": ["code"],
            }
        )

        with pytest.raises(SchemaConversionError, match=r"must be a type or `Annotated` type"):
            to_model(schema, formats={"code": normalize})  # type: ignore[dict-item]
