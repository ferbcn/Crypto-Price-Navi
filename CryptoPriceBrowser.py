#!/usr/bin/python3

"""
Crypto Price Browser GUI written in Python3 with PyQt5

Author: Fernando Garcia Winterling

"""

# TODO:
# Memory leakage (are instances grabage collected correctly?): try with fig.cla(); #fig.close() fig.clf(plt) #+Garbage collector?


import sys
import requests
import datetime as dt
import json

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from PyQt5.QtWidgets import QMainWindow, QAction, qApp, QPushButton, QApplication, QMessageBox, QDesktopWidget, \
    QSizePolicy, QLineEdit, QComboBox, QLabel,  QHBoxLayout, QVBoxLayout, QListWidget, QListWidgetItem, QSplitter, QWidget, QInputDialog, QScrollArea
from PyQt5.QtGui import QIcon, QPixmap, QImage, QColor
from PyQt5.QtCore import QTimer, QByteArray, QBuffer
from PyQt5 import QtWidgets
from PyQt5 import QtCore, QtGui

import asyncio
import concurrent.futures

import matplotlib.dates as mdates
import math

import matplotlib._color_data as mcd

import os
import shutil

########################
##  Global variables  ##
########################

currencies = ['EUR', 'USD', 'BTC', 'ETH', 'BNB']
timeWords = ['1-hour', '1-day', '1-week', '1-month', '3-months', '6-months', '1-year']
timeLim = [60, 1440, 168, 720, 90, 180, 365]
timeLimScale = ['minute', 'minute', 'hour', 'hour', 'day', 'day', 'day']

PRICE_URL = "https://min-api.cryptocompare.com/data/histo"

# custom colors
CANVAS_BG_COL = "gainsboro"
#CANVAS_BG_COL = "#595959"
#CANVAS_BG_COL = "grey"
#PLOT_BG_COL = "#595959"
PLOT_BG_COL = "lightgrey"
TITLE_COL = "k"
GRID_COL = 'grey'

# auto refresh timeout
TIMEOUT = 60000

########################
##  Helper functions  ##
########################

def check_color(color_name):
    if color_name in mcd.CSS4_COLORS:
        return True
    else:
        return False

def getScreenRes (self):
    screen_resolution = app.desktop ().screenGeometry ()
    width, height = screen_resolution.width (), screen_resolution.height ()
    return width, height

# PRE: an array of floats
# POST: returns % change between sum of first three vs sum of last three items
def calcGrowthRate (prices):
    #        print(prices)
    if len (prices) > 0:
        p2 = prices[len (prices) - 1]
        p1 = prices[0]
        if p1 == 0:
            return 0
        ChangePct = float (p2) / float (p1) - 1
        return ChangePct * 100
    else:
        return 0

# Cryptocompare API wrapper
def getTickerPrices (ticker='BTC', currency='USD', time='minute', lim=60):
    # build URL and call api
    fullURL = PRICE_URL + time + '?fsym=' + ticker + '&tsym=' + currency + '&limit=' + str (lim)
    #print(fullURL)
    try:
        r = requests.get (fullURL)
        tickerData = r.json ()
        priceData = tickerData["Data"]
        return priceData
    except Exception as e:
        print (e)
        priceData = {}
        return priceData


def get_top_coins (top=10):
    # build URL and call api
    URL = 'https://min-api.cryptocompare.com/data/top/totalvol?limit=' + str(top) + '&tsym=BTC'
    try:
        r = requests.get (URL)
        tickerData = r.json ()
        volumeData = tickerData["Data"]
        return volumeData

    except Exception as e:
        print(e)
        volumeData = {}
        return volumeData


# prints data to console
def print_data_console(all_price_data, coinList, timeScale, currency, lim, growthRates, last_time):
    print("\nNew data fetched ({}), timeframe: {}, currency: {}".format(last_time, timeWords[timeScale], currency))
    print ('{0:5}{1:>10}{2:>10}'.format ('COIN', 'PRICE', '% CHANGE'))
    for i, coin in enumerate(coinList):
        if coin == currency:
            lastp = 1
        else:
            lastp = all_price_data[coin][lim]["close"]
        print('{0:5}{1:10}{2:10.1f}'.format(coin, lastp, growthRates[i]))


# custom formatter for date labels in x-axis
def format_xaxis (plt, timeScale):
    ax = plt.gca ()  # create axis
    if timeScale == 0:
        ax.xaxis.set_major_locator (mdates.MinuteLocator (interval=10))
        ax.xaxis.set_major_formatter (mdates.DateFormatter ('%H:%M'))
    elif timeScale == 1:
        ax.xaxis.set_major_locator (mdates.HourLocator (interval=4))
        ax.xaxis.set_major_formatter (mdates.DateFormatter ('%H:%M'))
    elif timeScale == 2:
        ax.xaxis.set_major_locator (mdates.DayLocator (interval=1))
        ax.xaxis.set_major_formatter (mdates.DateFormatter ('%d/%m'))
    elif timeScale == 3:
        ax.xaxis.set_major_locator (mdates.DayLocator (interval=6))
        ax.xaxis.set_major_formatter (mdates.DateFormatter ('%d/%m/%y'))
    elif timeScale == 4:
        ax.xaxis.set_major_locator (mdates.DayLocator (interval=16))
        ax.xaxis.set_major_formatter (mdates.DateFormatter ('%d/%m/%y'))
    elif timeScale == 5:
        ax.xaxis.set_major_locator (mdates.DayLocator (interval=30))
        ax.xaxis.set_major_formatter (mdates.DateFormatter ('%m/%y'))
    elif timeScale == 6:
        ax.xaxis.set_major_locator (mdates.DayLocator (interval=60))
        ax.xaxis.set_major_formatter (mdates.DateFormatter ('%m/%y'))
    return plt


