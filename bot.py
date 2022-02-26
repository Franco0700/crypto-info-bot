from bs4 import BeautifulSoup
import requests
import schedule
import threading
import sys
import re
import json
import ast
from pprint import pformat
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext, CommandHandler
from telegram import Update, Bot

def search_price(url, newCoin, results):
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
        results[newCoin] = "Crypto incorrecta"


def start(update, context):
    ''' START '''
    # Enviar un mensaje a un ID determinado.
    context.bot.send_message(update.message.chat_id, "Bienvenido")

def coinPrice(update, context):
    th = []
    results = {}
    for coin in context.args:
        newCoin = coin.rstrip('\n\r')
        url = "https://coinmarketcap.com/es/currencies/" + newCoin + "/"
        x = threading.Thread(target=search_price, args=(url, newCoin, results))
        th.append(x)
        x.start()
    for i in th:
        i.join()
    update.message.reply_text(results)

def main():
    TOKEN="5230134533:AAHYhqOIC-dNFvjT46d-8df5K_tIgV0xCxI"
    updater=Updater(TOKEN, use_context=True)
    dp=updater.dispatcher

    # Eventos que activarán nuestro bot.
    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('coins', coinPrice))
    
    #dp.add_handler(MessageHandler(filters=Filters.all, callback=handle_message))

    # Comienza el bot
    updater.start_polling()
    # Lo deja a la escucha. Evita que se detenga.
    updater.idle()

if __name__ == '__main__':
    main()

"""
def bot_send_text(bot_message):
    bot_token = "5230134533:AAHYhqOIC-dNFvjT46d-8df5K_tIgV0xCxI"
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