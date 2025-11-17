"""Handle complex schemas with multiple levels of nesting and references."""

from pydantic_jsonschema import Schema, to_model

blog_schema = Schema.model_validate(
    {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "author": {"$ref": "#/$defs/Person"},
            "comments": {"type": "array", "items": {"$ref": "#/$defs/Comment"}},
            "tags": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["title", "author"],
        "$defs": {
            "Person": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "email": {"type": "string", "format": "email"},
                },
                "required": ["name"],
            },
            "Comment": {
                "type": "object",
                "properties": {
                    "author": {"$ref": "#/$defs/Person"},
                    "text": {"type": "string"},
                    "timestamp": {"type": "string"},
                },
                "required": ["author", "text"],
            },
        },
    },
)

BlogPost = to_model(blog_schema, model_name="BlogPost")

# Create a blog post with nested data
post = BlogPost(
    title="Getting Started with Pydantic JSON Schema",
    author={"name": "Alice", "email": "alice@example.com"},
    comments=[
        {
            "author": {"name": "Bob"},
            "text": "Great article!",
            "timestamp": "2024-01-15T10:30:00Z",
        },
    ],
    tags=["python", "pydantic", "json-schema"],
)

print(post.title)  # type: ignore[attr-defined]
# > Getting Started with Pydantic JSON Schema
print(len(post.comments))  # type: ignore[attr-defined]
# > 1
print(post.comments[0].text)  # type: ignore[attr-defined]
# > Great article!
