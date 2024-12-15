from geopy.geocoders import Nominatim

geolocator = Nominatim(user_agent="KiraPixel1")


def get_address(x, y):
    if x == 0 or y == 0:
        return None
    location = geolocator.reverse((x, y), exactly_one=True)
    print(location)
    return location


def get_address_decorator(coords=None):
    x, y = coords
    if x == 0 or y == 0 or coords is None:
        return ''

    location = geolocator.reverse((x, y), exactly_one=True)
    if location is None:
        return 'Ошибка определения'
    address = location.raw.get('address', {})
    #print(address)
    # Попробуем получить нужные части адреса
    city = address.get('city') or address.get('state') or address.get('town') or address.get('state', '') or address.get('county')

    road = address.get('road') or address.get('city_district', '') or address.get('county') or address.get(
        'municipality') or address.get('suburb') or address.get('house') or address.get('industrial') or address.get(
        'hamlet') or address.get('neighbourhood') or address.get('town')

    house_number = address.get('house_number') or address.get('amenity') or address.get('village') or address.get('neighbourhood') or address.get(
        'municipality') or address.get('postcode') or address.get("quarter") or address.get('road') or address.get("region")

    # Формируем сокращенный адрес
    short_address = f"{city}, {road}, {house_number}".strip(', ')
    if short_address == 'Химки, Коммунальный проезд, 141410':
        short_address = "Химки, Коммунальный проезд, 2"
    return short_address