### ASYNCIO MAGIC for simulataneous http requests ###
loop = asyncio.get_event_loop ()

async def main (currency, time, lim, coinList):
    price_data = []
    price_data_dict = dict.fromkeys(coinList.keys())
    with concurrent.futures.ThreadPoolExecutor (max_workers=10) as executor:
        futures = [loop.run_in_executor (None, getTickerPrices, coin, currency, time, lim) for coin in coinList]
        for response in await asyncio.gather (*futures):
            price_data.append(response)

    for index, coin in enumerate(price_data_dict):
        price_data_dict[coin] = price_data[index]

    return price_data_dict

# load all coin list from config files
def load_coin_lists():
    # load all coins lists
    with open ('all_coins.txt') as json_file:
        allCoins = json.load (json_file)

    # load coinList names and data
    all_coin_lists_names = []
    all_coin_lists = []
    all_coin_lists_dict = {}

    try:
        with open ('coin_lists.txt') as json_file:
            clist_data = json.load (json_file)
            all_coin_lists_dict = clist_data  # needed for customization in settings mode
        for listname in clist_data:
            all_coin_lists_names.append (listname)
            all_coin_lists.append (clist_data[listname])

    except Exception:
        print ("could not load config files!")
        # TO-DO: create config file

    return allCoins, all_coin_lists_names, all_coin_lists, all_coin_lists_dict


def make_dir(dirname):
    current_path = os.getcwd()
    path = os.path.join(current_path, dirname)
    if not os.path.exists(path):
        os.makedirs(path)


########################
##      Main App      ##
########################

