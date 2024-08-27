from geopy.geocoders import Nominatim

geolocator = Nominatim(user_agent="KiraPixel1")


def get_address(x, y):
    if x == 0 or y == 0:
        return None
    location = geolocator.reverse((x, y), exactly_one=True)
    return location
