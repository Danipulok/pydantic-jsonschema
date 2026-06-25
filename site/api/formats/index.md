# Formats

For usage and examples, see the [Formats guide](https://danipulok.github.io/pydantic-jsonschema/0.0.12/formats/index.md).

Built-in format types for JSON Schema validation.

This module exports Pydantic-compatible types for all formats defined in [JSON Schema §7.3](https://json-schema.org/draft/2020-12/json-schema-validation#section-7.3). Use them directly in Pydantic models or pass them as `formats` to `SchemaConverter`.

## UUID

```python
UUID = UUID
```

UUID value.

Source: [RFC 4122](https://www.rfc-editor.org/rfc/rfc4122)

## Date

```python
Date = date
```

Calendar date.

Source: [RFC 3339](https://www.rfc-editor.org/rfc/rfc3339)

## DateTime

```python
DateTime = datetime
```

Date-time value.

Source: [RFC 3339](https://www.rfc-editor.org/rfc/rfc3339)

## Duration

```python
Duration = timedelta
```

Duration.

Source: [RFC 3339, appendix A](https://www.rfc-editor.org/rfc/rfc3339#appendix-A)

## Email

```python
Email = Annotated[str, AfterValidator(validate_email)]
```

Email address.

Source: [RFC 5321](https://www.rfc-editor.org/rfc/rfc5321#section-4.1.2)

## Hostname

```python
Hostname = Annotated[str, AfterValidator(validate_hostname)]
```

Hostname.

Source: [RFC 1123](https://www.rfc-editor.org/rfc/rfc1123#section-2.1)

## IdnEmail

```python
IdnEmail = Annotated[str, AfterValidator(validate_idn_email)]
```

Internationalized email address.

Source: [RFC 6531](https://www.rfc-editor.org/rfc/rfc6531#section-3.3)

## IdnHostname

```python
IdnHostname = Annotated[str, AfterValidator(validate_idn_hostname)]
```

Internationalized hostname.

Source: [RFC 5890](https://www.rfc-editor.org/rfc/rfc5890#section-2.3.2.3)

## IPv4

```python
IPv4 = IPv4Address
```

IPv4 address.

Source: [RFC 2673, section 3.2](https://www.rfc-editor.org/rfc/rfc2673#section-3.2)

## IPv6

```python
IPv6 = IPv6Address
```

IPv6 address.

Source: [RFC 4291, section 2.2](https://www.rfc-editor.org/rfc/rfc4291#section-2.2)

## Iri

```python
Iri = Annotated[str, AfterValidator(validate_iri)]
```

Absolute internationalized URI.

Source: [RFC 3987](https://www.rfc-editor.org/rfc/rfc3987)

## IriReference

```python
IriReference = Annotated[str, AfterValidator(validate_iri_reference)]
```

IRI reference, absolute or relative.

Source: [RFC 3987](https://www.rfc-editor.org/rfc/rfc3987)

## JsonPointer

```python
JsonPointer = Annotated[str, AfterValidator(validate_json_pointer)]
```

JSON Pointer.

Source: [RFC 6901](https://www.rfc-editor.org/rfc/rfc6901#section-3)

## Regex

```python
Regex = Annotated[str, AfterValidator(validate_regex)]
```

Regular expression, ECMA-262 dialect.

Source: [JSON Schema §7.3.8](https://json-schema.org/draft/2020-12/json-schema-validation#section-7.3.8)

## RelativeJsonPointer

```python
RelativeJsonPointer = Annotated[
    str, AfterValidator(validate_relative_json_pointer)
]
```

Relative JSON Pointer.

Source: [draft-bhutton-relative-json-pointer-00](https://datatracker.ietf.org/doc/html/draft-bhutton-relative-json-pointer-00#section-3)

## Time

```python
Time = time
```

Time value.

Source: [RFC 3339](https://www.rfc-editor.org/rfc/rfc3339)

## Uri

```python
Uri = Annotated[str, AfterValidator(validate_uri)]
```

Absolute URI with a scheme.

Source: [RFC 3986](https://www.rfc-editor.org/rfc/rfc3986)

## UriReference

```python
UriReference = Annotated[str, AfterValidator(validate_uri_reference)]
```

URI reference, absolute or relative.

Source: [RFC 3986, section 4.1](https://www.rfc-editor.org/rfc/rfc3986#section-4.1)

## UriTemplate

```python
UriTemplate = Annotated[str, AfterValidator(validate_uri_template)]
```

URI Template.

Source: [RFC 6570](https://www.rfc-editor.org/rfc/rfc6570#section-2)
