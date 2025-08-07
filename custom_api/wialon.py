import json
import time
import warnings
import requests
from requests.exceptions import RequestException
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from threading import Lock

warnings.filterwarnings('ignore', category=InsecureRequestWarning)

class WialonAPI:
    def __init__(self, token, api_url, session_timeout=300):
        self.token = token
        self.api_url = api_url
        self.session_timeout = session_timeout
        self.sessions = {}
        self.lock = Lock()

    def _get_session(self, username):
        with self.lock:
            return self.sessions.setdefault(username, {'sid': None, 'last_activity': 0})

    def _clear_session(self, username):
        with self.lock:
            self.sessions.pop(username, None)

    def _get_wialon_sid(self, username):
        session = self._get_session(username)
        try:
            response = requests.get(self.api_url, params={
                'svc': 'token/login',
                'params': json.dumps({'token': self.token})
            }, verify=False, timeout=10)
            response.raise_for_status()
            result = response.json()
            if 'eid' in result:
                session['sid'] = result['eid']
                session['last_activity'] = time.time()
                return session['sid']
        except (RequestException, ValueError):
            return None
        return None

    def _is_session_valid(self, username):
        session = self._get_session(username)
        return session['sid'] and (time.time() - session['last_activity']) < self.session_timeout

    def _ensure_valid_sid(self, username):
        if not self._is_session_valid(username):
            return self._get_wialon_sid(username)
        return self._get_session(username)['sid']

    def fetch_sensor_data(self, username, unit_id, max_retries=4, retry_delay=10):
        for attempt in range(max_retries):
            sid = self._ensure_valid_sid(username)
            if not sid:
                return None
            try:
                response = requests.get(self.api_url, params={
                    'svc': 'unit/calc_last_message',
                    'params': json.dumps({'unitId': unit_id, 'sensors': ''}),
                    'sid': sid
                }, verify=False, timeout=10)
                response.raise_for_status()
                result = response.json()
                if any(value < -1 for value in result.values()):
                    time.sleep(retry_delay)
                    continue
                self._get_session(username)['last_activity'] = time.time()
                return result
            except (RequestException, ValueError):
                time.sleep(retry_delay)
        return None

    def execute_command(self, username, unit_id, command_name, link_type='', param='', timeout=5, flags=0):
        sid = self._ensure_valid_sid(username)
        if not sid:
            return {'error': 'Failed to get SID'}, 500

        try:
            response = requests.get(self.api_url, params={
                'svc': 'unit/exec_cmd',
                'params': json.dumps({
                    'itemId': unit_id,
                    'commandName': command_name,
                    'linkType': link_type,
                    'param': param,
                    'timeout': timeout,
                    'flags': flags
                }),
                'sid': sid
            }, verify=False, timeout=10)
            self._get_session(username)['last_activity'] = time.time()
            return response.json(), response.status_code
        except RequestException as e:
            return {'error': str(e)}, 500

    def get_unit_messages(self, username, unit_id, time_from, time_to, max_retries=4, retry_delay=10):
        for attempt in range(max_retries):
            sid = self._ensure_valid_sid(username)
            if not sid:
                return None

            try:
                layer_params = {
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
                response = requests.get(self.api_url, params={
                    'svc': 'render/create_messages_layer',
                    'params': json.dumps(layer_params),
                    'sid': sid
                }, verify=False, timeout=10)
                response.raise_for_status()

                messages_params = {
                    'unitId': unit_id,
                    'indexFrom': 0,
                    'indexTo': 1000000,
                    'layerName': 'cm_messages',
                    'calcSensors': 'true'
                }
                response = requests.get(self.api_url, params={
                    'svc': 'render/get_messages',
                    'params': json.dumps(messages_params),
                    'sid': sid
                }, verify=False, timeout=10)
                response.raise_for_status()
                self._get_session(username)['last_activity'] = time.time()
                return response.json()
            except (RequestException, ValueError):
                time.sleep(retry_delay)
        return None

    def get_unit_sensor_messages(self, username, unit_id, time_from, time_to, max_retries=4, retry_delay=10):
        messages = self.get_unit_messages(username, unit_id, time_from, time_to, max_retries, retry_delay)
        if not messages:
            return None

        try:
            return [{'message_time': msg.get('t', 0), 'sensors': msg.get('sensors', '')} for msg in messages]
        except Exception:
            return None