"""Advanced tests for schema converters (edge cases and error handling)."""

import pytest
from openapi_pydantic import Schema

from pydantic_jsonschema import SchemaConverter


class TestConverterErrorHandling:
    """Tests for error handling in converters."""

    def test_model_caching(self) -> None:
        """Test that identical schemas reuse cached models."""
        schema1 = Schema(
            type="object",
            properties={
                "name": Schema(type="string"),
            },
        )

        schema2 = Schema(
            type="object",
            properties={
                "name": Schema(type="string"),
            },
        )

        converter = SchemaConverter()
        model1 = converter.convert_schema(schema1)
        model2 = converter.convert_schema(schema2)

        # Should be the same class object (cached)
        assert model1 is model2

    def test_literal_enum(self) -> None:
        """Test enum conversion to Literal."""
        schema = Schema(
            type="object",
            properties={"status": Schema(enum=["active", "inactive", "pending"])},
        )

        from pydantic import ValidationError

        from pydantic_jsonschema import convert_schema

        Model = convert_schema(schema)
        instance = Model(status="active")
        assert instance.status == "active"  # type: ignore[attr-defined]

        # Should validate enum values
        with pytest.raises(ValidationError):
            Model(status="invalid")

    def test_const_literal(self) -> None:
        """Test const conversion to Literal."""
        schema = Schema(type="object", properties={"constant": Schema(const="fixed_value")})

        from pydantic_jsonschema import convert_schema

        Model = convert_schema(schema)
        instance = Model(constant="fixed_value")
        assert instance.constant == "fixed_value"  # type: ignore[attr-defined]

    def test_oneof_union(self) -> None:
        """Test oneOf creates Union types."""
        schema = Schema(
            type="object",
            properties={
                "value": Schema(
                    oneOf=[
                        Schema(type="string"),
                        Schema(type="boolean"),
                    ],
                ),
            },
        )

        from pydantic_jsonschema import convert_schema

        Model = convert_schema(schema)
        instance1 = Model(value="text")
        assert instance1.value == "text"  # type: ignore[attr-defined]

        instance2 = Model(value=True)
        assert instance2.value is True  # type: ignore[attr-defined]

    def test_dict_with_additional_properties_schema(self) -> None:
        """Test dict with typed additionalProperties."""
        schema = Schema(
            type="object",
            properties={
                "metadata": Schema(type="object", additionalProperties=Schema(type="integer")),
            },
        )

        from pydantic_jsonschema import convert_schema

        Model = convert_schema(schema)
        instance = Model(metadata={"count": 42, "total": 100})
        assert instance.metadata["count"] == 42  # type: ignore[attr-defined]
        assert instance.metadata["total"] == 100  # type: ignore[attr-defined]

    def test_multiple_type_union(self) -> None:
        """Test schema with multiple types."""
        schema = Schema(
            type="object",
            properties={
                "value": Schema(type=["string", "integer", "null"]),
            },
        )

        from pydantic_jsonschema import convert_schema

        Model = convert_schema(schema)

        # Test with string
        instance1 = Model(value="text")
        assert instance1.value == "text"  # type: ignore[attr-defined]

        # Test with integer
        instance2 = Model(value=42)
        assert instance2.value == 42  # type: ignore[attr-defined]

        # Test with null
        instance3 = Model(value=None)
        assert instance3.value is None  # type: ignore[attr-defined]


class TestAdditionalPropertiesFalse:
    """Tests for additionalProperties: false."""

    def test_additional_properties_forbid(self) -> None:
        """Test that additionalProperties: false forbids extra fields."""
        schema = Schema(
            type="object",
            properties={"name": Schema(type="string")},
            additionalProperties=False,
        )

        from pydantic import ValidationError

        from pydantic_jsonschema import convert_schema

        Model = convert_schema(schema)
        instance = Model(name="Alice")
        assert instance.name == "Alice"  # type: ignore[attr-defined]

        # Extra fields should be forbidden
        with pytest.raises(ValidationError):
            Model(name="Alice", extra="field")

    def test_additional_properties_allow(self) -> None:
        """Test that additionalProperties allows extra fields."""
        schema = Schema(
            type="object",
            properties={"name": Schema(type="string")},
            additionalProperties=True,
        )

        from pydantic_jsonschema import convert_schema

        Model = convert_schema(schema)
        instance = Model(name="Alice", extra="allowed")
        assert instance.name == "Alice"  # type: ignore[attr-defined]
        assert instance.extra == "allowed"  # type: ignore[attr-defined]

    def test_dict_with_false_additional_properties(self) -> None:
        """Test dict creation with additionalProperties: false."""
        schema = Schema(
            type="object",
            properties={
                "data": Schema(type="object", additionalProperties=False),
            },
        )

        from pydantic_jsonschema import convert_schema

        Model = convert_schema(schema)
        instance = Model(data={})
        assert instance.data == {}  # type: ignore[attr-defined]


class TestMinMaxConstraints:
    """Tests for min/max constraints."""

    def test_min_items_array(self) -> None:
        """Test array with minItems constraint."""
        schema = Schema(
            type="object",
            properties={"tags": Schema(type="array", items=Schema(type="string"), minItems=1)},
        )

        from pydantic import ValidationError

        from pydantic_jsonschema import convert_schema

        Model = convert_schema(schema)
        instance = Model(tags=["tag1"])
        assert instance.tags == ["tag1"]  # type: ignore[attr-defined]

        # Empty array should fail
        with pytest.raises(ValidationError):
            Model(tags=[])

    def test_max_items_array(self) -> None:
        """Test array with maxItems constraint."""
        schema = Schema(
            type="object",
            properties={"tags": Schema(type="array", items=Schema(type="string"), maxItems=2)},
        )

        from pydantic import ValidationError

        from pydantic_jsonschema import convert_schema

        Model = convert_schema(schema)
        instance = Model(tags=["tag1", "tag2"])
        assert len(instance.tags) == 2  # type: ignore[attr-defined]

        # Too many items should fail
        with pytest.raises(ValidationError):
            Model(tags=["tag1", "tag2", "tag3"])

    def test_min_length_string(self) -> None:
        """Test string with minLength constraint."""
        schema = Schema(type="object", properties={"name": Schema(type="string", minLength=3)})

        from pydantic import ValidationError

        from pydantic_jsonschema import convert_schema

        Model = convert_schema(schema)
        instance = Model(name="abc")
        assert instance.name == "abc"  # type: ignore[attr-defined]

        # Too short should fail
        with pytest.raises(ValidationError):
            Model(name="ab")

    def test_max_length_string(self) -> None:
        """Test string with maxLength constraint."""
        schema = Schema(type="object", properties={"name": Schema(type="string", maxLength=5)})

        from pydantic import ValidationError

        from pydantic_jsonschema import convert_schema

        Model = convert_schema(schema)
        instance = Model(name="short")
        assert instance.name == "short"  # type: ignore[attr-defined]

        # Too long should fail
        with pytest.raises(ValidationError):
            Model(name="toolong")