# the main window application class
# defines the UI
class App (QMainWindow):

    def __init__ (self):
        super ().__init__ ()

        self.currency = 'EUR'
        self.coinListIndex = 0

        #FigureCanvas.setSizePolicy (self, QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)

        self.timeScale = 1
        self.lim = timeLim[self.timeScale]
        self.time = timeLimScale[self.timeScale]
        self.view = 0

        self.thisWidth, self.thisHeight = getScreenRes (self)

        self.timeout = TIMEOUT

        self.initUI ()

    def initUI (self):

        # Window Geometry
        self.setGeometry (0, 0, int(self.thisWidth * 0.4), int(self.thisHeight * 0.5))
        #self.setStyleSheet("background-color: gainsboro")
        self.setAutoFillBackground(True)
        p = self.palette()
        p.setColor(self.backgroundRole(), QColor(CANVAS_BG_COL))
        self.setPalette(p)
        #self.center ()
        self.setWindowTitle ('Crypto Price Browser')
        self.setWindowOpacity(1)

        # MENU
        # define exit action of menu
        exitAct = QAction (QIcon ('images/exit.png'), '&Exit', self)
        exitAct.setShortcut ('Ctrl+Q')
        exitAct.setStatusTip ('Exit application')
        exitAct.triggered.connect (qApp.quit)

        toggleViewAct = QAction (QIcon ('images/refresh.png'), '&Toggle View', self)
        toggleViewAct.setShortcut ('Ctrl+T')
        toggleViewAct.setStatusTip ('toggle view')
        toggleViewAct.triggered.connect (self.toggleView)

        loadMultiAct = QAction (QIcon ('images/graph.png'), '&Multi Coins Panel', self)
        loadMultiAct.setShortcut ('Ctrl+M')
        loadMultiAct.setStatusTip ('Plot Multi Coins Panel')
        loadMultiAct.triggered.connect (self.loadMulti)

        customizeAct = QAction (QIcon ('images/settings.png'), '&Customize Coins', self)
        customizeAct.setShortcut ('Ctrl+C')
        customizeAct.setStatusTip ('Settings')
        customizeAct.triggered.connect (self.loadSettings)

        loadManyAct = QAction (QIcon ('images/graph.png'), '&Indexed Coins Plot', self)
        loadManyAct.setShortcut ('Ctrl+I')
        loadManyAct.setStatusTip ('Plot Many Coins')
        loadManyAct.triggered.connect (self.loadMany)

        aboutAct = QAction (QIcon ('images/about.png'), '&About', self)
        aboutAct.setStatusTip ('About')
        aboutAct.triggered.connect (self.dispAbout)

        self.autoupdateAct = QAction (QIcon ('images/refresh.png'), '&Auto Update', self, checkable=True)
        self.autoupdateAct.setStatusTip ('Auto Update')
        self.autoupdateAct.setChecked (True)
        self.autoupdateAct.triggered.connect (self.toggle_timeout)

        # MENUBAR
        menubar = self.menuBar ()
        menubar.setNativeMenuBar (False)

        fileMenu = menubar.addMenu ('&File')
        fileMenu.addAction (exitAct)

        viewMenu = menubar.addMenu ('View')
        viewMenu.addAction (loadMultiAct)
        viewMenu.addAction (loadManyAct)

        settingsMenu = menubar.addMenu ('&Settings')
        settingsMenu.addAction (customizeAct)
        settingsMenu.addAction (self.autoupdateAct)

        aboutMenu = menubar.addMenu ('&About')
        aboutMenu.addAction (aboutAct)

        # TOOLBAR: define which actions will be shown in the toolbar
        toolbar = self.addToolBar ('Exit')
        toolbar.addAction (exitAct)
        toolbar = self.addToolBar ('Toggle Main View')
        toolbar.addAction (toggleViewAct)
        toolbar = self.addToolBar ('Customize CoinList')
        toolbar.addAction (customizeAct)

        # MAIN PAGE LAYOUT
        page_layout = QVBoxLayout()
        page_widget = QWidget()
        page_widget.setLayout(page_layout)

        # MAIN PLOT
        # create the the matplot canvas instance
        self.CL = PlotMultiCoins (self)
        self.CL.move (0, 50)  # make space for menu and buttons

        plot_layout = QHBoxLayout()
        plot_layout.addWidget(self.CL)
        plot_widget = QWidget()
        plot_widget.setContentsMargins(0,0,0,0)
        plot_widget.setMaximumHeight(500)
        plot_widget.setLayout(plot_layout)

        # GROWTH GRAPH
        # create the the matplot canvas instance
        self.GL = PlotGrowthGraph(self)

        graph_layout = QHBoxLayout()
        graph_layout.addWidget(self.GL)
        graph_widget = QWidget()
        graph_widget.setContentsMargins(0, 0, 0, 0)
        # plot_widget.setMinimumHeight(400)
        graph_widget.setLayout(graph_layout)

        # DROP DOWN MENU WIDGET
        ddmenus_layout = QHBoxLayout()
        ddmenus_widget = QWidget()
        ddmenus_widget.setLayout(ddmenus_layout)
        #ddmenus_widget.setFixedHeight(50)
        ddmenus_widget.setMinimumSize(400, 50)
        #ddmenus_widget.setMaximumSize(600, 50)
        #ddmenus_widget.setFixedWidth(300)

        page_layout.addWidget(ddmenus_widget)
        page_layout.addWidget(plot_widget)
        page_layout.addWidget(graph_widget)
        self.setCentralWidget(page_widget)

        # load all coins lists from file
        self.allCoins, self.all_coin_lists_names, self.all_coin_lists, self.all_coin_lists_dict = load_coin_lists()
        # current list
        try:
            self.coinList = self.all_coin_lists[self.coinListIndex]
        except:
            self.coinListIndex = 0
            self.coinList = self.all_coin_lists[self.coinListIndex]

        # Spacer

        # drop down menus
        self.comboBox1 = QComboBox(self)
        for list in self.all_coin_lists_names:
            self.comboBox1.addItem(list)
        # self.comboBox1.move (int(self.thisWidth / 2), 55)
        self.comboBox1.activated[int].connect(self.listChoice)
        self.comboBox1.setCurrentIndex(self.coinListIndex)
        ddmenus_layout.addWidget(self.comboBox1)

        self.comboBox2 = QComboBox(self)
        for t in timeWords:
            self.comboBox2.addItem(t)
        # self.comboBox2.move (int(self.thisWidth / 2 + self.thisWidth * 0.09), 55)
        self.comboBox2.activated[str].connect(self.timeChoice)
        self.comboBox2.setCurrentIndex(self.timeScale)
        ddmenus_layout.addWidget(self.comboBox2)

        self.comboBox3 = QComboBox(self)
        for curr in currencies:
            self.comboBox3.addItem(curr + "         ")
        # self.comboBox3.move (int(self.thisWidth / 2 + self.thisWidth * 0.18), 55)
        self.comboBox3.activated[str].connect(self.currencyChoice)
        self.comboBox3.setCurrentText(self.currency)
        ddmenus_layout.addWidget(self.comboBox3)

        # create a timer for auto-update of data
        self.timer0 = QTimer(self)
        self.timer0.timeout.connect(self.auto_load)

        if self.autoupdateAct.isChecked():
            self.timer0.start(self.timeout)

        # Draw the plots (returns an array of growth rates) and draw a bar graph
        if len(self.coinList) > 0:
            growthRates = self.CL.plot_multi(self.coinList, self.currency, self.timeScale, self.time, self.lim, self.view)
            self.GL.drawBarGraph(growthRates, self.coinList)

        self.show()

    def auto_load(self):
        self.CL.fig.clf()
        growthRates = self.CL.plot_multi(self.coinList, self.currency, self.timeScale, self.time, self.lim, self.view)
        #drawBarGraph(growthRates, self.coinList)
        self.CL.fig.canvas.draw()

    def listChoice(self, item):
        self.CL.fig.clf()
        self.coinListIndex = item
        self.coinList = self.all_coin_lists[item]
        # set current coinlist index globally (so child classes can retrieve it)
        myApp.coinListIndex = self.coinListIndex
        if len(self.coinList) > 0:
            growthRates = self.CL.plot_multi(self.coinList, self.currency, self.timeScale, self.time, self.lim, self.view)
            #drawBarGraph(growthRates, self.coinList)
        self.CL.fig.canvas.draw()

    def timeChoice(self, text):  # convert: "hour... year" to int value as defined in the index of timeWords array
        self.CL.fig.clf()
        for i, t in enumerate(timeWords):
            if t == text:
                # myApp.timeout = 10000
                self.CL.fig.clf()
                self.timeScale = i
                self.time = timeLimScale[i]
                self.lim = timeLim[i]
                growthRates = self.CL.plot_multi(self.coinList, self.currency, self.timeScale, self.time, self.lim, self.view)
                #drawBarGraph(growthRates, self.coinList)
                self.CL.fig.canvas.draw()

    def currencyChoice(self, text):
        self.CL.fig.clf()
        self.currency = text.strip()
        growthRates = self.CL.plot_multi(self.coinList, self.currency, self.timeScale, self.time, self.lim, self.view)
        #drawBarGraph(growthRates, self.coinList)
        self.CL.fig.canvas.draw()
        myApp.currency = self.currency

    def toggle_timeout(self, state):
        try: # settings mode will have the timer deactivated
            if not state:
                self.CL.timer0.stop ()
            else:
                self.CL.timer0.start (self.timeout)
        except Exception:
            pass

    def center (self):
        qr = self.frameGeometry ()
        cp = QDesktopWidget ().availableGeometry ().center ()
        qr.moveCenter (cp)
        self.move (qr.topLeft ())

    def closeEvent (self, event):
        reply = QMessageBox.question (self, 'Message',
                                      "Are you sure to quit?", QMessageBox.Yes |
                                      QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            event.accept ()
        else:
            event.ignore ()

    def kill_timer(self):
        try:
            self.CL.timer0.stop ()
        except Exception:
            pass

    def loadMulti (self):
        # del self.CL
        self.CL.close ()
        self.CL.deleteLater ()
        self.kill_timer ()
        self.view = 0
        self.CL = PlotMultiCoins (self)
        self.CL.move (0, 65)

    def loadMany (self):
        #del self.CL
        self.CL.close ()
        self.CL.deleteLater ()
        self.kill_timer ()
        self.view = 1
        self.CL = PlotMultiCoins (self)
        self.CL.move (0, 65)

    def toggleView (self):
        if self.view == 0:
            self.view = 1
        else:
            self.view = 0
        self.loadFresh ()

    def loadFresh (self):
        if self.view == 1:
            self.loadMany()
        else:
            self.view = 0
            self.loadMulti()

    def loadSettings (self):
        #del self.CL
        self.CL.close ()
        self.CL.deleteLater ()
        self.kill_timer ()
        self.view = 2
        self.CL = PlotCustomize (self)
        self.CL.move (0, 65)

    def dispAbout (self):
        mes = 'Author: Fernando Garcia Winterling <html><br>GitHub: <a href = "https://github.com/ferbcn/CryptoPriceGUI">CryptoPriceGUI</a> <br>Data API: <a href = "https://min-api.cryptocompare.com/">CryptoCompare API</a></html>'
        QMessageBox.question (self, 'GUI Message', mes, QMessageBox.Ok, QMessageBox.Ok)


########################
##  Multi Coin Plot   ##
########################

class PlotGrowthGraph (FigureCanvas):

    def __init__ (self, parent):

        self.thisWidth = parent.thisWidth
        self.thisHeight = parent.thisHeight

        self.fig = plt.figure (figsize=(self.thisWidth / 80, self.thisHeight / 10), dpi=80)
        self.fig.set_facecolor (CANVAS_BG_COL)
        FigureCanvas.__init__ (self, self.fig)
        self.setParent (parent)

    # draws a bar graph given an input of GR (array) and coinList (dictionary)
    def drawBarGraph (self, GR, coinList):

        ind = [n for n in range (len (coinList))]
        width = 0.5  # the width of the bars

        axBar = plt.axes ([0.1, 0, 0.8, 0.1])
        rects = axBar.bar (ind, GR, width, color=list(coinList.values()))

        axBar.set_ylabel ('%')
        axBar.set_title ('Change in %')
        axBar.set_xticks (ind)
        axBar.set_facecolor(PLOT_BG_COL)
        axBar.yaxis.grid (color=GRID_COL, linestyle='dashed')
        axBar.set_axisbelow (True)

        xLabels = coinList.keys()
        axBar.set_xticklabels (xLabels)

        # put the labels on the graphs
        for rect in rects:
            height = rect.get_height ()
            axBar.text (rect.get_x () + rect.get_width () / 2., 1.0 * height, "%.1f" % float (height), ha='center',
                        va='bottom')
            # add colors
        plt.draw ()



class PlotMultiCoins (FigureCanvas):

    def __init__ (self, parent):

        self.timeScale = parent.timeScale
        self.currency = parent.currency
        self.lim = timeLim[self.timeScale]
        self.time = timeLimScale[self.timeScale]
        self.coinListIndex = parent.coinListIndex
        self.thisWidth = parent.thisWidth
        self.thisHeight = parent.thisHeight
        self.timeout = parent.timeout
        self.view = parent.view

        self.fig = plt.figure (figsize=(self.thisWidth / 80, self.thisHeight / 80), dpi=80)
        self.fig.set_facecolor (CANVAS_BG_COL)

        FigureCanvas.__init__ (self, self.fig)

        self.setParent (parent)

    # Main Graph Plotting function
    def plot_multi(self, coinList, currency, timeScale, time, lim, view):

        growthRates = []  # will be passed to the batr graph drawing function

        # get all data with asyncio (blackmagic!)
        all_price_data = loop.run_until_complete(main(currency, time, lim, coinList))

        # View 0 shows a grid
        if view == 0:
            # adjust grid structure depending on number of items to show (hacky but i don't wana mess with matplotlib now)
            list_len = len(coinList)
            row = 1
            col = list_len
            if list_len > 2:
                row = 2
                col = math.ceil(list_len / row)
            if list_len > 6:
                row = 3
                col = math.ceil(list_len / row)

            pl = 1  # sublots counter

            for coin in coinList:
                # draw current sublot
                p = plt.subplot(row, col, pl)
                pl += 1
                # plt.tight_layout()

                # extract prices for current coin from all_price_data
                price_data = all_price_data[coin]

                prices = []
                times = []
                volumes = []

                # mambojambo to catch special case: coin == base currency (no data provided by api)
                # write prices and dates to array avoiding exceptions and ugly graphs further down
                if currency == coin:
                    for i in range(lim + 1):
                        prices.append(1.0)
                        volumes.append(1.0)
                        if time == 'minute':
                            d = dt.datetime.now() - dt.timedelta(minutes=lim)
                            d = d + dt.timedelta(minutes=i)
                        elif time == 'hour':
                            d = dt.datetime.now() - dt.timedelta(hours=lim)
                            d = d + dt.timedelta(hours=i)
                        elif time == 'day':
                            d = dt.datetime.now() - dt.timedelta(days=lim)
                            d = d + dt.timedelta(days=i)
                        times.append(d)
                    # drawing every plot
                    plt.plot(times, prices, color=coinList[coin])
                    ax = plt.gca()
                    ax.set_facecolor(PLOT_BG_COL)
                    ax.xaxis.grid(color=GRID_COL, linestyle='dashed')
                    ax.yaxis.grid(color=GRID_COL, linestyle='dashed')

                else:
                    for data in price_data:
                        prices.append(data["close"])
                        times.append(dt.datetime.fromtimestamp(data["time"]))
                        volumes.append(data["volumefrom"] + (data["volumeto"]))

                    # draw this coins plot
                    # prices
                    ax = plt.gca()
                    # volumes on secondary axis
                    ax2 = ax.twinx()

                    # correct x-axis ticks and date format
                    ax.set_facecolor(PLOT_BG_COL)
                    ax.xaxis.grid(color=GRID_COL, linestyle='dashed')
                    ax.yaxis.grid(color=GRID_COL, linestyle='dashed')
                    color = GRID_COL
                    ax2.tick_params(axis='y', labelcolor=color)

                    ax.plot(times, prices, color=coinList[coin])
                    ax2.fill_between(times, 0, volumes, facecolor=color, alpha=0.5)
                    # ax2.set_yticklabels ([])
                    ax2.axis('off')
                    format_xaxis(plt, timeScale)

                changePct = calcGrowthRate(prices)
                growthRates.append(changePct)

                # save timestamp of last data received for later use
                if len(times) > 0:
                    last_time = times[len(times) - 1]
                    # add title and label (price infos: Min, MAX, LAST) to every subplot
                    plt.title(str(coin))
                    plt.xlabel('Min: ' + str(min(prices)) + ' - Max: ' + str(max(prices)) + ' - Last: ' + str(
                        prices[len(prices) - 1]))
                else:
                    last_time = dt.datetime.now()

        # View 1 shows a single graph with all coins index and plotted together
        elif view == 1:

            # create one single subplot
            p = plt.subplot(111)

            for coin in coinList:
                # query data for current coin and draw it to subplot
                prices = []
                times = []

                # extract prices for current coin from all_price_data
                price_data = all_price_data[coin]

                # write prices to array  when coin == currency, avoiding exceptions and ugly graphs further down
                if currency == coin:
                    for i in range(lim + 1):
                        prices.append(1.0)
                        times.append(dt.datetime.now())
                else:
                    for data in price_data:
                        prices.append(data["close"])
                        times.append(dt.datetime.fromtimestamp(data["time"]))

                drawThisCoin = False

                if len(times) > 0:
                    last_time = times[len(times) - 1]

                    # index coins to 100 and set a flag to not plot if no initial data available
                    drawThisCoin = True
                    base = prices[0]
                    if base == 0:  # check for bad data
                        drawThisCoin = False
                    else:
                        for i in range(len(prices)):
                            prices[i] = prices[i] / base * 100

                    # add title
                    plt.title("Indexed Crypto-Prices")
                    plt.draw()

                # plot current coin only if data is valid
                if drawThisCoin == True:
                    plt.plot(times, prices, color=coinList[coin], label=coin)
                    changePct = calcGrowthRate(prices)
                    growthRates.append(changePct)
                    plt.draw()
                    plt.legend()
                else:
                    growthRates.append(0)

            # correct x-axis ticks and date format
            format_xaxis(plt, timeScale)

            # custom bg color
            ax = plt.gca()
            ax.set_facecolor(PLOT_BG_COL)

            # adjust legend style
            legend = ax.legend()
            # Put a nicer background color on the legend.
            legend.get_frame().set_facecolor(CANVAS_BG_COL)

            # add grid to bg
            ax.yaxis.grid(color=GRID_COL, linestyle='dashed')
            ax.xaxis.grid(color=GRID_COL, linestyle='dashed')

        # Title / Info Box
        plt.axes([0.3, 0.9, 0.5, 0.05])
        plt.axis('off')
        t = 'Prices in ' + currency + ' last ' + str(lim) + ' ' + time + 's (' + timeWords[
            timeScale] + ')'
        plt.text(0, 1, t, fontproperties='sans', fontsize='x-large')

        # adjust position of subplot-grid on window
        # plt.subplots_adjust (hspace=0.6, left=0.05, right=0.75, bottom=0.4)

        # print data to console
        if len(times) > 0:
            print_data_console(all_price_data, coinList, timeScale, currency, lim, growthRates, last_time)

        # return array with calculated growth rates
        return growthRates


###############
#  CUSTOMIZE  #
###############

# Custom Widget Class that allows drag & drop between QList Widgets
class ThumbListWidget(QListWidget):

    def __init__(self, type, parent=None):
        super(ThumbListWidget, self).__init__(parent)
        self.setIconSize(QtCore.QSize(124, 124))
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDrop)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            super(ThumbListWidget, self).dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()
        else:
            super(ThumbListWidget, self).dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()
            links = []
            for url in event.mimeData().urls():
                links.append(str(url.toLocalFile()))
        else:
            event.setDropAction(QtCore.Qt.MoveAction)
            super(ThumbListWidget, self).dropEvent(event)
        self.setFocus()


