"""URI and IRI format validators.

See: https://www.rfc-editor.org/rfc/rfc3986
See: https://www.rfc-editor.org/rfc/rfc3987
"""

import re
from typing import Final

from pydantic_jsonschema.exceptions import FormatValidationError

__all__ = [
    "validate_iri",
    "validate_iri_reference",
    "validate_uri",
    "validate_uri_reference",
]

# See: https://www.rfc-editor.org/rfc/rfc3986#appendix-B
# Decompose a URI-reference into scheme, authority, path, query, and fragment.
_URI_RE: Final[re.Pattern[str]] = re.compile(
    r"^(?:(?P<scheme>[^:/?#]+):)?(?://(?P<authority>[^/?#]*))?(?P<path>[^?#]*)(?:\?[^#]*)?(?:#.*)?$",
)

# See: https://www.rfc-editor.org/rfc/rfc3986#section-3.1
# Scheme starts with a letter, followed by any combination of letters, digits, `+`, `-`, `.`.
_SCHEME_RE: Final[re.Pattern[str]] = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.\-]*$")

# See: https://www.rfc-editor.org/rfc/rfc3986#section-3.2
# Authority = [userinfo@]host[:port]. Host is either an IPv6 literal in brackets or a reg-name.
# Port must be digits-only; non-numeric port or unclosed IPv6 bracket fails to match.
_AUTHORITY_RE: Final[re.Pattern[str]] = re.compile(
    r"^(?:[^@]*@)?"
    r"(?:\[(?P<ipv6>[^\]]+)\]|(?P<host>[^:\[\]]*))"
    r"(?::(?P<port>[0-9]*))?$",
)

# See: https://www.rfc-editor.org/rfc/rfc3986#section-3.2.2
# IPv4 address: four decimal octets (0-255) separated by dots.
_IPV4_RE: Final[re.Pattern[str]] = re.compile(r"^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$")

_MAX_IPV4_OCTET: Final[int] = 255


def _validate_uri_reference(value: str, *, require_scheme: bool) -> str | None:
    """Validate a URI/IRI reference per RFC 3986. Returns error message or `None`."""
    match = _URI_RE.match(value)
    if match is None:
        return "Invalid URI"

    scheme: str | None = match.group("scheme") or None
    authority: str | None = match.group("authority")
    if authority is not None and authority == "":
        authority = None

    if require_scheme and scheme is None:
        return "scheme was required but missing"

    if scheme is not None and not _SCHEME_RE.match(scheme):
        return "scheme was found to be invalid"

    if authority is not None:
        auth_match = _AUTHORITY_RE.match(authority)
        if auth_match is None:
            return "host was found to be invalid"

        host: str = auth_match.group("ipv6") or auth_match.group("host") or ""
        ipv4_match = _IPV4_RE.match(host)
        if (
            auth_match.group("ipv6") is None
            and ipv4_match
            and not all(0 <= int(octet) <= _MAX_IPV4_OCTET for octet in ipv4_match.groups())
        ):
            return "host was found to be invalid"

    return None


def validate_uri(value: str) -> str:
    """Validate URI format per RFC 3986.

    :param value: Value to validate.
    :returns: Original value if valid.
    :raises FormatValidationError: If value is not a valid URI.
    """
    error: str | None = _validate_uri_reference(value, require_scheme=True)
    if error is not None:
        msg = f"Invalid URI format: `{value!r}` - {error}"
        raise FormatValidationError(
            message=msg,
            value=value,
        )

    return value


def validate_uri_reference(value: str) -> str:
    """Validate URI reference format per RFC 3986.

    :param value: Value to validate.
    :returns: Original value if valid.
    :raises FormatValidationError: If value is not a valid URI reference.
    """
    error: str | None = _validate_uri_reference(value, require_scheme=False)
    if error is not None:
        msg = f"Invalid URI reference format: `{value!r}` - {error}"
        raise FormatValidationError(
            message=msg,
            value=value,
        )

    return value


def validate_iri(value: str) -> str:
    """Validate IRI format per RFC 3987.

    :param value: Value to validate.
    :returns: Original value if valid.
    :raises FormatValidationError: If value is not a valid IRI.
    """
    error: str | None = _validate_uri_reference(value, require_scheme=True)
    if error is not None:
        msg = f"Invalid IRI format: `{value!r}` - {error}"
        raise FormatValidationError(
            message=msg,
            value=value,
        )

    return value


def validate_iri_reference(value: str) -> str:
    """Validate IRI reference format per RFC 3987.

    :param value: Value to validate.
    :returns: Original value if valid.
    :raises FormatValidationError: If value is not a valid IRI reference.
    """
    error: str | None = _validate_uri_reference(value, require_scheme=False)
    if error is not None:
        msg = f"Invalid IRI reference format: `{value!r}` - {error}"
        raise FormatValidationError(
            message=msg,
            value=value,
        )

    return value
