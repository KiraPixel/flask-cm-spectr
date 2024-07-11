import csv
from datetime import datetime, timedelta, timezone
import time
import requests
import json


with open('config.json', 'r') as f:
    config = json.load(f)


token = ''


class CesarApi:
    def __init__(self):
        self.api_url = 'https://apicsp.csat.ru/api/v1/'
        self.token = ''
        self.set_token()

    def set_token(self):
        headers = {
            'accept': '*/*',
        }
        data = {
            'username': config['cesar_username'],
            'password': config['cesar_password'],
            'grant_type': 'password'
        }
        request = requests.post(self.api_url+'token', headers=headers, data=data)
        access_token = request.json()
        access_token = access_token['access_token']
        self.token = access_token

    def get_all_unit(self):
        headers = {
            'accept': '*/*',
            'Authorization': 'Bearer ' + self.token,
            'Content-Type': 'application/json'
        }

        request = requests.get(self.api_url+'units', headers=headers)
        return request.json()

    def get_unit_name(self, unitID):
        headers = {
            'accept': '*/*',
            'Authorization': 'Bearer ' + self.token,
            'Content-Type': 'application/json'
        }

        request = requests.get(self.api_url+'units/'+unitID, headers=headers)
        return request.json()

    def get_cars_info(self, unitID=[], toString=False, offline=False):
        headers = {
            'accept': '*/*',
            'Authorization': 'Bearer ' + self.token,
            'Content-Type': 'application/json'
        }
        data = {
            'unit_ids': unitID
        }
        request = requests.post(self.api_url + 'units/device-state', headers=headers, json=data)
        result_items = request.json()
        result_items = result_items['devices']
        current_unix_time = int(time.time())
        three_days_ago_unix = current_unix_time - 3 * 24 * 60 * 60
        if toString:
            res_list = []
            for item in result_items:
                cesar_id = item['unit_id']
                object_name = item['object_name']
                pin = item['pin']
                model = item['device_type']
                lmsg = item['receive_time']
                if lmsg is not None:
                    dt = datetime.strptime(lmsg, "%Y-%m-%dT%H:%M:%SZ")
                    moscow_tz = timezone(timedelta(hours=3))
                    moscow_time = dt.astimezone(moscow_tz)
                    lmsg = moscow_time.strftime("%d-%m-%Y %H:%M")

                if offline:
                    if lmsg is None:
                        final_str = f'{cesar_id};{object_name};{pin};{model};{lmsg}'
                        res_list.append(final_str)
                        continue
                    dt = datetime.strptime(lmsg, "%Y-%m-%dT%H:%M:%SZ")
                    unix_time = int(dt.timestamp())
                    if unix_time < three_days_ago_unix:
                        final_str = f'{cesar_id};{object_name};{pin};{model};{lmsg}'
                        res_list.append(final_str)
                        continue

                final_str = f'{cesar_id};{object_name};{pin};{model};{lmsg}'
                res_list.append(final_str)
            return res_list

        return request['devices']

# Cesar = CesarApi()
# #all_unit = Cesar.get_all_unit()
# Cesar.get_cars_info([375401])

# x =Cesar.get_cars_info(toString=True, offline=True)
# with open('cesar_car.txt', 'w', newline='', encoding='utf-8') as file_all:
#     writer = csv.DictWriter(file_all, fieldnames=['unitId', 'name'], delimiter=';')
#
#     # Записываем заголовки (имена полей)
#     writer.writeheader()
#
#     # Записываем строки данных
#     writer.writerows(all_unit)

# url = 'https://apicsp.csat.ru/api/v1/units'
# headers = {
#     'accept': '*/*',
#     'Authorization': f'Bearer {token}',
#     'Content-Type': 'application/json'
# }
#
# response = requests.get(url, headers=headers)
#
# data = response.json()
# print(data)