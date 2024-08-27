from math import radians, sin, cos, sqrt, atan2


def calculate_distance(coord1, coord2):
    R = 6371.0
    lon1, lat1 = coord1  # Приводим к формату (широта, долгота)
    lon2, lat2 = coord2

    # Округление до одного знака после запятой
    lon1, lat1 = round(lon1, 1), round(lat1, 1)
    lon2, lat2 = round(lon2, 1), round(lat2, 1)

    lat1 = radians(lat1)
    lon1 = radians(lon1)
    lat2 = radians(lat2)
    lon2 = radians(lon2)

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    distance = R * c
    return distance
