from wialon import Wialon
from app import config

token = config.WIALON_TOKEN


def wialon_connector():
    wialon_api = Wialon()
    result = wialon_api.token_login(token=token)
    wialon_api.sid = result['eid']
    return wialon_api


def search_all_items():
    wialon_api = wialon_connector()

    params = {
        'spec': {
            'itemsType': 'avl_unit',
            'propName': 'sys_name',
            'propValueMask': '*',
            'sortType': 'sys_name'
        },
        'force': 1,
        'flags': 1 | 256 | 1024,
        'from': 0,
        'to': 0,
    }

    result = wialon_api.core_search_items(params)

    return result['items']