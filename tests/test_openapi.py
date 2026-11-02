import json

import pytest

from discover.openapi import import_openapi


def test_import_openapi_json_resolves_schemas_and_persists(fake_project, tmp_path):
    spec_path = tmp_path / "openapi.json"
    spec_path.write_text(
        json.dumps(
            {
                "openapi": "3.1.0",
                "info": {"title": "Test API", "version": "1"},
                "paths": {
                    "/users": {
                        "post": {
                            "requestBody": {
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/User"}
                                    }
                                }
                            },
                            "responses": {
                                "201": {
                                    "content": {
                                        "application/json": {
                                            "schema": {
                                                "$ref": "#/components/schemas/User"
                                            }
                                        }
                                    }
                                },
                                "200": {
                                    "content": {
                                        "application/json": {
                                            "schema": {"type": "boolean"}
                                        }
                                    }
                                },
                            },
                        }
                    }
                },
                "components": {
                    "schemas": {
                        "User": {
                            "type": "object",
                            "properties": {"name": {"type": "string"}},
                        }
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    imported = import_openapi(spec_path)

    assert imported[0]["method"] == "POST"
    assert imported[0]["body"]["properties"]["name"]["type"] == "string"
    assert imported[0]["response_status"] == 200
    assert imported[0]["response_body"] == {"type": "boolean"}

    saved = json.loads((fake_project / "milk-man" / "endpoints.json").read_text())
    assert isinstance(saved[0]["body"], dict)
    assert saved[0]["response_body"] == {"type": "boolean"}
    assert saved[0]["observed_by"] == {
        "source_code": False,
        "live_traffic": False,
        "imported": True,
    }


def test_import_openapi_yaml_extracts_parameters_and_response(fake_project, tmp_path):
    spec_path = tmp_path / "openapi.yaml"
    spec_path.write_text(
        """
openapi: 3.0.3
info:
  title: Test API
  version: "1"
paths:
  /users/{user_id}:
    parameters:
      - name: user_id
        in: path
        required: true
        schema:
          type: integer
    get:
      responses:
        "200":
          content:
            application/json:
              schema:
                type: object
                properties:
                  id:
                    type: integer
""",
        encoding="utf-8",
    )

    imported = import_openapi(spec_path)

    assert imported[0]["body"] == {"user_id": {"type": "integer"}}
    assert imported[0]["response_status"] == 200
    assert imported[0]["response_body"]["type"] == "object"


@pytest.mark.parametrize("version", ["2.0", "3.2.0"])
def test_import_openapi_rejects_unsupported_versions(tmp_path, version):
    spec_path = tmp_path / "openapi.json"
    spec_path.write_text(
        json.dumps({"openapi": version, "paths": {}}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Only OpenAPI 3.0 and 3.1"):
        import_openapi(spec_path)
