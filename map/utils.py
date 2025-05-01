import pyproj

def convert_tm_to_wgs84(x, y):
    transformer = pyproj.Transformer.from_crs("epsg:5186", "epsg:4326", always_xy=True)
    lon, lat = transformer.transform(x, y)
    return lat, lon
