"""Builds the /find-product response body (API.md) from the database and map."""
from app.database.db import get_product
from app.routing.router import route_to


def find_product(conn, product_id, start="KIOSK"):
    """Return the result object, or None for an unknown product_id.

    Out-of-stock products are returned with available=False and stock=0; the
    route is still included.
    """
    product = get_product(conn, product_id)
    if product is None:
        return None
    product["route"] = route_to(conn, product["node"], product["aisle"], product["shelf"], start)
    return product
