from unittest.mock import patch

from app.main import create_app


def test_create_app():
    with patch("os.getenv") as mock_getenv:
        mock_getenv.return_value = "False"  # Mock the 'prod' environment variable
        app = create_app()
        assert app.title == "OpenAPI"

        # Verifying that all routes are included
        routes = [route.path for route in app.routes]
        expected_routes = ["/openapi.json", "/v1/tenants"]
        for route in expected_routes:
            assert route in routes
