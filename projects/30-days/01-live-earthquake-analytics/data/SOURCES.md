# Country boundary data

The bundled `countries.geojson` contains 177 countries/areas from Natural Earth
1:110m Admin 0 country geometry, downloaded on 25 October 2026.

Source: https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_110m_admin_0_countries.geojson

Licence: public domain. Terms: https://www.naturalearthdata.com/about/terms-of-use/

Modifications: retained the country name, ISO/admin code, label point and geometry;
rounded coordinates to four decimals; removed unrelated properties. Geometry
remains coarse and is unsuitable for exact border, coastal or territorial claims.
Small countries/islands may be absent at this scale. The interface uses
“country/area” labels and identifies this limitation. Country filtering tests a
point against the polygon, including holes, rather than treating a rectangular
bounding box as a country. Offshore earthquakes are excluded from land filters.

The country's default weather point is a city or an explicitly labelled
representative location. A point forecast does not describe every part of that
country. Users may change the coordinates within the mapped area.
