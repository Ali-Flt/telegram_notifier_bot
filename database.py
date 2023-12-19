from redis import Redis
from os import system, path
from datetime import datetime, timedelta
from random import randint
import config

parameters = ['next_schedule', 'step', 'schedule_updated', 'snoozed', 'message_id']
notifier_db = None
prefix = 'notifier_'
cache_parameters = {}

def singleton():
    global notifier_db
    if notifier_db is None:
        notifier_db = Redis(host='redis_db',
            port=6379)
    return notifier_db


def get_default(key):
    if key == 'snoozed':
        return False
    elif key == 'schedule_updated':
        return False
    return None

def check_datatype(value):
    if isinstance(value, bytes):
        value = value.decode('UTF-8')
    if value == 'False':
        return False
    elif value == 'True':
        return True
    elif value == 'None':
        return None
    else:
        try:
            return int(value)
        except (ValueError, TypeError):
            return value


def get_parameter(key):
    if key in parameters:
        my_db = singleton()
        data = my_db.get(prefix + key)
        if data is None:
            data = get_default(key)
            my_db.set(prefix + key, str(data))
        data = check_datatype(data)
        if data is None:
            return data
        if key == 'next_schedule':
            try:
                return datetime.strptime(data, "%Y-%m-%d %H:%M")
            except ValueError:
                data = get_default(key)
                my_db.set(prefix + key, str(data))
        elif key == 'step':
            try:
                return timedelta(days=data)
            except ValueError:
                data = get_default(key)
                my_db.set(prefix + key, str(data))
        return data
    else:
        return None


def set_parameter(key, value):
    if key in parameters:
        singleton().set(prefix + key, str(value))
        return value
    else:
        return None


def get_cache_parameter(key):
    if key in parameters:
        return cache_parameters[key]
    else:
        return None

def set_parameters_to_cache(keys=None):
    if keys is None:
        keys = parameters
    for key in keys:
        cache_parameters[key] = get_parameter(key)