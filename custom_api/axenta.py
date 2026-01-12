import time
import requests
from requests.exceptions import RequestException
from threading import Lock
from datetime import datetime
from typing import Optional, Dict, List


class AxentaApi:
    def __init__(self, login: str, password: str, api_url: str = "https://axenta.cloud/api/", session_timeout: int = 600):
        self.login = login
        self.password = password
        self.api_url = api_url.rstrip("/") + "/"
        self.session_timeout = session_timeout

        self.token: Optional[str] = None
        self.token_expiry: float = 0
        self.lock = Lock()

    def _ensure_valid_token(self) -> Optional[str]:
        with self.lock:
            if self.token is None or time.time() >= self.token_expiry:
                return self._login()
            return self.token

    def _login(self) -> Optional[str]:
        url = self.api_url + "auth/login/"
        payload = {"username": self.login, "password": self.password}
        try:
            resp = requests.post(url, data=payload, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            if "token" in data:
                self.token = data["token"]
                self.token_expiry = time.time() + self.session_timeout
                return self.token
        except RequestException:
            pass
        return None

    def _request(self, method: str, endpoint: str, json=None, params=None, data=None, max_retries=3) -> Optional[Dict]:
        url = self.api_url + endpoint.lstrip("/")
        token = self._ensure_valid_token()
        if not token:
            return None

        headers = {"Authorization": f"Token {token}", "Content-Type": "application/json"}

        for attempt in range(max_retries):
            try:
                resp = requests.request(
                    method=method.upper(),
                    url=url,
                    headers=headers,
                    json=json,
                    params=params,
                    data=data,
                    timeout=20
                )
                if resp.status_code in (200, 201, 204):
                    return resp.json() if resp.content else {}
                if resp.status_code == 401:
                    with self.lock:
                        self.token = None
                elif resp.status_code >= 500 and attempt < max_retries - 1:
                    time.sleep(3)
                    continue
                resp.raise_for_status()
            except RequestException:
                if attempt == max_retries - 1:
                    return None
                time.sleep(2)
        return None

    @staticmethod
    def _unix_to_iso(ts: int) -> str:
        return datetime.utcfromtimestamp(ts).strftime('%Y-%m-%dT%H:%M:%SZ')

    def get_object_details(self, object_id: str) -> Optional[Dict]:
        return self._request("GET", f"objects/{object_id}/")

    def get_sensors(self, object_id: str) -> Optional[Dict]:
        return self._request("GET", f"objects/{object_id}/sensors/")

    def get_commands(self, object_id: str) -> Optional[List[Dict]]:
        return self._request("GET", f"objects/{object_id}/commands/")

    def send_command(self, object_id: str, params: str) -> bool:
        return self._request("POST", f"objects/{object_id}/send_command/", json={"params": params}) is not None

    def build_track(self, object_id: str, start_ts: int, end_ts: int, detectTrips: bool = True, **options) -> Optional[Dict]:
        payload = {
            "objectId": int(object_id),
            "startDate": self._unix_to_iso(start_ts),
            "endDate": self._unix_to_iso(end_ts),
            "trackType": options.get("trackType", "single"),
            "sensorId": options.get("sensorId", 0),
            "detectTrips": detectTrips,
            "withStops": options.get("withStops", False),
            "withParkings": options.get("withParkings", False),
            "withRefuels": options.get("withRefuels", False),
            "withPlums": options.get("withPlums", False),
            "withOverSpeed": options.get("withOverSpeed", False),
        }
        return self._request("POST", "tracks/create/", json=payload)

    def reverse_geocode(self, coordinates: List[Dict[str, float]]) -> Optional[Dict]:
        if not coordinates:
            return {}
        return self._request("POST", "geocoding/reverse/", json={"coordinates": coordinates}) or {}

    def get_messages_with_sensors(
            self,
            object_id: int,
            start_ts: int,
            end_ts: int,
            sort: str = "desc",
            messages_param: str = "sensors"
    ) -> Optional[List[Dict]]:
        payload = {
            "objectId": int(object_id),
            "startDate": self._unix_to_iso(start_ts),
            "endDate": self._unix_to_iso(end_ts),
            "messagesType": "with_data",
            "messagesParam": messages_param,
            "sort": sort,
            #"sortField": "t",
            #"filterServiceMessages": False
        }

        raw = self._request("POST", "messages/get", json=payload)
        if not raw or not isinstance(raw, list):
            return None

        result = []
        for msg in raw:
            sensors = msg.get("sensors")
            if sensors:
                result.append({"t": msg.get("t"), "sensors": sensors})
        return result if result else None

    def get_sensors_by_period(
            self,
            object_id: int,
            start_ts: int,
            end_ts: int,
            sensor_ids: List[int]
    ) -> Optional[Dict]:
        payload = {
            "objectId": int(object_id),
            "startDatetime": self._unix_to_iso(start_ts),
            "endDatetime": self._unix_to_iso(end_ts),
            "messageFields": sensor_ids,
            "messagesType": "sensors"
        }
        return self._request("POST", "messages/chart", json=payload)