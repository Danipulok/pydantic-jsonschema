"""Validating LLM outputs with automatic type coercion."""

from pydantic_jsonschema import Schema, to_lax_model

# Define the structure you expect from the LLM
schema = Schema.model_validate(
    {
        "type": "object",
        "properties": {
            "sentiment": {"type": "string", "enum": ["positive", "negative", "neutral"]},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "entities": {"type": "array", "items": {"type": "string"}},
            "summary": {"type": "string"},
        },
        "required": ["sentiment", "confidence"],
    },
)

SentimentAnalysis = to_lax_model(schema, model_name="SentimentAnalysis")

# LLM returns data with type inconsistencies
llm_response = {
    "sentiment": "positive",
    "confidence": "0.92",  # String instead of number
    "entities": "Apple, iPhone",  # Comma-separated instead of array
    "summary": "Product review is positive",
}

# Lax validation handles it gracefully
result = SentimentAnalysis.model_validate(llm_response)

print(f"Sentiment: {result.sentiment}")  # > Sentiment: positive
print(f"Confidence: {result.confidence}")  # > Confidence: 0.92
print(f"Entities: {result.entities}")  # > Entities: ['Apple', 'iPhone']
