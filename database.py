from redis import Redis
from os import system, path
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
        except ValueError:
            return value


def get_parameter(key):
    if key in parameters:
        my_db = singleton()
        data = my_db.get(prefix + key)
        if data is None:
            data = get_default(key)
            my_db.set(prefix + key, str(data))
        return check_datatype(data)
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

def set_parameters_to_cache():
    for key in parameters:
        cache_parameters[key] = get_parameter(key)