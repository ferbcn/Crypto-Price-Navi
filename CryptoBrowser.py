import sys
import numpy as np
import random

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QWidget, QPushButton, QHBoxLayout, QVBoxLayout, QLabel, QComboBox, QSlider
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure


import sys
import requests
import datetime as dt
import json

#import matplotlib.pyplot as plt
#from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

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
    if timeScale == 0:
        plt.xaxis.set_major_locator (mdates.MinuteLocator (interval=10))
        plt.xaxis.set_major_formatter (mdates.DateFormatter ('%H:%M'))
    elif timeScale == 1:
        plt.xaxis.set_major_locator (mdates.HourLocator (interval=4))
        plt.xaxis.set_major_formatter (mdates.DateFormatter ('%H:%M'))
    elif timeScale == 2:
        plt.xaxis.set_major_locator (mdates.DayLocator (interval=1))
        plt.xaxis.set_major_formatter (mdates.DateFormatter ('%d/%m'))
    elif timeScale == 3:
        plt.xaxis.set_major_locator (mdates.DayLocator (interval=6))
        plt.xaxis.set_major_formatter (mdates.DateFormatter ('%d/%m/%y'))
    elif timeScale == 4:
        plt.xaxis.set_major_locator (mdates.DayLocator (interval=16))
        plt.xaxis.set_major_formatter (mdates.DateFormatter ('%d/%m/%y'))
    elif timeScale == 5:
        plt.xaxis.set_major_locator (mdates.DayLocator (interval=30))
        plt.xaxis.set_major_formatter (mdates.DateFormatter ('%m/%y'))
    elif timeScale == 6:
        plt.xaxis.set_major_locator (mdates.DayLocator (interval=60))
        plt.xaxis.set_major_formatter (mdates.DateFormatter ('%m/%y'))
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

# adjust grid structure depending on number of items to show (hacky but i don't wana mess with matplotlib now)
def make_grid(current_coin_list):
    list_len = len(current_coin_list)
    row = 1
    col = list_len
    if list_len > 2:
        row = 2
        col = math.ceil(list_len / row)
    if list_len > 6:
        row = 3
        col = math.ceil(list_len / row)
    return row, col


########################
##### PLOT CLASS #######
########################

