import importlib.util

try:
    importlib.util.find_spec("fqdn")
    importlib.util.find_spec("rfc3986")
except ImportError as _import_error:
    msg = (
        "`fqdn` and `rfc3986` are required to use JsonSchema formats. "
        "Install them with: `pip install pydantic-jsonschema[formats-base]` or "
        "`pip install pydantic-jsonschema[formats-all]`."
    )
    raise ImportError(msg) from _import_error

from fqdn import FQDN
from rfc3986 import (  # type: ignore[attr-defined]
    IRIReference,
    URIReference,
    exceptions,
    validators,
)

from pydantic_jsonschema.exceptions import FormatValidationError
from pydantic_jsonschema.types import JsonType

__all__ = [
    "validate_hostname",
    "validate_iri",
    "validate_iri_reference",
    "validate_uri",
    "validate_uri_reference",
]

# Reusable validators for URI/IRI
_URI_VALIDATOR = validators.Validator().require_presence_of("scheme")
_URI_REFERENCE_VALIDATOR = validators.Validator()
_IRI_VALIDATOR = validators.Validator().require_presence_of("scheme")
_IRI_REFERENCE_VALIDATOR = validators.Validator()


def validate_hostname(value: JsonType) -> str:
    """Validate hostname format per RFC 1123, section 2.1.

    Validates Internet host names as defined by RFC 1123, which allows
    both single labels (e.g., "localhost") and fully qualified domain
    names (e.g., "example.com").

    :param value: Value to validate.
    :returns: Original value if valid.
    :raises FormatValidationError: If value is not a valid hostname.
    """
    if not isinstance(value, str):
        msg = f"Expected string, got: `{value!r}`"
        raise FormatValidationError(
            message=msg,
            value=value,
        )

    # RFC 1123 allows hostnames with a single label (min_labels=1)
    # Default is 2, which would reject "localhost"
    fqdn = FQDN(value, min_labels=1)  # type: ignore[no-untyped-call]
    if not fqdn.is_valid:
        msg = f"Invalid hostname format: `{value!r}`"
        raise FormatValidationError(
            message=msg,
            value=value,
        )

    return value


# URI validators
def validate_uri(value: JsonType) -> str:
    """Validate URI format (RFC 3986) using rfc3986 library.

    :param value: Value to validate.
    :returns: Original value if valid.
    :raises FormatValidationError: If value is not a valid URI.
    """
    if not isinstance(value, str):
        msg = f"Expected string, got: `{value!r}`"
        raise FormatValidationError(
            message=msg,
            value=value,
        )

    try:
        uri = URIReference.from_string(value)
        _URI_VALIDATOR.validate(uri)
    except exceptions.ValidationError as exc:
        # Extract error message from ValidationError tuple
        error_msg = exc.args[0] if exc.args else "Invalid URI"
        msg = f"Invalid URI format: `{value!r}` - {error_msg}"
        raise FormatValidationError(
            message=msg,
            value=value,
        ) from exc

    return value


def validate_uri_reference(value: JsonType) -> str:
    """Validate URI reference format (RFC 3986) using rfc3986 library.

    URI reference can be either an absolute URI or a relative reference.

    :param value: Value to validate.
    :returns: Original value if valid.
    :raises FormatValidationError: If value is not a valid URI reference.
    """
    if not isinstance(value, str):
        msg = f"Expected string, got: `{value!r}`"
        raise FormatValidationError(
            message=msg,
            value=value,
        )

    try:
        uri_ref = URIReference.from_string(value)
        _URI_REFERENCE_VALIDATOR.validate(uri_ref)
    except exceptions.ValidationError as exc:  # pragma: no cover
        # Extract error message from ValidationError tuple
        error_msg = exc.args[0] if exc.args else "Invalid URI reference"
        msg = f"Invalid URI reference format: `{value!r}` - {error_msg}"
        raise FormatValidationError(
            message=msg,
            value=value,
        ) from exc

    return value


# IRI validators (Internationalized Resource Identifier)
def validate_iri(value: JsonType) -> str:
    """Validate IRI format (RFC 3987) using rfc3986 library.

    Similar to URI but allows international characters.

    :param value: Value to validate.
    :returns: Original value if valid.
    :raises FormatValidationError: If value is not a valid IRI.
    """
    if not isinstance(value, str):
        msg = f"Expected string, got: `{value!r}`"
        raise FormatValidationError(
            message=msg,
            value=value,
        )

    try:
        iri = IRIReference.from_string(value)
        _IRI_VALIDATOR.validate(iri)
    except exceptions.ValidationError as exc:
        # Extract error message from ValidationError tuple
        error_msg = exc.args[0] if exc.args else "Invalid IRI"
        msg = f"Invalid IRI format: `{value!r}` - {error_msg}"
        raise FormatValidationError(
            message=msg,
            value=value,
        ) from exc

    return value


def validate_iri_reference(value: JsonType) -> str:
    """Validate IRI reference format (RFC 3987) using rfc3986 library.

    IRI reference can be either an absolute IRI or a relative reference.

    :param value: Value to validate.
    :returns: Original value if valid.
    :raises FormatValidationError: If value is not a valid IRI reference.
    """
    if not isinstance(value, str):
        msg = f"Expected string, got: `{value!r}`"
        raise FormatValidationError(
            message=msg,
            value=value,
        )

    try:
        iri_ref = IRIReference.from_string(value)
        _IRI_REFERENCE_VALIDATOR.validate(iri_ref)
    except exceptions.ValidationError as exc:  # pragma: no cover
        # Extract error message from ValidationError tuple
        error_msg = exc.args[0] if exc.args else "Invalid IRI reference"
        msg = f"Invalid IRI reference format: `{value!r}` - {error_msg}"
        raise FormatValidationError(
            message=msg,
            value=value,
        ) from exc

    return value
