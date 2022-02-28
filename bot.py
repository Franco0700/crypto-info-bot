from email import message
from bs4 import BeautifulSoup
from Saved_Thread import SavedThread
import requests
import threading
from functools import partial
import sys
import os
import re
import json
import bisect
import yaml
from pprint import pformat
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext, CommandHandler
from telegram import Update, Bot
import logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)
logger = logging.getLogger(__name__)


class TelegramBot:
    def coins_from_file(self, args):
        th = args[0]
        bot = args[1]
        with open('Coins.txt', "r") as fh:
            scrapTh = []
            results = {}
            for coin in fh.readlines():
                newCoin = coin.rstrip('\n\r')
                url = "https://coinmarketcap.com/es/currencies/" + newCoin + "/"
                x = threading.Thread(
                    target=self.search_price, args=(url, newCoin, results))
                scrapTh.append(x)
                x.start()
            for i in scrapTh:
                i.join()
            bot.send_message(th.owner, yaml.dump(results))

    def search_price(self, url, newCoin, results):
        req = requests.get(url)
        if req.status_code == 200:
            parsed = BeautifulSoup(req.text, "html.parser")
            priceTit = parsed.find(class_=re.compile("priceTitle"))
            price = priceTit.find(class_=re.compile("priceValue")).get_text()
            percentage = priceTit.find(style=re.compile(
                "font-size:14px;font-weight:600;padding:5px 10px")).get_text()
            table = parsed.find(class_=re.compile(
                "sc-16r8icm-0 fmPyWa")).findAll(scope=re.compile("row"))[2]
            if (priceTit.find(class_="icon-Caret-up")):
                percentage = "+" + percentage
            else:
                percentage = "-" + percentage
            data = {
                "Price": price,
                "Percentage": percentage,
                "Minimo en 24h/ Maximo en 24h": table.find_next_sibling("td").getText()}
            results[newCoin] = data
        else:
            results[newCoin] = "Crypto Not Found"

    def error_callback(self, update, context):
        logger.warning('Update "%s" caused error "%s"', update, context.error)

    def record_callback(self, update):
        mes = update.message
        message = ("\n" +
                   'name: ' +
                   str(mes.chat.first_name) +
                   " " +
                   str(mes.chat.last_name) +
                   '\n' +
                   'username: ' +
                   str(mes.chat.username) +
                   '\n' +
                   'chatID: ' +
                   str(mes.chat.id) +
                   '\n' +
                   'message: ' +
                   str(mes.text) +
                   '\n')
        logger.info(message)

    def coin_price(self, update, context):
        self.record_callback(update)
        th = []
        results = {}
        for coin in context.args:
            newCoin = coin.rstrip('\n\r')
            url = "https://coinmarketcap.com/es/currencies/" + newCoin + "/"
            x = threading.Thread(target=self.search_price,
                                 args=(url, newCoin, results))
            th.append(x)
            x.start()
        for i in th:
            i.join()
        update.message.reply_text(yaml.dump(results))

    def send_hello(self, args):
        th = args[0]
        bot = args[1]
        bot.send_message(th.owner, "Hola")

    def check_sch(self, func, args, th):
        x = threading.Timer(th.time, function=self.check_sch,
                            args=(func, args, th))
        index = bisect.bisect(self.chatScheduleId, th.owner) - 1
        if self.threads_running[index].mustContinue:
            func(args)
            x.start()
        else:
            x.cancel()
            self.threads_running.pop(index)
            self.chatScheduleId.pop(index)

    def set_schedule(self, func, update, context):
        self.record_callback(update)
        id = update.message.chat_id
        time = int(context.args[0])
        context.bot.send_message(
            update.message.chat_id,
            "Okay, send message in " +
            context.args[0] +
            " seconds")
        index = bisect.bisect(self.chatScheduleId, id)
        th = SavedThread(index, id, time)
        x = threading.Timer(time, function=self.check_sch,
                            args=(func, (th, context.bot), th))
        self.threads_running.insert(index, th)
        self.chatScheduleId.insert(index, id)
        x.start()

    def stop_schedule(self, update, context):
        self.record_callback(update)
        id = update.message.chat_id
        index = bisect.bisect(self.chatScheduleId, id)
        beforeElem = self.threads_running[index - 1]
        if (beforeElem.owner == id):
            beforeElem.mustContinue = False
        else:
            context.bot.send_message(id, "Not message scheduled for you")

    def start(self):
        ''' START '''
        # Commands received by the bot
        self.dp.add_handler(CommandHandler('coins', self.coin_price))
        self.dp.add_handler(CommandHandler(
            'sch', partial(self.set_schedule, self.send_hello)))
        self.dp.add_handler(CommandHandler('default', partial(
            self.set_schedule, self.coins_from_file)))
        self.dp.add_handler(CommandHandler('stop', self.stop_schedule))
        # self.dp.add_error_handler(self.error_callback)

        # Starting bot
        self.updater.start_polling()
        # Bot waiting messages
        self.updater.idle()

    def __init__(self):
        TOKEN = "TOKEN"
        print("Iniciando bot....")
        self.updater = Updater(TOKEN, use_context=True)
        self.dp = self.updater.dispatcher
        self.lowestIndex = 0
        self.threads_running = []
        self.chatScheduleId = []


if __name__ == '__main__':
    coinBot = TelegramBot()
    coinBot.start()

"""
def bot_send_text(bot_message):
    bot_token = "TOKEN"
    bot_chatID = "1934620415"
    for rs in bot_message:
        send_text = ('https://api.telegram.org/bot' +
                    bot_token +
                    '/sendMessage?chat_id=' +
                    bot_chatID +
                    '&parse_mode=Markdown&text=' +
                    '+' + rs + "\n" +
                   pformat(bot_message[rs]))

        response = requests.get(send_text)

    return response
"""
