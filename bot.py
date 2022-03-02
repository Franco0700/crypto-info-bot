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
from Scraping import *
import yaml
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.service import Service
from webdriver_manager.firefox import GeckoDriverManager
from pprint import pformat
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext, CommandHandler
from telegram import Update, Bot, constants
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
                    target=search_price_market, args=(url, newCoin, results))
                scrapTh.append(x)
                x.start()
            for i in scrapTh:
                i.join()
            bot.send_message(th.owner, yaml.dump(
                results), constants.PARSEMODE_HTML)

    def error_callback(self, update, context):
        logger.warning('Update "%s" caused error "%s"', update, context.error)

    def record_callback(self, update, bot):
        mes = update.message
        message = ('\n' +
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
        if self.actRemote:
            bot.send_message(self.owner, message)

    def binance_price(self, update, context):
        self.record_callback(update, context.bot)
        results = {}
        th = []
        lock = threading.Lock()
        browser = webdriver.Firefox(
            service=Service(GeckoDriverManager().install()))
        for coin in context.args:
            newCoin = coin.rstrip('\n\r').upper()
            url = "https://www.binance.com/en/trade/" + newCoin + "_BUSD"
            x = threading.Thread(target=search_price_bin,
                                 args=(url, browser, newCoin, results, lock))
            th.append(x)
            x.start()
        for i in th:
            i.join()
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
            print("Something went wrong")

    def set_schedule(self, func, update, context):
        self.record_callback(update, context.bot)
        id = update.message.chat_id
        time = int(context.args[0])
        index = bisect.bisect(self.chatScheduleId, id)
        th = SavedThread(index, id, time)
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
        self.chatScheduleId.insert(index, id)
        func((th, context.bot))
        x.start()

    def stop_schedule(self, update, context):
        self.record_callback(update, context.bot)
        id = update.message.chat_id
        index = bisect.bisect(self.chatScheduleId, id)
        ownerSchId = int(context.args[0])
        i = 1
        notFinded = True
        beforeElem = self.threads_running[index - i]
        while (beforeElem.owner == id
                and beforeElem.index != ownerSchId
                and i <= index):
            i += 1
            beforeElem = self.threads_running[index - i]
        if (i <= index and beforeElem.owner == id):
            beforeElem.mustContinue = False
        else:
            context.bot.send_message(
                id, "Not message scheduled for you with that schedule id")

    def coins_file(self, update, context):
        self.record_callback(update, context.bot)
        id = update.message.chat_id
        bot = context.bot
        th = SavedThread(1, id, 0)
        self.coins_from_file((th, bot))

    def switch_remote(self, update, context):
        if (update.message.chat.id == self.owner):
            if self.actRemote:
                self.actRemote = False
                update.message.reply_text("Remote logging desactivated")
            else:
                self.actRemote = True
                update.message.reply_text("Remote logging activated")
        else:
            self.record_callback(update, context.bot)
            update.message.reply_text("You can't perform this action")

    def start(self):
        ''' START '''
        # Commands received by the bot
        self.dp.add_handler(CommandHandler('coins', self.coin_price))
        self.dp.add_handler(CommandHandler(
            'sch', partial(self.set_schedule, self.send_hello)))
        self.dp.add_handler(CommandHandler('default', partial(
            self.set_schedule, self.coins_from_file)))
        self.dp.add_handler(CommandHandler('stop', self.stop_schedule))
        self.dp.add_handler(CommandHandler('bin', self.binance_price))
        self.dp.add_handler(CommandHandler('list', self.coins_file))
        self.dp.add_handler(CommandHandler('remote', self.switch_remote))
        self.dp.add_error_handler(self.error_callback)

        # Starting bot
        self.updater.start_polling()
        # Bot waiting messages
        self.updater.idle()

    def __init__(self):
        TOKEN = "TOKEN"
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
