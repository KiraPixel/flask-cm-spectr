import time
import datetime


def get_time_minus_three_days():
    current_time = time.time()
    three_days_ago = current_time - 3 * 24 * 60 * 60
    return int(three_days_ago)


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
