import bisect
import getpass
import json
import logging
import os
from pprint import pformat
import re
import requests
import sys
import threading

from bs4 import BeautifulSoup
import ccxt
import encrypted
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext, CommandHandler
from telegram import Update, Bot, constants
import yaml

from saved_thread import SavedThread
from search_info import *
from constants import HELP_MESSAGE

if not os.path.isdir("./logging"):
    os.mkdir("./logging")
logging.basicConfig(
    filename="./logging/logs.txt",
    filemode='a+',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler(sys.stdout))


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
                    target=search_price_market, args=(url, newCoin, results))
                scrapTh.append(x)
                x.start()
            for i in scrapTh:
                i.join()
            bot.send_message(th.owner, yaml.dump(
                results), constants.PARSEMODE_HTML)

    def error_callback(self, update, context):
        mes = f"Update {update} caused error {context.error}"
        logger.warning(mes)
        self.send_help(update, context)
        if self.actRemote:
            context.bot.send_message(self.owner, mes)

    def record_callback(self, update, bot):
        mes = update.message.chat
        text = str(update.message.text)
        message = ('\n' +
                   'name: ' +
                   str(mes.first_name) +
                   " " +
                   str(mes.last_name) +
                   '\n' +
                   'username: ' +
                   str(mes.username) +
                   '\n' +
                   'chatID: ' +
                   str(mes.id) +
                   '\n' +
                   'message: ' +
                   text +
                   '\n')
        logger.info(message)
        if self.actRemote:
            bot.send_message(self.owner, message)

    def binance_price(self, update, context):
        self.record_callback(update, context.bot)
        results = {}
        binance = ccxt.binance()
        for coin in context.args:
            coinInfo = binance.fetchTicker(coin)
            data = {
                "Price": "$" + str(coinInfo['bid']),
                "Minimo en 24h/ Maximo en 24h": str(coinInfo['high']) +
                                                "/" + str(coinInfo['low'])
            }
            results['<b>' + coin + '</b>'] = data
        update.message.reply_text(yaml.dump(results), constants.PARSEMODE_HTML)

    def coin_price(self, update, context):
        self.record_callback(update, context.bot)
        th = []
        results = {}
        for coin in context.args:
            newCoin = coin.rstrip('\n\r')
            url = "https://coinmarketcap.com/es/currencies/" + newCoin + "/"
            x = threading.Thread(target=search_price_market,
                                 args=(url, newCoin, results))
            th.append(x)
            x.start()
        for i in th:
            i.join()
        update.message.reply_text(yaml.dump(results), constants.PARSEMODE_HTML)

    def send_hello(self, args):
        th = args[0]
        bot = args[1]
        bot.send_message(th.owner, "Hola")

    def check_sch(self, func, args, th):
        x = threading.Timer(th.time, function=self.check_sch,
                            args=(func, args, th))
        i = 1
        index = bisect.bisect(self.chatScheduleId, th.owner)
        elem = self.threads_running[index - i]
        while (elem.owner == th.owner
                and elem.index != th.index
                and i <= index):
            i += 1
            elem = self.threads_running[index - i]
        if (i <= index and elem.owner == th.owner):
            if elem.mustContinue:
                func(args)
                x.start()
            else:
                x.cancel()
                self.threads_running.pop(index - i)
                self.chatScheduleId.pop(index - i)
        else:
            logger.warning("Something went wrong")

    def set_schedule_dec(self, func):
        def set_schedule(update, context):
            self.record_callback(update, context.bot)
            eventId = update.message.chat_id
            time = int(context.args[0])
            index = bisect.bisect(self.chatScheduleId, eventId)
            th = SavedThread(index, eventId, time)
            context.bot.send_message(
                update.message.chat_id,
                "Okay, send message in " +
                context.args[0] +
                " seconds." +
                "This is your schedule id for this event " +
                str(index))
            x = threading.Timer(time, function=self.check_sch,
                                args=(func, (th, context.bot), th))
            self.threads_running.insert(index, th)
            self.chatScheduleId.insert(index, eventId)
            func((th, context.bot))
            x.start()
        return set_schedule

    def stop_schedule(self, update, context):
        self.record_callback(update, context.bot)
        eventId = update.message.chat_id
        index = bisect.bisect(self.chatScheduleId, eventId)
        ownerSchId = int(context.args[0])
        i = 1
        notFinded = True
        beforeElem = self.threads_running[index - i]
        while (beforeElem.owner == eventId
                and beforeElem.index != ownerSchId
                and i <= index):
            i += 1
            beforeElem = self.threads_running[index - i]
        if (i <= index and beforeElem.owner == eventId):
            beforeElem.mustContinue = False
        else:
            context.bot.send_message(
                eventId, "Not message scheduled for you with that schedule id")

    def coins_file(self, update, context):
        self.record_callback(update, context.bot)
        id = update.message.chat_id
        bot = context.bot
        th = SavedThread(1, id, 0)
        self.coins_from_file((th, bot))

    def switch_remote(self, update, context):
        if (update.message.chat.id == self.owner):
            self.actRemote = not self.actRemote
            update.message.reply_text(f"Remote logging setted to {self.actRemote}")
        else:
            self.record_callback(update, context.bot)
            update.message.reply_text("You can't perform this action")

    def send_help(self, update, context):
        self.record_callback(update, context.bot)
        update.message.reply_text(HELP_MESSAGE)

    def start(self):
        ''' START '''
        # Commands received by the bot
        self.dp.add_handler(CommandHandler('coins', self.coin_price))
        self.dp.add_handler(CommandHandler(
            'sch', self.set_schedule_dec(self.send_hello)))
        self.dp.add_handler(CommandHandler('default',
            self.set_schedule_dec(self.coins_from_file)))
        self.dp.add_handler(CommandHandler('stop', self.stop_schedule))
        self.dp.add_handler(CommandHandler('bin', self.binance_price))
        self.dp.add_handler(CommandHandler('list', self.coins_file))
        self.dp.add_handler(CommandHandler('remote', self.switch_remote))
        # self.dp.add_handler(CommandHandler('wsp', self.schedule_wsp))
        self.dp.add_handler(CommandHandler('start', self.send_help))
        self.dp.add_handler(CommandHandler('help', self.send_help))
        self.dp.add_error_handler(self.error_callback)

        # Starting bot
        self.updater.start_polling()
        # Bot waiting messages
        self.updater.idle()

    def __init__(self):
        if os.path.exists('./token.txt'):
            with open('./token.txt', 'r+') as fd:
                token = fd.read()
                key = getpass.getpass(prompt="Insert password: ")
                TOKEN = encrypted.password_decrypt(token, key).decode()
        else:
            TOKEN = input("Insert token: ")
            key = getpass.getpass(prompt="Insert password: ")
            with open('./token.txt', 'w+') as fd:
                print(encrypted.password_encrypt(TOKEN.encode(), key).decode(), file=fd)
        print("Iniciando bot....")
        self.updater = Updater(TOKEN, use_context=True)
        self.dp = self.updater.dispatcher
        self.threads_running = []
        self.owner = 1934620415
        self.actRemote = False
        self.chatScheduleId = []


if __name__ == '__main__':
    coinBot = TelegramBot()
    coinBot.start()


"""
    def search_price_bin(url, browser, newCoin, results, lock):
        if lock.acquire():
            browser.get(url)
            text = browser.page_source
            lock.release()
        parsed = BeautifulSoup(text, "html.parser")
        price = parsed.find(class_=re.compile("showPrice")).get_text()
        data = {"Price": price}
        results[newCoin] = data


    def search_price_market(self, url, newCoin, results):
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
"""
