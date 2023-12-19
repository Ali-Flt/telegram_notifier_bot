import telebot
import os
from datetime import datetime, timedelta
import time
import sys
import logging
import re
from telebot import types, logger
import database
import config
from threading import Thread

os.environ['TZ'] = config.timezone
time.tzset()
bot = telebot.TeleBot(config.TOKEN)
logger.setLevel(logging.INFO)
hour = 3600

@bot.message_handler(func=lambda message: message.from_user.username == config.user_name, commands=['reset'])
def reset_command(message):
    bot.send_message(
        message.chat.id,
        'Resetting scheduling!'
        )
    database.reset_parameters()
    database.set_parameters_to_cache()
    markup = types.ForceReply(selective=False, input_field_placeholder='YYYY-MM-DD HH:MM')
    bot.send_message(message.chat.id, "What is the starting time and date for scheduling?", reply_markup=markup)

@bot.message_handler(func=lambda message: message.from_user.username == config.user_name, commands=['start'])
def start_command(message):
    bot.send_message(
        message.chat.id,
        'Greetings! I am a reminder bot for your DS-160 form update! \n' +
        'Please input the time of the first notification.'
        )
    
    markup = types.ForceReply(selective=False, input_field_placeholder='YYYY-MM-DD HH:MM')
    bot.send_message(message.chat.id, "What is the starting time and date for scheduling?", reply_markup=markup)
    
@bot.message_handler(func=lambda message: message.from_user.username == config.user_name and database.get_cache_parameter('next_schedule') is None and re.search("(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2})", message.text))
def get_start_date(message):
    database.set_parameter('next_schedule', message.text)
    database.set_parameters_to_cache(['next_schedule'])
    markup = types.ForceReply(selective=False, input_field_placeholder='e.g.: 21')
    bot.send_message(message.chat.id, "How often should I notify you (in days)?:", reply_markup=markup)
        
@bot.message_handler(func=lambda message: message.from_user.username == config.user_name and database.get_cache_parameter('next_schedule') is not None and database.get_cache_parameter('step') is None and message.text.isnumeric())
def get_step(message):
    database.set_parameter('step', message.text)
    database.set_parameter('message_id', message.chat.id)
    database.set_parameters_to_cache(['step', 'message_id'])
    bot.send_message(message.chat.id, f'Scheduling started! Next Schedule: {database.get_cache_parameter('next_schedule')}')
    start_schedule(message.chat.id)
    
@bot.callback_query_handler(func=lambda call: True)
def iq_callback(query):
    data = query.data
    if data.startswith('I did it'):
        update_next_schedule(query)
    elif data.startswith('Snooze'):
        send_snooze_message(query)
       

@bot.message_handler(func=lambda message: message.from_user.username == config.user_name, commands=['help'])
def help_command(message):
   keyboard = telebot.types.InlineKeyboardMarkup()
   bot.send_message(
       message.chat.id,
       'press /start to start scheduling the notifications!\n' +
       'press /status to see the scheduling status.\n' +
       'press /reset to reset the scheduler.',
       reply_markup=keyboard
   )

@bot.message_handler(func=lambda message: message.from_user.username == config.user_name, commands=['status'])
def status_command(message):
   keyboard = telebot.types.InlineKeyboardMarkup()
   bot.send_message(
       message.chat.id,
       f"Next Schedule: {database.get_cache_parameter('next_schedule')}\n"\
       f"Schedule Interval: {database.get_cache_parameter('step')}",
       reply_markup=keyboard
   )

def start_schedule(id):
    schedule_finished = False
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.row(
        telebot.types.InlineKeyboardButton('I did it', callback_data='I did it'),
        telebot.types.InlineKeyboardButton('Snooze', callback_data='Snooze')
        )
    while True:
        if database.get_cache_parameter('next_schedule') is not None:
            while datetime.now() < database.get_cache_parameter('next_schedule'):
                time.sleep(config.time_check_step_hours*hour)
                if database.get_cache_parameter('next_schedule') is None:
                    schedule_finished = True
                    break
        else: 
            schedule_finished = True
        if schedule_finished:
            break
        database.set_parameter('schedule_updated', False)
        database.set_parameter('snoozed', False)
        database.set_parameters_to_cache(['schedule_updated', 'snoozed'])
        bot.send_message(id, config.notification_message, reply_markup=keyboard)
        time.sleep(snooze_hours*hour)
        
def update_next_schedule(query):
    if not database.get_cache_parameter('schedule_updated'):
        database.set_parameter('next_schedule', database.get_cache_parameter('next_schedule') + database.get_cache_parameter('step'))
        database.set_parameter('schedule_updated', True)
        database.set_parameters_to_cache(['next_schedule', 'schedule_updated'])
        bot.send_message(query.message.chat.id, f"Updated next schedule for {database.get_cache_parameter('next_schedule')}.")
    else:
        bot.send_message(query.message.chat.id, f"Already updated schedule for {database.get_cache_parameter('next_schedule')}.")
    
def send_snooze_message(query):
    if not database.get_cache_parameter('snoozed') and not database.get_cache_parameter('schedule_updated'):
        database.set_parameter('snoozed', True)
        database.set_parameters_to_cache(['snoozed'])
        bot.send_message(query.message.chat.id, f'Snoozed for {config.snooze_hours} hours.')
    elif not database.get_cache_parameter('schedule_updated'):
        bot.send_message(query.message.chat.id, 'Already snoozed.')
    else:
        bot.send_message(query.message.chat.id, f"Already updated schedule for {database.get_cache_parameter('next_schedule')}.")


def main_loop():
    database.set_parameters_to_cache()
    if database.get_cache_parameter('next_schedule') and database.get_cache_parameter('step'):
        bot.send_message(database.get_cache_parameter('message_id'), f"Bot Started! Scheduling for {database.get_cache_parameter('next_schedule')}.")
        thread = Thread(target=start_schedule, args=(database.get_cache_parameter('message_id'),))
        thread.start()
    else:
        database.reset_parameters()
    database.print_cache_parameters()
    bot.infinity_polling()
    while 1:
        time.sleep(3)


if __name__ == '__main__':
    try:
        main_loop()
    except KeyboardInterrupt:
        print('\nExiting by user request.\n')
        sys.exit(0)
