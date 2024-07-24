import time
import datetime


def now_unix_time():
    return time.time()


def online_check(unix_time):
    try:
        current_time = datetime.datetime.now().timestamp()
        time_difference = current_time - unix_time
        if time_difference <= 300:  # 5 minutes in seconds
            return "online"
        else:
            return "offline"
    except:
        return "unknown"


def get_time_minus_three_days():
    current_time = time.time()
    three_days_ago = current_time - 3 * 24 * 60 * 60
    return int(three_days_ago)


def to_unix_time(time_str):
    try:
        return time.mktime(datetime.datetime.strptime(time_str, '%Y-%m-%dT%H:%M').timetuple())
    except ValueError:
        return None


def tz_to_moscow_time(z_time):
    try:
        dt = datetime.datetime.strptime(z_time, "%Y-%m-%dT%H:%M:%SZ")
        moscow_tz = datetime.timezone(datetime.timedelta(hours=3))
        moscow_time = dt.astimezone(moscow_tz)
        return moscow_time.strftime("%d-%m-%Y %H:%M")
    except:
        return 0


def unix_to_moscow_time(timestamp):
    try:
        dt_utc = datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc)

        moscow_timezone = datetime.timezone(datetime.timedelta(hours=3))
        dt_msk = dt_utc.astimezone(moscow_timezone)

        formatted_time = dt_msk.strftime('%d-%m-%Y %H:%M:%S')
        return formatted_time
    except:
        return 0