class PlotCustomize (QMainWindow):

    def __init__ (self, parent):

        super ().__init__ ()
        QMainWindow.__init__ (self)

        self.setMinimumSize(1000, 700)

        self.setParent (parent)

        self.thisHeight = parent.thisHeight
        self.thisWidth = parent.thisWidth

        self.coinListIndex = parent.coinListIndex

        # read all coin lists from file
        self.allCoins, self.all_coin_lists_names, self.all_coin_lists, self.all_coin_lists_dict = load_coin_lists ()

        self.coinList = self.all_coin_lists[self.coinListIndex]

        # get con infos top 150 by volume
        self.all_coin_infos = get_top_coins(150)
        #print(self.all_coin_infos)

        self.initUI ()

    def initUI (self):

        # get screen size and set app size
        screen_resolution = app.desktop ().screenGeometry ()
        self.screenW, self.screenH = screen_resolution.width (), screen_resolution.height ()

        myQWidget = QWidget ()
        self.setCentralWidget (myQWidget)

        # the main layout Box (vertical)
        mainVerticalLayout = QVBoxLayout ()

        # Select the list to edit from a drop down menu (vertical)
        listSeleBox = QHBoxLayout ()
        # Selector for the current list to edit
        selectorTitle = QLabel()
        selectorTitle.setText("List to edit:")
        # create buttons
        addListButton = QPushButton ("Add List")
        removeListButton = QPushButton ("Remove List")
        addListButton.setMaximumWidth(100)
        removeListButton.setMaximumWidth(100)
        # spliter (make some space)
        mySpace = QSplitter()

        # drop down menu
        self.seleComboBox = QComboBox (self)
        for list in self.all_coin_lists_names:
            self.seleComboBox.addItem (list)
        self.seleComboBox.setMaximumWidth(200)
        # connect drop down menu
        self.seleComboBox.activated[int].connect (self.listChoice)
        self.seleComboBox.setCurrentIndex (self.coinListIndex)
        # add widgets to list sele box container
        listSeleBox.addWidget (selectorTitle)
        listSeleBox.addWidget (self.seleComboBox)
        listSeleBox.addWidget (addListButton)
        listSeleBox.addWidget (removeListButton)
        listSeleBox.addWidget (mySpace)


        # create two QList items (horizontal)
        listsTextBox = QHBoxLayout ()
        TextLeft = QLabel()
        TextLeft.setText("Available Coins:")
        listsTextBox.addWidget(TextLeft)

        TextRight = QLabel ()
        TextRight.setText ("Coins in the current List:")
        listsTextBox.addWidget (TextRight)

        listsBox = QHBoxLayout ()
        self.listWidgetA = ThumbListWidget (self)
        self.listWidgetA.setAcceptDrops (False)
        #self.listWidgetA.setAlternatingRowColors (True)
        self.listWidgetA.setStyleSheet ("""QListWidget{background: gainsboro;}""")  # arrrgg no variabl!!!!???
        for coin in self.allCoins:
            item = QListWidgetItem(coin, self.listWidgetA)
        self.listWidgetB = ThumbListWidget (self)
        self.listWidgetB.setAcceptDrops (True)
        self.listWidgetB.setContextMenuPolicy (QtCore.Qt.ActionsContextMenu)
        #self.listWidgetB.setAlternatingRowColors (True)
        self.listWidgetB.setStyleSheet( """QListWidget{background: gainsboro;}""") #arrrgg no variabl!!!!???

        listsBox.addWidget (self.listWidgetA)
        listsBox.addWidget (self.listWidgetB)

        # create some text below
        infoTextBelow = QHBoxLayout ()

        self.infoTextLeft = QLabel ()
        self.infoTextLeft.setText ("Number of coins: " + str(len(self.allCoins)))
        infoTextBelow.addWidget (self.infoTextLeft)

        self.infoTextRight = QLabel ()
        self.infoTextRight.setText ("Number of coins in list: " + str(self.listWidgetB.count()))
        infoTextBelow.addWidget (self.infoTextRight)

        # buttons to edit the master list
        masterButtonsBox = QHBoxLayout ()
        addCoinMasterButt = QPushButton ("Add One Coin")
        loadCoinsMasterButt = QPushButton ("Load Top Coins")
        delCoinMasterButt = QPushButton ("Remove Coin(s)")

        # buttons for the editing list
        delButton = QPushButton ("Delete Item")
        clrButton = QPushButton ("Clear List ")
        saveButton = QPushButton ("Save List  ")

        # define layout: horizontal box with three buttons in it
        buttonsBox = QHBoxLayout ()
        buttonsBox.addWidget (addCoinMasterButt)
        buttonsBox.addWidget (loadCoinsMasterButt)
        buttonsBox.addWidget (delCoinMasterButt)
        buttonsBox.addWidget (mySpace)
        buttonsBox.addWidget (delButton)
        buttonsBox.addWidget (clrButton)
        buttonsBox.addWidget (saveButton)
        buttonsBox.setContentsMargins (0, 0, 0, 0)

        coinInfoTitleBox = QHBoxLayout ()
        coinInfoLabel = QLabel()
        coinInfoLabel.setText ("Coin Infos:")
        coinInfoTitleBox.addWidget(coinInfoLabel)

        coinInfoBox = QHBoxLayout ()
        self.coinInfoText = QLabel ()
        self.coinInfoText.setText ("")
        self.coin_logo = QLabel()
        self.coin_logo.setMaximumSize(200,200)
        coinInfoBox.addWidget (mySpace)
        coinInfoBox.addWidget (self.coin_logo)
        coinInfoBox.addWidget (mySpace)
        coinInfoBox.addWidget (self.coinInfoText)
        coinInfoBox.addWidget (mySpace)

        # add all elements to the layout
        mainVerticalLayout.addLayout (listSeleBox)
        mainVerticalLayout.addLayout (listsTextBox)
        mainVerticalLayout.addLayout (listsBox)
        mainVerticalLayout.addLayout (infoTextBelow)
        mainVerticalLayout.addLayout (masterButtonsBox)
        mainVerticalLayout.addLayout (buttonsBox)
        mainVerticalLayout.addLayout (coinInfoTitleBox)
        mainVerticalLayout.addLayout (coinInfoBox)

        myQWidget.setLayout (mainVerticalLayout)

        # connect button to methods on_click
        delButton.clicked.connect (self.deleteItem)
        clrButton.clicked.connect (self.clearList)
        saveButton.clicked.connect (self.saveList)
        addListButton.clicked.connect (self.add_list)
        removeListButton.clicked.connect (self.remove_list)
        loadCoinsMasterButt.clicked.connect (self.load_coins_web)
        addCoinMasterButt.clicked.connect (self.add_one_coin)
        delCoinMasterButt.clicked.connect (self.del_coins_master)

        # connect list widgets
        self.listWidgetA.itemDoubleClicked.connect (self.add_coin_color_to_list)
        self.listWidgetA.itemChanged.connect (self.update_infos)
        self.listWidgetB.itemChanged.connect (self.update_infos)
        self.listWidgetA.itemClicked.connect (self.update_coin_infos)

        self.listChoice(self.coinListIndex)

        self.show ()


    def update_coin_infos(self, arg):
        # update coin infos
        coin_ticker = self.listWidgetA.currentItem().text()
        coin_infos_str = ""
        for item in self.all_coin_infos:
            if item["CoinInfo"]["Name"] == coin_ticker:
                coin_infos = item["CoinInfo"]
                #print(coin_infos)
                coin_infos_str += "Coin: " + item["CoinInfo"]["Name"] + "\n"
                coin_infos_str += "Full Name: " + item["CoinInfo"]["FullName"] + "\n"
                coin_infos_str += "Algorithm: " + item["CoinInfo"]["Algorithm"] + "\n"
                coin_infos_str += "Prooftype: " + item["CoinInfo"]["ProofType"] + "\n"
                coin_infos_str += "Blocktime: " + str(item["CoinInfo"]["BlockTime"]) + "\n"
                coin_infos_str += "Blockreward: " + str(item["CoinInfo"]["BlockReward"]) + "\n"

                coin_infos_str += "Supply: " + str (item["ConversionInfo"]["Supply"]) + "\n"
                coin_infos_str += "Volume 24H: " + str (item["ConversionInfo"]["TotalVolume24H"]) + "\n"

                self.coinInfoText.setText (str(coin_infos_str))

                # get coin logo for selected ticker
                # get image and save to logos folder
                url_file_name = coin_infos["ImageUrl"]
                extension = os.path.splitext (url_file_name)[1]
                if os.path.exists ('images/logos/' + coin_ticker + extension):
                    print (coin_ticker+extension, " exists!")
                else:
                    print ("Fetching: ", url_file_name)
                    url = 'https://www.cryptocompare.com'
                    full_url = url + url_file_name
                    #print(full_url)
                    response = requests.get (full_url)
                    with open ('images/logos/' + coin_ticker + extension, 'wb') as out_file:
                        out_file.write (response.content)
                    del response

                #load the image
                pixmap = QPixmap ('images/logos/' + coin_ticker + extension)
                pixmap_resized = pixmap.scaledToWidth(128)

                #pixmap = QPixmap()
                #image = QImage()
                #image.load('logos/' + coin_ticker + extension)
                #qimg = image.convertToFormat(QImage.Format_RGB888)
                #pixmap.convertFromImage(qimg)
                self.coin_logo.setPixmap (pixmap_resized)
                #self.coin_logo.setPixmap (pixmap)
                #self.coin_logo.show ()


    def del_coins_master(self):
        reply = QMessageBox.question (self, 'Coin List Management', "Delete coin(s) from master file?", QMessageBox.Ok)
        if reply:
            listItems = self.listWidgetA.selectedItems ()
            for item in listItems:
                self.listWidgetA.takeItem (self.listWidgetA.row (item))
                if item.text() in self.allCoins:
                    del self.allCoins[item.text()]
        self.update_infos()
        # overwrite current master file
        with open ('all_coins.txt', 'w') as outfile:
            json.dump (self.allCoins, outfile)
        self.allCoins, self.all_coin_lists_names, self.all_coin_lists, self.all_coin_lists_dict = load_coin_lists ()



    def add_coin_color_to_list(self): # add/modify coin color and save it to master list
        current_coin = self.listWidgetA.currentItem().text()
        if current_coin in self.allCoins:
            current_coin_color = self.allCoins[current_coin]
        else:
            current_coin_color = ''
        #open dialog
        text, okPressed = QInputDialog.getText (self, "Coin List Management", "Set color for " + current_coin, QLineEdit.Normal, current_coin_color)
        if okPressed and text != '':
            current_coin_color = text
             #check if color is accepted by matplotlib
            if not check_color(current_coin_color):
                all_colors = ""
                for color in mcd.CSS4_COLORS:
                    all_colors += color + " "
                QMessageBox.information (self, 'Coin List Management', 'Wrong Color! Use one from this list: ' + all_colors)
            else:
                # retrieve current coins from editing list, covert to dict and add coresponding colors found in allCoins
                new_entry = {current_coin:current_coin_color}
                self.allCoins.update(new_entry)
                # overwrite current master file
                with open ('all_coins.txt', 'w') as outfile:
                    json.dump (self.allCoins, outfile)
                QMessageBox.question (self, 'GUI Message', "Coin and color updated in master list ", QMessageBox.Ok)
                self.allCoins, self.all_coin_lists_names, self.all_coin_lists, self.all_coin_lists_dict = load_coin_lists ()


    def add_one_coin(self):
        text, okPressed = QInputDialog.getText (self, "Coin List Management", "Add one coin (Cryptocompare.com Ticker): ", QLineEdit.Normal, "")
        if okPressed and text != '':
            self.listWidgetA.addItem (text.upper())
        self.update_infos()

    def load_coins_web(self):
        data = get_top_coins(150)
        new_ticker_list = []
        for i in range(len(data)):
            new_ticker_list.append(data[i]["CoinInfo"]["Name"])
        for ticker in new_ticker_list:
            all_items_in_list = []
            for index in range (self.listWidgetA.count ()):
                all_items_in_list.append (self.listWidgetA.item (index).text())
            if not ticker in all_items_in_list:
                self.listWidgetA.addItem(ticker)
        self.update_infos ()

    def add_list(self):
        text, okPressed = QInputDialog.getText (self, "Coin List Management", "New List: ", QLineEdit.Normal, "")
        if okPressed and text != '':
            print ("New list " + text + " was created.")
            new_lists_dict = self.all_coin_lists_dict
            #append the new list
            new_entry = {text: {}}
            new_lists_dict.update(new_entry)
            #update combobox and class variables concerning coin lists
            with open ('coin_lists.txt', 'w') as outfile:
                json.dump (new_lists_dict, outfile)
                #QMessageBox.information (self, 'Coin List Management', "New list created!")
            self.seleComboBox.addItem(text)
            self.allCoins, self.all_coin_lists_names, self.all_coin_lists, self.all_coin_lists_dict = load_coin_lists ()
            self.seleComboBox.setCurrentIndex(self.seleComboBox.count()-1)
            self.listWidgetB.clear()
            self.listChoice (self.seleComboBox.count()-1)

    def remove_list(self):
        if len (self.all_coin_lists) < 2:
            QMessageBox.information (self, 'Coin List Management', 'You need at least one list')
        else:
            reply = QMessageBox.question (self, 'Coin List Management', "Remove list: " + str(self.all_coin_lists_names[self.coinListIndex]), QMessageBox.Yes |
                                      QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                new_lists_dict = self.all_coin_lists_dict
                # remove current list
                current_list_name = self.all_coin_lists_names[self.seleComboBox.currentIndex()]
                del new_lists_dict[current_list_name]
                print(current_list_name, "deleted!")
                print("New list dict: ", new_lists_dict)
                # update combobox and class variables concerning coin lists
                with open ('coin_lists.txt', 'w') as outfile:
                    json.dump (new_lists_dict, outfile)
                print ('List removed for ever!')
                self.seleComboBox.removeItem(self.coinListIndex)
                self.allCoins, self.all_coin_lists_names, self.all_coin_lists, self.all_coin_lists_dict = load_coin_lists ()

                self.listChoice (self.coinListIndex-1)

    def listChoice(self, item):
        #print('List', item, 'selected for edition.')
        self.clearList()
        self.currentListToEdit = self.all_coin_lists[item]
        for coin in self.currentListToEdit:
            item = QListWidgetItem(coin, self.listWidgetB)
        self.coinListIndex = self.seleComboBox.currentIndex()
        myApp.coinListIndex = self.coinListIndex
        self.update_infos()

    def update_infos(self):
        #print('List changed!')
        if self.listWidgetB.count() > 12:
            self.infoTextRight.setStyleSheet ('color: red')
        else:
            self.infoTextRight.setStyleSheet ('color: black')
        self.infoTextLeft.setText ("Number of coins: " + str (self.listWidgetA.count()))
        self.infoTextRight.setText ("Number of coins: " + str (self.listWidgetB.count ()))

    def deleteItem(self):
        listItems = self.listWidgetB.selectedItems()
        if not listItems:
            if self.listWidgetB.count() > 0:
                #self.deleteItem()
                self.listWidgetB.takeItem (self.listWidgetB.count()-1)
        for item in listItems:
            self.listWidgetB.takeItem(self.listWidgetB.row(item))
        self.update_infos ()

    def clearList(self):
        self.listWidgetB.setCurrentItem(self.listWidgetB.item(0))
        for i in range(self.listWidgetB.count()):
            self.listWidgetB.clear()
        self.update_infos ()


    def saveList (self):
        #retrieve current coins from editing list, covert to dict and add coresponding colors found in allCoins
        num_items = self.listWidgetB.count ()
        list2save = []
        for i in range (num_items):
            list2save.append(self.listWidgetB.item(i).text())
        name_current_list = self.all_coin_lists_names[self.coinListIndex]
        new_lists_dict = self.all_coin_lists_dict

        if len (list2save) > 12:
            QMessageBox.question (self, 'Coin List Management', "Sorry, max. 12 coins per list! \nRemove items from list to save it.",
                                  QMessageBox.Ok, QMessageBox.Ok)
        else:
            #create dictionary (coin:color pairs) of curren modified list
            dict_list2save = dict.fromkeys(list2save)
            for key in dict_list2save:
                try:
                    dict_list2save[key] = self.allCoins[key]
                except KeyError:
                    dict_list2save[key] = "gray" # set default color for new coins (i.e. not present in master coinlist)

            #overwrite current list
            new_lists_dict[name_current_list] = dict_list2save

            with open ('coin_lists.txt', 'w') as outfile:
                json.dump (new_lists_dict, outfile)
            QMessageBox.question (self, 'GUI Message', "Current list saved! ", QMessageBox.Ok)
            self.allCoins, self.all_coin_lists_names, self.all_coin_lists, self.all_coin_lists_dict = load_coin_lists ()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    myApp = App()
    sys.exit(app.exec_())
