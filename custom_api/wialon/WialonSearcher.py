import time
from wialon import flags
from custom_api.wialon import WialonConnector


def search_all_items(offline=False, site=False):
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
    res_list = []

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

        if offline and lmsg is not None and lmsg['t'] > three_days_ago_unix:
            lmsg = WialonConnector.convert_to_moscow_time(lmsg['t'])  # конвертируем в московское время
            final_str = f'{nm};{uuid};{lmsg};'
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

# all_car = search_all_items()

# test_search()


# with open('nm_values_all.txt', 'w', encoding='utf-8') as file_all:
#     for nm in all_car:
#         file_all.write(nm + '\n')
#
# with open('nm_values_offline.txt', 'w', encoding='utf-8') as file_offline:
#     for nm in offline_car:
#         file_offline.write(nm + '\n')
