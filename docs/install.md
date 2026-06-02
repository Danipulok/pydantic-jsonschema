# Installation

Pydantic JSON Schema is available on PyPI as [`pydantic-jsonschema`](https://pypi.org/project/pydantic-jsonschema/).

## Python Version

Requires **Python 3.12+**

## Install

Install with `uv` (recommended):

```bash
uv add pydantic-jsonschema
```

Or with `pip`:

```bash
pip install pydantic-jsonschema
```

This installs the core library with required dependencies:

- [`pydantic`](https://docs.pydantic.dev/) >= 2.0.0 - Model creation and validation
- [`openapi-pydantic`](https://github.com/kuimono/openapi-pydantic) >= 0.5.0 - JSON Schema types (`Schema`, `Reference`, `DataType`)

## Optional: Format Validators

### Base Format Validators

For JSON Schema standard format validators (email, hostname, URI, IRI, etc.):

```bash
uv add pydantic-jsonschema[formats-base]
# or
pip install pydantic-jsonschema[formats-base]
```

This adds validators for standard JSON Schema formats:

- **Email**: `email-validator` - RFC 5322 email validation
- **Hostname**: `fqdn` - RFC 1123 hostname validation
- **URI/IRI**: `rfc3986` - RFC 3986/3987 URI and IRI validation
- Date, time, datetime, UUID, IPv4, IPv6 (via Pydantic)

### Extended Format Validators

For domain-specific validators (payment cards, phone numbers, colors, etc.):

```bash
uv add pydantic-jsonschema[formats-extra]
# or
pip install pydantic-jsonschema[formats-extra]
```

This adds [`pydantic-extra-types[all]`](https://github.com/pydantic/pydantic-extra-types) for extended validators:

- Payment cards
- Phone numbers
- Colors (hex, RGB)
- Country codes
- MAC addresses
- [And many more](formats.md)

### All Format Validators

To install both base and extended validators:

```bash
uv add pydantic-jsonschema[formats-all]
# or
pip install pydantic-jsonschema[formats-all]
```

## Development Installation

Want to contribute? See the [contributing guide](contributing.md) for setup instructions.

```bash
git clone https://github.com/YOUR-USERNAME/pydantic-jsonschema.git
cd pydantic-jsonschema
just install  # Install with development dependencies
```

## Next Steps

- [Examples](examples.md) - See real-world usage
- [Contributing](contributing.md) - Help improve the library
