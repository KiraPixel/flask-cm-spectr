import time
from wialon import flags
from custom_api.wialon import WialonConnector
from geopy.geocoders import Nominatim
geolocator = Nominatim(user_agent="KiraPixel")


def search_all_items(offline=False, address=False, last_time_start_unix=None, last_time_end_unix=None, originals=False):
    wialon_api = WialonConnector.wialon_connector()

    # Параметры для поиска объектов
    params = {
        'spec': {
            'itemsType': 'avl_unit',
            'propName': 'sys_name',
            'propValueMask': '*',
            'sortType': 'sys_name'
        },
        'force': 1,
        'flags': 1 | 1024,
        'from': 0,
        'to': 0,
    }

    # Выполнение запроса на поиск объектов
    result = wialon_api.core_search_items(params)
    result_items = result['items']
    res_list = ['wialon_id;uNumber;wialon_id2(tech);last_time;last_pos_time;x_y poistion']

    if originals:
        return result_items

    if offline:
        current_time_unix = time.time()  # текущее время в формате Unix (секунды с начала эпохи)
        # Вычисляем временную метку для 3 дней назад
        three_days_ago_unix = current_time_unix - (
                    3 * 24 * 60 * 60)  # 3 дня в секундах (24 часа * 60 минут * 60 секунд)

    for item in result_items:
        wialon_id = item['id']
        nm = item['nm']
        uuid = item['id']
        lmsg = item['lmsg']
        final_str = ''

        if offline and lmsg is not None and lmsg['t'] > three_days_ago_unix:
            lmsg = WialonConnector.convert_to_moscow_time(lmsg['t'])  # конвертируем в московское время
            final_str = f'{nm}'
        elif address:
            if lmsg is not None:
                pos = item.get('pos', None)
                pos_x = ''
                pos_y = ''
                location = None
                last_time = WialonConnector.convert_to_moscow_time(lmsg['t'])
                if pos is not None:
                    pos_x = pos['x']
                    pos_y = pos['y']
                if pos_x == '' or pos_y == '':
                    location = ''
                else:
                    location = geolocator.reverse((pos_y, pos_x), exactly_one=True)
                print(location)
                final_str = f'{nm};{last_time};{location}'
        elif last_time_start_unix is not None or last_time_end_unix is not None:
            if lmsg is None:
                continue
            lmsg_conv = WialonConnector.convert_to_moscow_time(lmsg['t'])
            if last_time_start_unix is not None and last_time_end_unix is not None:
                if last_time_start_unix <= lmsg['t'] <= last_time_end_unix:
                    final_str = f'{nm}'
                else:
                    continue
            elif last_time_start_unix is not None:
                if lmsg['t'] >= last_time_start_unix:
                    final_str = f'{nm}'
                else:
                    continue
            elif last_time_end_unix is not None:
                if lmsg['t'] <= last_time_end_unix:
                    final_str = f'{nm}'
                else:
                    continue
        else:
            pos = item.get('pos', None)
            last_pos = ''
            pos_x = ''
            pos_y = ''
            if pos:
                last_pos = pos['t']
                last_pos = WialonConnector.convert_to_moscow_time(last_pos)
                pos_x = pos['x']
                pos_y = pos['y']

            if lmsg:
                last_time = lmsg['t']
                last_time = WialonConnector.convert_to_moscow_time(last_time)
            else:
                last_time = ''

            final_str = f'{wialon_id};{nm};{uuid};{last_time};{last_pos};{pos_y},{pos_x};'

        res_list.append(final_str)
    return res_list


def search_item(item):
    wialon_api = WialonConnector.wialon_connector()
    params = {
        'spec': {
            'itemsType': 'avl_unit',
            'propName': 'sys_name',
            'propValueMask': f'*{item}*',
            'sortType': 'sys_name'
        },
        "from": 0,
        "to": 0,
        'force': 0,
        'flags': 1 | 1024
    }

    result = wialon_api.core_search_items(params)
    if (len(result['items']) == 0):
        return None

    result_item = result['items'][0]

    Car = WialonConnector.Car()
    Car.id = result_item['id']
    Car.nm = result_item['nm']
    Car.uuid = result_item['id']
    Car.last_time_msg = result_item['lmsg']
    Car.last_pos_msg = result_item['pos']
    Car.convert_all()

    return Car


def test_search():
    wialon_api = WialonConnector.wialon_connector()
    params = {
        'spec': {
            'itemsType': 'avl_unit',
            'propName': 'sys_name',
            'propValueMask': f'*{"test"}*',
            'sortType': 'sys_name'
        },
        "from": 0,
        "to": 0,
        'force': 0,
        'flags': 1025 | flags.ITEM_UNIT_DATAFLAG_RESTRICTED
    }

    result = wialon_api.core_search_items(params)
    result_items = result['items']


# x = search_item('F 00823')
# x.refresh_address()
# print(x.address)

# all_car = search_all_items(address=True)

# test_search()


# with open('nm_values_all.txt', 'w', encoding='utf-8') as file_all:
#     for nm in all_car:
#         file_all.write(nm + '\n')
#
# with open('nm_values_offline.txt', 'w', encoding='utf-8') as file_offline:
#     for nm in offline_car:
#         file_offline.write(nm + '\n')
