import time
import datetime
import pytz

moscow_tz = pytz.timezone('Europe/Moscow')


def now_unix_time():
    return time.time()


def five_minutes_ago_unix():
    return int((datetime.datetime.now() - datetime.timedelta(minutes=5)).timestamp())


def one_hours_ago_unix():
    return int((datetime.datetime.now() - datetime.timedelta(hours=1)).timestamp())


def forty_eight_hours_ago_unix():
    return int((datetime.datetime.now() - datetime.timedelta(hours=48)).timestamp())


def online_check(unix_time):
    try:
        current_time = datetime.datetime.now().timestamp()
        time_difference = current_time - unix_time
        if time_difference <= 300:  # 5 minutes in seconds
            return "Online"
        else:
            return "Offline"
    except:
        return "Unknown"


def get_time_minus_three_days():
    current_time = time.time()
    three_days_ago = current_time - 3 * 24 * 60 * 60
    return int(three_days_ago)


def to_unix_time(time_str):
    try:
        naive_time = datetime.datetime.strptime(time_str, '%Y-%m-%dT%H:%M')
        localized_time = moscow_tz.localize(naive_time)
        return int(localized_time.timestamp())
    except ValueError:
        return None


def tz_to_moscow_time(z_time):
    try:
        dt = datetime.datetime.strptime(z_time, "%Y-%m-%dT%H:%M:%SZ")
        moscow_tzz = datetime.timezone(datetime.timedelta(hours=3))
        moscow_time = dt.astimezone(moscow_tzz)
        return moscow_time.strftime("%d-%m-%Y %H:%M")
    except:
        return 0


def unix_to_moscow_time(timestamp):
    try:
        if timestamp == 0:
            return ''
        dt_utc = datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc)

        moscow_timezone = datetime.timezone(datetime.timedelta(hours=3))
        dt_msk = dt_utc.astimezone(moscow_timezone)

        formatted_time = dt_msk.strftime('%d-%m-%Y %H:%M:%S')
        return formatted_time
    except:
        return 0
