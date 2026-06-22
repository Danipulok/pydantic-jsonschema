"""Tests for `format` validators."""

from datetime import UTC, datetime
from ipaddress import IPv4Address
from typing import TYPE_CHECKING, Annotated, Any
from uuid import UUID

import pytest
from inline_snapshot import snapshot
from pydantic import GetCoreSchemaHandler, ValidationError
from pydantic.functional_validators import AfterValidator
from pydantic_core import CoreSchema, core_schema

from pydantic_jsonschema import (
    to_model,
)
from pydantic_jsonschema.formats import UUID as UUID_FORMAT
from pydantic_jsonschema.formats import DateTime, Email, IPv4, Uri
from pydantic_jsonschema.types import Schema
from tests.conftest import dump_errors

if TYPE_CHECKING:
    from tests.conftest import SchemaRaw

__all__: list[str] = []


class TestFormatValidators:
    """Tests for `format_validators` support: custom validators and built-in aliases."""

    def test_annotated_validator_basic(self) -> None:
        """Test basic Annotated type as validator."""

        def validate_positive(v: int) -> int:
            if v <= 0:
                msg = "Must be positive"
                raise ValueError(msg)
            return v

        PositiveInt = Annotated[int, AfterValidator(validate_positive)]  # noqa: N806

        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {"count": {"type": "integer", "format": "positive"}},
            "required": ["count"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema, format_validators={"positive": PositiveInt})

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

        def double(v: int) -> int:
            return v * 2

        def check_even(v: int) -> int:
            if v % 2 != 0:
                msg = "Must be even"
                raise ValueError(msg)
            return v

        DoubledEvenInt = Annotated[int, AfterValidator(double), AfterValidator(check_even)]  # noqa: N806

        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {"count": {"type": "integer", "format": "doubled-even"}},
            "required": ["count"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema, format_validators={"doubled-even": DoubledEvenInt})

        instance = model(count=3)
        assert instance.model_dump() == snapshot({"count": 6})

        instance = model(count=4)
        assert instance.model_dump() == snapshot({"count": 8})

    def test_callable_validator(self) -> None:
        """Test callable function as validator."""

        def validate_email_simple(v: str) -> str:
            if "@" not in v:
                msg = "Invalid email"
                raise ValueError(msg)
            return v

        schema_raw: SchemaRaw = {
            "type": "object",
            "properties": {"email": {"type": "string", "format": "email-simple"}},
            "required": ["email"],
        }
        schema = Schema.model_validate(schema_raw)
        model = to_model(schema, format_validators={"email-simple": validate_email_simple})  # type: ignore[dict-item]

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
        """Test multiple validator types in one schema."""

        def validate_positive(v: int) -> int:
            if v <= 0:
                msg = "Must be positive"
                raise ValueError(msg)
            return v

        def validate_uppercase(v: str) -> str:
            if not v.isupper():
                msg = "Must be uppercase"
                raise ValueError(msg)
            return v

        PositiveInt = Annotated[int, AfterValidator(validate_positive)]  # noqa: N806

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
            format_validators={"positive": PositiveInt, "uppercase": validate_uppercase},  # type: ignore[dict-item]
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
        model = to_model(schema, format_validators={"custom": CustomType})

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
            format_validators={
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
        model = to_model(schema, format_validators={"email": Email})

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
        model = to_model(schema, format_validators={"date-time": DateTime})

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
        model = to_model(schema, format_validators={"uuid": UUID_FORMAT})

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
        model = to_model(schema, format_validators={"ipv4": IPv4})

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
        model = to_model(schema, format_validators={"uri": Uri})

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
            format_validators={
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
