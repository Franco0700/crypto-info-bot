from bs4 import BeautifulSoup
import requests
import schedule
import threading
import sys
import os
import signal
import re
import json
import ast
from pprint import pformat
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext, CommandHandler
from telegram import Update, Bot
import logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',level=logging.INFO)
logger = logging.getLogger(__name__)

class TelegramBot:
    def coins_from_file(self, time, update, context):
        with open('Coins.txt', "r") as fh:
            th = []
            results = {}
            for coin in fh.readlines():
                newCoin = coin.rstrip('\n\r')
                url = "https://coinmarketcap.com/es/currencies/" + newCoin + "/"
                x = threading.Thread(target=self.search_price, args=(url, newCoin, results))
                th.append(x)
                x.start()
            for i in th:
                i.join()
            update.message.reply_text(results)
        x = threading.Timer(time, function=self.coins_from_file, args=(time, update, context))
        x.start()

    def search_price(self, url, newCoin, results):
        req = requests.get(url)
        if req.status_code == 200:
            parsed = BeautifulSoup(req.text, "html.parser")
            priceTit = parsed.find(class_=re.compile("priceTitle"))
            price = priceTit.find(class_=re.compile("priceValue")).get_text()
            percentage = priceTit.find(style=re.compile("font-size:14px;font-weight:600;padding:5px 10px")).get_text()
            table = parsed.find(class_=re.compile("sc-16r8icm-0 fmPyWa")).findAll(scope=re.compile("row"))[2]
            if (priceTit.find(class_="icon-Caret-up")):
                percentage = "+" +  percentage
            else:
                percentage = "-" +  percentage
            data = {
                "Price": price,
                "Percentage": percentage,
                "Minimo en 24h/ Maximo en 24h": table.find_next_sibling("td").getText()
            }
            results[newCoin] = data
        else:
            results[newCoin] = "Crypto Not Found"

    def error_callback(self, update, context):
        logger.warning('Update "%s" caused error "%s"', update, context.error)

    def coin_price(self, update, context):
        th = []
        results = {}
        for coin in context.args:
            newCoin = coin.rstrip('\n\r')
            url = "https://coinmarketcap.com/es/currencies/" + newCoin + "/"
            x = threading.Thread(target=self.search_price, args=(url, newCoin, results))
            th.append(x)
            x.start()
        for i in th:
            i.join()
        update.message.reply_text(results)

    def send_hello(self, time, id, bot):
        bot.send_message(id, "Hola")
        x = threading.Timer(time, function=self.send_hello, args=(time, id, bot))
        x.start()
        
    #def schedule_every(self, scd, id, bot):
    #    schedule.every(scd).seconds.do(self.send_hello, id=id, bot=bot)
    #    while True:
    #        schedule.run_pending()

    def set_schedule(self, update, context):
        id = update.message.chat_id
        time = int(context.args[0])
        context.bot.send_message(update.message.chat_id, "Okay, send message in " + time + " seconds")
        x = threading.Timer(time, function=self.send_hello, args=(time, id, context.bot))
        self.threads_running.append(x)
        x.start()
    
    def default(self, update, context):
        time = int(context.args[0])
        context.bot.send_message(update.message.chat_id, "Okay, send message in " + context.args[0] + " seconds")
        x = threading.Timer(time, function=self.coins_from_file, args=(time, update, context))
        self.threads_running.append(x)
        x.start()


    def start(self):
        ''' START '''
         # Eventos que activarán nuestro bot.
        self.dp.add_handler(CommandHandler('coins', self.coin_price))
        self.dp.add_handler(CommandHandler('sch', self.set_schedule))
        self.dp.add_handler(CommandHandler('default', self.default))
        self.dp.add_error_handler(self.error_callback)

        # Comienza el bot
        self.updater.start_polling()
        # Lo deja a la escucha. Evita que se detenga.
        self.updater.idle()

    def __init__(self):
        TOKEN="TOKEN"
        self.updater=Updater(TOKEN, use_context=True)
        self.dp = self.updater.dispatcher
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


if __name__ == "__main__":
    with open(sys.argv[1], "r") as fh:
        th=list()
        results={}
        for coin in fh.readlines():
            newCoin = coin.rstrip('\n\r')
            url = "https://coinmarketcap.com/es/currencies/" + newCoin + "/"
            x = threading.Thread(target=search_price, args=(url, newCoin, results))
            th.append(x)
            x.start()
        for i in th:
            i.join()
        bot_send_text(results)
"""