"""Tests for schema dumping."""

from pydantic import BaseModel

from pydantic_jsonschema import model_dump_json_schema


class TestSchemaDumping:
    """Tests for model_dump_json_schema."""

    def test_simple_model_dump(self):
        """Test dumping a simple model to JSON Schema."""
        class User(BaseModel):
            name: str
            age: int

        schema = model_dump_json_schema(User)

        assert schema["type"] == "object"
        assert "name" in schema["properties"]
        assert "age" in schema["properties"]
        assert schema["properties"]["name"]["type"] == "string"
        assert schema["properties"]["age"]["type"] == "integer"
        assert "name" in schema["required"]
        assert "age" in schema["required"]

    def test_nested_model_dump(self):
        """Test dumping nested models."""
        class Address(BaseModel):
            street: str
            city: str

        class User(BaseModel):
            name: str
            address: Address

        schema = model_dump_json_schema(User)

        assert "$defs" in schema
        assert "Address" in schema["$defs"]
        assert "address" in schema["properties"]

    def test_dump_with_custom_refs(self):
        """Test dumping with custom reference URIs."""
        class Address(BaseModel):
            street: str
            city: str

        class User(BaseModel):
            name: str
            address: Address

        refs = {"#/components/schemas/Address": Address}
        schema = model_dump_json_schema(User, refs=refs)

        # Check that schema was generated
        assert "properties" in schema
        assert "address" in schema["properties"]

    def test_dump_by_alias(self):
        """Test schema generation respects by_alias parameter."""
        from pydantic import Field

        class User(BaseModel):
            name: str = Field(alias="userName")

        schema_alias = model_dump_json_schema(User, by_alias=True)
        schema_no_alias = model_dump_json_schema(User, by_alias=False)

        # With alias
        assert "userName" in schema_alias["properties"]
        # Without alias
        assert "name" in schema_no_alias["properties"]
