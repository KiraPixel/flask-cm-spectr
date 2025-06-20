import json
import os
import requests


token = os.getenv('WIALON_TOKEN', 'default_token')
api_url = os.getenv('WIALON_HOST', 'default_host')


def get_wialon_sid():
    params = {
        'token': token
    }
    response = requests.get(api_url, params={
        'svc': 'token/login',
        'params': json.dumps(params)
    }, verify=False)

    if response.status_code == 200:
        result = response.json()
        if 'eid' in result:
            return result['eid']
        else:
            print(f"Error: {result}")
            return None
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None


def search_all_items():
    params = {
        'spec': {
            'itemsType': 'avl_unit',
            'propName': 'sys_name',
            'propValueMask': '*',
            'sortType': 'sys_name'
        },
        'force': 1,
        'flags': 1 | 256 | 1024 | 4096 | 524288,
        'from': 0,
        'to': 0,
    }
    response = requests.get(api_url, params={
        'svc': 'core/search_items',
        'params': json.dumps(params),
        'sid': get_wialon_sid()
    }, verify=False)

    if response.status_code == 200:
        final_response = response.json()
        final_response = final_response['items']

        # with open('search_items_response.json', 'w', encoding='utf-8') as json_file:
        #     json.dump(final_response, json_file, ensure_ascii=False, indent=4)

        return final_response
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None


def exec_cmd(unit_id, command_name):
    params = {
        'itemId': unit_id,
        'commandName': f"{command_name}",
        'linkType': '',
        'param': '',
        'timeout': 5,
        'flags': 0
    }
    response = requests.get(api_url, params={
        'svc': 'unit/exec_cmd',
        'params': json.dumps(params),
        'sid': get_wialon_sid()
    }, verify=False)

    if response.status_code == 200:
        final_response = response.json()
        return final_response
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None


def get_sensors(unit_id):
    params = {
        'unitId': unit_id,
        'sensors': '',
    }
    response = requests.get(api_url, params={
        'svc': 'unit/calc_sensors',
        'params': json.dumps(params),
        'sid': get_wialon_sid()
    }, verify=False)

    if response.status_code == 200:
        final_response = response.json()
        return final_response
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None


def get_message_for_interval(unit_id, time_from, time_to):
    sid=get_wialon_sid()

    # Создаем слой
    params = {
        'layerName': 'cm_messages',
        'itemId': unit_id,
        'timeFrom': time_from,
        'timeTo': time_to,
        'tripDetector': 0,
        'trackColor': 'cc0000ff',
        'trackWidth': 0,
        'arrows': 0,
        'points': 0,
        'pointColor': 'cc0000ff',
        'annotations': 0
    }
    response = requests.get(api_url, params={
        'svc': 'render/create_messages_layer',
        'params': json.dumps(params),
        'sid': sid
    }, verify=True)

    if not response.status_code == 200:
        print(f"Error: {response.status_code} - {response.text}")
        return None

    # получаем сообщение с сенсорами из слоя
    params = {
        'unitId': unit_id,
        'indexFrom': 0,
        'indexTo': 1000000,
        'layerName': "cm_messages",
        'calcSensors': 'true'
    }
    response = requests.get(api_url, params={
        'svc': 'render/get_messages',
        'params': json.dumps(params),
        'sid': sid,
    }, verify=True)

    if response.status_code == 200:
        final_response = response.json()
        return final_response
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None