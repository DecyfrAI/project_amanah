"""The published OpenAPI document is the service-boundary contract (B-S2.2, B-S2.5).

The frontend validates both its fixture and live providers against this document,
so these assertions guard the contract itself rather than any one endpoint.
"""

from typing import Any

from fastapi import FastAPI

OPERATIONAL_PATHS = {"/healthz", "/readyz"}


def openapi(app: FastAPI) -> dict[str, Any]:
    document: dict[str, Any] = app.openapi()
    return document


def product_operations(document: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (path, method): operation
        for path, methods in document["paths"].items()
        if path.startswith("/v1")
        for method, operation in methods.items()
    }


def test_document_declares_a_single_major_version(app: FastAPI) -> None:
    document = openapi(app)

    assert all(path.startswith("/v1") or path in OPERATIONAL_PATHS for path in document["paths"]), (
        document["paths"].keys()
    )


def test_every_product_operation_requires_bearer_authentication(app: FastAPI) -> None:
    operations = product_operations(openapi(app))

    assert operations
    for (path, method), operation in operations.items():
        requirements = operation.get("security", [])
        assert requirements, f"{method.upper()} {path} publishes no security requirement"
        assert any("HTTPBearer" in requirement for requirement in requirements)


def test_bearer_scheme_is_declared(app: FastAPI) -> None:
    schemes = openapi(app)["components"]["securitySchemes"]

    assert schemes["HTTPBearer"]["type"] == "http"
    assert schemes["HTTPBearer"]["scheme"] == "bearer"


def test_operational_endpoints_stay_unauthenticated(app: FastAPI) -> None:
    document = openapi(app)

    for path in OPERATIONAL_PATHS:
        for operation in document["paths"][path].values():
            assert not operation.get("security")


def test_product_operations_document_the_denial_responses(app: FastAPI) -> None:
    for (path, method), operation in product_operations(openapi(app)).items():
        assert "401" in operation["responses"], f"{method.upper()} {path} omits 401"
        assert "403" in operation["responses"], f"{method.upper()} {path} omits 403"


def test_error_envelope_is_part_of_the_published_contract(app: FastAPI) -> None:
    schemas = openapi(app)["components"]["schemas"]

    envelope = schemas["ErrorEnvelope"]
    body = schemas["ErrorBody"]

    assert envelope["required"] == ["error"]
    assert set(body["required"]) == {"code", "message", "request_id", "retryable"}
    assert set(body["properties"]) == {"code", "message", "request_id", "retryable", "details"}


def test_error_codes_are_published_as_a_closed_set(app: FastAPI) -> None:
    codes = openapi(app)["components"]["schemas"]["ErrorCode"]["enum"]

    assert "AUTHENTICATION_REQUIRED" in codes
    assert "PERMISSION_DENIED" in codes
    assert "UNSUPPORTED_FILTER" in codes
    assert "VALIDATION_FAILED" in codes


def test_published_field_names_are_snake_case(app: FastAPI) -> None:
    schemas = openapi(app)["components"]["schemas"]

    for name, schema in schemas.items():
        for field in schema.get("properties", {}):
            assert field == field.lower(), f"{name}.{field} is not snake_case"
            assert " " not in field and "-" not in field
