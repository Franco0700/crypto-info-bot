from pprint import pformat
import re
import requests

from bs4 import BeautifulSoup
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext, CommandHandler
from telegram import Update, Bot

def search_price_market(url, newCoin, results):
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
        results[ '<b>' + newCoin + '</b>'] = data
    else:
        results[ '<b>' + newCoin + '</b>'] = "Crypto Not Found"
