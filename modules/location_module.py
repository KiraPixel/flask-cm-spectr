from geopy.geocoders import Nominatim

geolocator = Nominatim(user_agent="KiraPixel1")


def get_address(x, y):
    if x == 0 or y == 0:
        return None
    location = geolocator.reverse((x, y), exactly_one=True)
    return location


def get_address_decorator(coords=None):
    x, y = coords
    if x == 0 or y == 0 or coords is None:
        return ''

    location = geolocator.reverse((x, y), exactly_one=True)
    address = location.raw.get('address', {})
    print(address)

    # Попробуем получить нужные части адреса
    city = address.get('city') or address.get('town') or address.get('state', '') or address.get('county')
    road = address.get('road') or address.get('city_district', '') or address.get('municipality') or address.get('suburb') or address.get('house') or address.get('hamlet')
    house_number = address.get('house_number') or address.get('amenity') or address.get('village') or address.get(
        'neighbourhood', '') or address.get('municipality') or address.get('postcode')

    # Формируем сокращенный адрес
    short_address = f"{city}, {road}, {house_number}".strip(', ')
    if short_address == 'Химки, Коммунальный проезд, 141410':
        short_address = "Химки, Коммунальный проезд, 2"

    return short_address
