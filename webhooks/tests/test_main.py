from webhooks.web.main import create_app
from webhooks.web.routers import sse, webhooks, websocket


def test_create_app():
    app = create_app()
    assert app.title == "Aries Cloud API: Webhooks and Server-Sent Events"

    # Verifying that all routes are included

    # Get all routes in app
    routes = [route.path for route in app.routes]

    # Get expected routes from all the routers
    routers = [sse, webhooks, websocket]
    nested_list = [m.router.routes for m in routers]
    flattened_routers_list = [item for sublist in nested_list for item in sublist]
    expected_routes = [r.path for r in flattened_routers_list]
    for route in expected_routes:
        assert route in routes
