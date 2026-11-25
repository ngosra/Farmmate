import json
import math
from decimal import ROUND_HALF_UP, Decimal

from django.contrib.gis.geos import GEOSGeometry, Polygon
from rest_framework.exceptions import ValidationError

EARTH_RADIUS_M = 6378137.0


def polygon_from_geojson(value) -> Polygon:
    if not isinstance(value, dict) or value.get("type") != "Polygon":
        raise ValidationError("Boundary must be a GeoJSON Polygon.")
    try:
        geom = GEOSGeometry(json.dumps(value), srid=4326)
    except Exception as exc:
        raise ValidationError("Boundary could not be read as a polygon.") from exc
    if geom.geom_type != "Polygon" or not geom.valid:
        raise ValidationError("Boundary is not a valid polygon.")
    ring = geom.coords[0]
    if len(ring) < 4 or ring[0] != ring[-1]:
        raise ValidationError("Boundary ring must be closed.")
    for lon, lat in ring:
        if not -180 <= lon <= 180 or not -90 <= lat <= 90:
            raise ValidationError("Boundary coordinates are out of range.")
    return geom


def polygon_to_geojson(geom):
    if geom is None:
        return None
    return json.loads(geom.geojson)


def hectares_from_polygon(polygon: Polygon) -> Decimal:
    ring = list(polygon.coords[0])
    if len(ring) < 4:
        return Decimal("0.00")
    total = 0.0
    for (lon1, lat1), (lon2, lat2) in zip(ring, ring[1:], strict=False):
        total += math.radians(lon2 - lon1) * (
            2 + math.sin(math.radians(lat1)) + math.sin(math.radians(lat2))
        )
    meters = abs(total) * EARTH_RADIUS_M * EARTH_RADIUS_M / 2.0
    return Decimal(str(meters / 10000)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
