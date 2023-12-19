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


os.environ['TZ'] = config.timezone
time.tzset()
bot = telebot.TeleBot(config.TOKEN)
logger.setLevel(logging.INFO)
hour = 3600

curr_year = datetime.now().year

@bot.message_handler(func=lambda message: message.from_user.username == config.user_name, commands=['start'])
def start_command(message):
    bot.send_message(
        message.chat.id,
        'Greetings! I am a reminder bot for your DS-160 form update! \n' +
        'Please input the time of the first notification.'
        )
    
    markup = types.ForceReply(selective=False, input_field_placeholder='YYYY-MM-DD HH:MM')
    bot.send_message(message.chat.id, "What is the starting time and date for scheduling?", reply_markup=markup)
    
@bot.message_handler(func=lambda message: message.from_user.username == config.user_name and next_schedule is None and re.search("(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2})", message.text))
def get_start_date(message):
    database.set_parameter('next_schedule', datetime.strptime(message.text, "%Y-%m-%d %H:%M"))
    markup = types.ForceReply(selective=False, input_field_placeholder='e.g.: 21')
    bot.send_message(message.chat.id, "How often should I notify you (in days)?:", reply_markup=markup)
        
@bot.message_handler(func=lambda message: message.from_user.username == config.user_name and next_schedule is not None and step is None and message.text.isnumeric())
def get_step(message):
    database.set_parameter('step', timedelta(days=int(message.text)))
    database.set_parameter('message_id', message.chat.id)
    bot.send_message(message.chat.id, f'Scheduling started! Next Schedule: {database.get_cache_parameter('next_schedule')}')
    start_schedule(message.chat.id)

def start_schedule(id):
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.row(
        telebot.types.InlineKeyboardButton('I did it', callback_data='I did it'),
        telebot.types.InlineKeyboardButton('Snooze', callback_data='Snooze')
        )
    while True:
        while datetime.now() < next_schedule:
            time.sleep(config.time_check_step_hours*hour)
        database.set_parameter('schedule_updated', False)
        database.set_parameter('snoozed', False)
        bot.send_message(id, config.notification_message, reply_markup=keyboard)
        time.sleep(config.snooze_hours*hour)
        
def update_next_schedule(query):
    if not database.get_cache_parameter('schedule_updated'):
        database.set_parameter('next_schedule', database.get_cache_parameter('next_schedule') + database.get_cache_parameter('step'))
        database.set_parameter('schedule_updated' True)
        database.set_parameter('snoozed' True)
        bot.send_message(query.message.chat.id, f'Updated next schedule for {next_schedule}.')
    
def send_snooze_message(query):
    if not snoozed:
        bot.send_message(query.message.chat.id, f'Snoozed for {config.snooze_hours} hours.')
        database.set_parameter('snoozed' True)
    
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
       'press /start to start scheduling the notifications!',
       reply_markup=keyboard
   )

   
def main_loop():
    database.set_parameters_to_cache()
    if database.get_cache_parameter('next_schedule') and database.get_cache_parameter('step'):
        start_schedule(database.get_cache_parameter('message_id'))

    bot.infinity_polling()
    while 1:
        time.sleep(3)


if __name__ == '__main__':
    try:
        main_loop()
    except KeyboardInterrupt:
        print('\nExiting by user request.\n')
        sys.exit(0)