class MplCanvas(FigureCanvasQTAgg):

    def __init__(self, current_coin_list, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super(MplCanvas, self).__init__(self.fig)
        #self.fig.set_facecolor('#595959')
        self.fig.set_facecolor(CANVAS_BG_COL)
        #self.fig.tight_layout(h_pad=1)

        self.coin_list = current_coin_list

        self.subplots = []
        self.plot_lines = []

        self.growth_rates = []


    def draw_plots(self, coin_list, currency, timeScale, time, lim, view):

        # reset array where growth rates are calculated
        self.growth_rates = []

        # get price data for current coinlist
        all_price_data = loop.run_until_complete(main(currency, time, lim, coin_list))

        row, col = make_grid(coin_list)
        pl = 1  # sublots counter
        for coin in coin_list:
            # draw current sublot
            sub_plt = self.fig.add_subplot(row, col, pl)
            self.subplots.append(sub_plt)
            pl += 1
            # plt.tight_layout()
            sub_plt.set(xlabel='', facecolor='#595959')
            sub_plt.xaxis.label.set_fontsize('small')
            sub_plt.set(facecolor='#595959')
            #sub_plt.set(facecolor='#3a3a3a')
            sub_plt.set_title(coin, color='#000000', size='medium')
            sub_plt.tick_params(axis='both', which='major', labelsize=6, labelcolor='#000000')

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

                sub_plt.plot(times, prices, color=coin_list[coin])
                sub_plt.set_facecolor(PLOT_BG_COL)
                sub_plt.xaxis.grid(color=GRID_COL, linestyle='dashed')
                sub_plt.yaxis.grid(color=GRID_COL, linestyle='dashed')

                # drawing every plot
                sub_plt.plot(times, prices, color=coin_list[coin])
                sub_plt.set_facecolor(PLOT_BG_COL)

            else:
                for data in price_data:
                    prices.append(data["close"])
                    times.append(dt.datetime.fromtimestamp(data["time"]))
                    volumes.append(data["volumefrom"] + (data["volumeto"]) )

                # format axis
                sub_plt.set_facecolor(PLOT_BG_COL)
                sub_plt.xaxis.grid(color=GRID_COL, linestyle='dashed')
                sub_plt.yaxis.grid(color=GRID_COL, linestyle='dashed')
                color = GRID_COL
                sub_plt.tick_params(axis='y', labelcolor=color)

                # draw plot for current coin
                sub_plt.plot(times, prices, color=coin_list[coin])

                # draw volumes on secondary axis
                ax2 = sub_plt.twinx()
                ax2.fill_between(times, 0, volumes, facecolor=color, alpha=0.5)
                ax2.axis('off')
                format_xaxis(sub_plt, timeScale)

            changePct = calcGrowthRate(prices)
            self.growth_rates.append(changePct)

            # save timestamp of last data received for later use
            if len(times) > 0:
                last_time = times[len(times) - 1]
                # add title and label (price infos: Min, MAX, LAST) to every subplot
                sub_plt.set_title(str(coin))
                #sub_plt.xlabel('Min: ' + str(min(prices)) + ' - Max: ' + str(max(prices)) + ' - Last: ' + str(prices[len(prices) - 1]))
            else:
                last_time = dt.datetime.now()

            # update figure
            self.fig.canvas.draw()
            #self.fig.canvas.flush_events()

        return self.growth_rates



class MplGrowthCanvas(FigureCanvasQTAgg):

    def __init__(self, current_coin_list, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super(MplGrowthCanvas, self).__init__(self.fig)
        self.fig.set_facecolor('#595959')
        self.fig.set_facecolor(CANVAS_BG_COL)
        self.coin_list = current_coin_list


    # draws a bar graph given an input of GR (array) and coinList (dictionary)
    def draw_graph (self, growth_rates, coinList):

        ind = [n for n in range (len (coinList))]
        width = 0.5  # the width of the bars
        axBar = self.fig.add_subplot(111)
        rects = axBar.bar (ind, growth_rates, width, color=list(coinList.values()))

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

        # update figure
        self.fig.canvas.draw()



########################
##### MAIN CLASS #######
########################

class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.title = 'Crypto Browser'
        self.setWindowTitle(self.title)

        screen_width, screen_height = getScreenRes(self)

        self.width = int(screen_width / 2)
        self.height = int(screen_height / 3 * 2)
        self.left = 10
        self.top = 10

        self.currency = 'EUR'
        self.coinListIndex = 0

        self.growth_rates = []

        self.timeScale = 1
        self.lim = timeLim[self.timeScale]
        self.time = timeLimScale[self.timeScale]
        self.view = 0

        self.timeout = TIMEOUT

        self.initUI()

        self.show()

    def initUI(self):

        # Window Geometry
        #self.setStyleSheet("background-color: #595959")
        self.setGeometry(0, 0, self.width, self.height)
        # self.setStyleSheet("background-color: gainsboro")
        self.setAutoFillBackground(True)
        p = self.palette()
        p.setColor(self.backgroundRole(), QColor(CANVAS_BG_COL))
        self.setPalette(p)

        # self.center ()
        self.setWindowTitle('Crypto Price Browser')
        self.setWindowOpacity(1)

        # MENU
        # define exit action of menu
        exitAct = QAction(QIcon('images/exit.png'), '&Exit', self)
        exitAct.setShortcut('Ctrl+Q')
        exitAct.setStatusTip('Exit application')
        exitAct.triggered.connect(qApp.quit)

        toggleViewAct = QAction(QIcon('images/refresh.png'), '&Toggle View', self)
        toggleViewAct.setShortcut('Ctrl+T')
        toggleViewAct.setStatusTip('toggle view')
        toggleViewAct.triggered.connect(self.toggleView)

        loadMultiAct = QAction(QIcon('images/graph.png'), '&Multi Coins Panel', self)
        loadMultiAct.setShortcut('Ctrl+M')
        loadMultiAct.setStatusTip('Plot Multi Coins Panel')
        loadMultiAct.triggered.connect(self.loadMulti)

        customizeAct = QAction(QIcon('images/settings.png'), '&Customize Coins', self)
        customizeAct.setShortcut('Ctrl+C')
        customizeAct.setStatusTip('Settings')
        customizeAct.triggered.connect(self.loadSettings)

        loadManyAct = QAction(QIcon('images/graph.png'), '&Indexed Coins Plot', self)
        loadManyAct.setShortcut('Ctrl+I')
        loadManyAct.setStatusTip('Plot Many Coins')
        loadManyAct.triggered.connect(self.loadMany)

        aboutAct = QAction(QIcon('images/about.png'), '&About', self)
        aboutAct.setStatusTip('About')
        aboutAct.triggered.connect(self.dispAbout)

        self.autoupdateAct = QAction(QIcon('images/refresh.png'), '&Auto Update', self, checkable=True)
        self.autoupdateAct.setStatusTip('Auto Update')
        self.autoupdateAct.setChecked(True)
        self.autoupdateAct.triggered.connect(self.toggle_timeout)

        # MENUBAR
        menubar = self.menuBar()
        menubar.setNativeMenuBar(False)

        fileMenu = menubar.addMenu('&File')
        fileMenu.addAction(exitAct)

        viewMenu = menubar.addMenu('View')
        viewMenu.addAction(loadMultiAct)
        viewMenu.addAction(loadManyAct)

        settingsMenu = menubar.addMenu('&Settings')
        settingsMenu.addAction(customizeAct)
        settingsMenu.addAction(self.autoupdateAct)

        aboutMenu = menubar.addMenu('&About')
        aboutMenu.addAction(aboutAct)

        # TOOLBAR: define which actions will be shown in the toolbar
        toolbar = self.addToolBar('Exit')
        toolbar.addAction(exitAct)
        toolbar = self.addToolBar('Toggle Main View')
        toolbar.addAction(toggleViewAct)
        toolbar = self.addToolBar('Customize CoinList')
        toolbar.addAction(customizeAct)

        page_layout = QVBoxLayout()
        page_widget = QWidget()
        page_widget.setLayout(page_layout)

        input_layout = QHBoxLayout()
        input_widget = QWidget()
        input_widget.setMaximumHeight(40)
        input_widget.setLayout(input_layout)

        # load all coins lists from file
        self.allCoins, self.all_coin_lists_names, self.all_coin_lists, self.all_coin_lists_dict = load_coin_lists()
        # current list
        try:
            self.coinList = self.all_coin_lists[self.coinListIndex]
        except:
            self.coinListIndex = 0
            self.coinList = self.all_coin_lists[self.coinListIndex]

        # drop down menus
        self.comboBox1 = QComboBox(self)
        for list in self.all_coin_lists_names:
            self.comboBox1.addItem(list)
        # self.comboBox1.move (int(self.thisWidth / 2), 55)
        self.comboBox1.activated[int].connect(self.listChoice)
        self.comboBox1.setCurrentIndex(self.coinListIndex)
        input_layout.addWidget(self.comboBox1)

        self.comboBox2 = QComboBox(self)
        for t in timeWords:
            self.comboBox2.addItem(t)
        # self.comboBox2.move (int(self.thisWidth / 2 + self.thisWidth * 0.09), 55)
        self.comboBox2.activated[str].connect(self.timeChoice)
        self.comboBox2.setCurrentIndex(self.timeScale)
        input_layout.addWidget(self.comboBox2)

        self.comboBox3 = QComboBox(self)
        for curr in currencies:
            self.comboBox3.addItem(curr + "         ")
        # self.comboBox3.move (int(self.thisWidth / 2 + self.thisWidth * 0.18), 55)
        self.comboBox3.activated[str].connect(self.currencyChoice)
        self.comboBox3.setCurrentText(self.currency)
        input_layout.addWidget(self.comboBox3)
        #input_widget.setContentsMargins(0, -50, 0, 0)

        # create a timer for auto-update of data
        self.timer0 = QTimer(self)
        self.timer0.timeout.connect(self.auto_load)

        if self.autoupdateAct.isChecked():
            self.timer0.start(self.timeout)

        # Create the maptlotlib FigureCanvas object,
        plot_layout = QVBoxLayout()
        self.CL = MplCanvas(self.coinList, width=5, height=4, dpi=100)
        self.growth_rates = self.CL.draw_plots(self.coinList, self.currency, self.timeScale, self.time, self.lim, self.view)
        plot_layout.addWidget(self.CL)
        plot_widget = QWidget()
        plot_widget.setContentsMargins(0,0,0,0)
        #plot_widget.setMinimumHeight(400)
        plot_widget.setLayout(plot_layout)

        # Create the maptlotlib FigureCanvas object,
        growth_plot_layout = QVBoxLayout()
        self.GL = MplGrowthCanvas(self.coinList, width=5, height=2, dpi=100)
        self.GL.draw_graph(self.growth_rates, self.coinList)
        growth_plot_layout.addWidget(self.GL)
        growth_plot_widget = QWidget()
        growth_plot_widget.setMaximumHeight(200)
        growth_plot_widget.setLayout(growth_plot_layout)

        page_layout.addWidget(input_widget)
        page_layout.addWidget(plot_widget)
        page_layout.addWidget(growth_plot_widget)
        self.setCentralWidget(page_widget)

        self.show()

    def auto_load(self):
        self.CL.fig.clf()
        self.GL.fig.clf()
        self.growth_rates = self.CL.draw_plots(self.coinList, self.currency, self.timeScale, self.time, self.lim, self.view)
        self.GL.draw_graph(self.growth_rates, self.coinList)

    def listChoice(self, item):
        self.CL.fig.clf()
        self.GL.fig.clf()
        self.coinListIndex = item
        self.coinList = self.all_coin_lists[item]
        self.growth_rates = self.CL.draw_plots(self.coinList, self.currency, self.timeScale, self.time, self.lim, self.view)
        self.GL.draw_graph(self.growth_rates, self.coinList)

    def timeChoice(self, text):  # convert: "hour... year" to int value as defined in the index of timeWords array
        self.CL.fig.clf()
        self.GL.fig.clf()
        for i, t in enumerate(timeWords):
            if t == text:
                # myApp.timeout = 10000
                self.CL.fig.clf()
                self.timeScale = i
                self.time = timeLimScale[i]
                self.lim = timeLim[i]
                self.growth_rates = self.CL.draw_plots(self.coinList, self.currency, self.timeScale, self.time, self.lim, self.view)
                self.GL.draw_graph(self.growth_rates, self.coinList)

    def currencyChoice(self, text):
        self.CL.fig.clf()
        self.GL.fig.clf()
        self.currency = text.strip()
        self.growth_rates = self.CL.draw_plots(self.coinList, self.currency, self.timeScale, self.time, self.lim, self.view)
        self.GL.draw_graph(self.growth_rates, self.coinList)

    def toggle_timeout(self, state):
        try: # settings mode will have the timer deactivated
            if not state:
                self.CL.timer0.stop ()
            else:
                self.CL.timer0.start (self.timeout)
        except Exception as e:
            print(e)

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
        except Exception as e:
            print(e)


    def loadMulti (self):
        pass

    def loadMany (self):
        pass

    def toggleView (self):
        pass

    def loadFresh (self):
        pass

    def loadSettings (self):
        pass

    def dispAbout (self):
        mes = 'Author: Fernando Garcia Winterling <html><br>GitHub: <a href = ""</a> <br>Data API: <a href = "https://min-api.cryptocompare.com/">CryptoCompare API</a></html>'
        QMessageBox.question (self, 'GUI Message', mes, QMessageBox.Ok, QMessageBox.Ok)


app = QtWidgets.QApplication(sys.argv)
w = MainWindow()
app.exec_()