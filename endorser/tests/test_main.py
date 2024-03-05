from endorser.main import app


def test_create_app():
    assert app.title == "Aries Cloud API: Endorser Service"

    # Verifying that all routes are included

    # Get all routes in app
    routes = [route.path for route in app.routes]

    expected_routes = "/health"
    assert expected_routes in routes
