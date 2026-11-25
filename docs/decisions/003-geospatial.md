# Geospatial storage

PostGIS is the production engine, selected by a `postgis://` database URL. Tests and a laptop without Docker use SpatiaLite so polygon fields still run. CI does not start PostGIS.

Hectares use a spherical shoelace approximation rounded to 0.01. That is good enough to show a boundary's order of magnitude. A survey-grade area would use a local projected CRS and is not claimed here.

Mapbox is optional. The console can sketch a stored polygon without a token. No map tile is invented when the token is absent.
