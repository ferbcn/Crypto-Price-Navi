import sys
import requests
import datetime as dt
import json
import math
import asyncio
import concurrent.futures
import os

import matplotlib

matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure

import matplotlib.dates as mdates
import matplotlib._color_data as mcd

from PyQt5.QtWidgets import QMainWindow, QAction, qApp, QPushButton, QApplication, QMessageBox, QDesktopWidget, \
    QSizePolicy, QLineEdit, QComboBox, QLabel, QHBoxLayout, QVBoxLayout, QListWidget, QListWidgetItem, QSplitter, \
    QWidget, QInputDialog, QScrollArea
from PyQt5.QtGui import QIcon, QPixmap, QImage, QColor
from PyQt5.QtCore import QTimer
from PyQt5 import QtWidgets, QtCore

from list_widget import ThumbListWidget

########################
##  Global variables  ##
########################

currencies = ['EUR', 'USD', 'BTC', 'ETH', 'BNB']
timeWords = ['1-hour', '1-day', '1-week', '1-month', '3-months', '6-months', '1-year']
timeLim = [60, 1440, 168, 720, 90, 180, 365]
timeLimScale = ['minute', 'minute', 'hour', 'hour', 'day', 'day', 'day']

PRICE_URL = "https://min-api.cryptocompare.com/data/histo"

# custom colors
BG_COL_D = "#595959"
FACE_COL_D = "#444444"

BG_COL_L = "gainsboro"
FACE_COL_L = "lightgrey"

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


def getScreenRes(self):
    screen_resolution = app.desktop().screenGeometry()
    width, height = screen_resolution.width(), screen_resolution.height()
    return width, height


# PRE: an array of floats
# POST: returns % change between sum of first three vs sum of last three items
def calcGrowthRate(prices):
    #        print(prices)
    if len(prices) > 0:
        p2 = prices[len(prices) - 1]
        p1 = prices[0]
        if p1 == 0:
            return 0
        ChangePct = float(p2) / float(p1) - 1
        return ChangePct * 100
    else:
        return 0


# Cryptocompare API wrapper
def getTickerPrices(ticker='BTC', currency='USD', time='minute', lim=60):
    # build URL and call api
    fullURL = PRICE_URL + time + '?fsym=' + ticker + '&tsym=' + currency + '&limit=' + str(lim)
    # print(fullURL)
    try:
        r = requests.get(fullURL)
        tickerData = r.json()
        priceData = tickerData["Data"]
        return priceData
    except Exception as e:
        print(e)
        priceData = {}
        return priceData


def get_top_coins(top=10):
    # build URL and call api
    URL = 'https://min-api.cryptocompare.com/data/top/totalvol?limit=' + str(top) + '&tsym=BTC'
    #print(f'Fetching URL: {URL}')
    try:
        r = requests.get(URL)
        tickerData = r.json()
        volumeData = tickerData["Data"]
        return volumeData

    except Exception as e:
        print(e)
        volumeData = {}
        return volumeData


# prints data to console
def print_data_console(all_price_data, coinList, timeScale, currency, lim, growthRates, last_time):
    print("\nNew data fetched ({}), timeframe: {}, currency: {}".format(last_time, timeWords[timeScale], currency))
    print('{0:5}{1:>10}{2:>10}'.format('COIN', 'PRICE', '% CHANGE'))
    for i, coin in enumerate(coinList):
        if coin == currency:
            lastp = 1
        else:
            lastp = all_price_data[coin][lim]["close"]
        print('{0:5}{1:10}{2:10.1f}'.format(coin, lastp, growthRates[i]))


# custom formatter for date labels in x-axis
def format_xaxis(plt, timeScale):
    if timeScale == 0:
        plt.xaxis.set_major_locator(mdates.MinuteLocator(interval=10))
        plt.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    elif timeScale == 1:
        plt.xaxis.set_major_locator(mdates.HourLocator(interval=4))
        plt.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    elif timeScale == 2:
        plt.xaxis.set_major_locator(mdates.DayLocator(interval=1))
        plt.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
    elif timeScale == 3:
        plt.xaxis.set_major_locator(mdates.DayLocator(interval=6))
        plt.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m/%y'))
    elif timeScale == 4:
        plt.xaxis.set_major_locator(mdates.DayLocator(interval=16))
        plt.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m/%y'))
    elif timeScale == 5:
        plt.xaxis.set_major_locator(mdates.DayLocator(interval=30))
        plt.xaxis.set_major_formatter(mdates.DateFormatter('%m/%y'))
    elif timeScale == 6:
        plt.xaxis.set_major_locator(mdates.DayLocator(interval=60))
        plt.xaxis.set_major_formatter(mdates.DateFormatter('%m/%y'))
    return plt


### ASYNCIO MAGIC for simulataneous http requests ###
loop = asyncio.get_event_loop()

async def main(currency, time, lim, coinList):
    price_data = []
    price_data_dict = dict.fromkeys(coinList.keys())
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [loop.run_in_executor(None, getTickerPrices, coin, currency, time, lim) for coin in coinList]
        for response in await asyncio.gather(*futures):
            price_data.append(response)

    for index, coin in enumerate(price_data_dict):
        price_data_dict[coin] = price_data[index]

    return price_data_dict


# load all coin list from config files
def load_coin_lists():
    # load all coins lists
    with open('all_coins.txt') as json_file:
        allCoins = json.load(json_file)

    # load coinList names and data
    all_coin_lists_names = []
    all_coin_lists = []
    all_coin_lists_dict = {}

    try:
        with open('coin_lists.txt') as json_file:
            clist_data = json.load(json_file)
            all_coin_lists_dict = clist_data  # needed for customization in settings mode
        for listname in clist_data:
            all_coin_lists_names.append(listname)
            all_coin_lists.append(clist_data[listname])

    except Exception:
        print("could not load config files!")

    return allCoins, all_coin_lists_names, all_coin_lists, all_coin_lists_dict


def make_dir(dirname):
    current_path = os.getcwd()
    path = os.path.join(current_path, dirname)
    if not os.path.exists(path):
        os.makedirs(path)


# adjust grid structure depending on number of items to show (hacky...)
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

class MplPriceChartsCanvas(FigureCanvasQTAgg):

    def __init__(self, current_coin_list, dark_mode=True, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super(MplPriceChartsCanvas, self).__init__(self.fig)

        self.dark_mode = dark_mode
        self.bg_color = BG_COL_D
        self.plot_color = FACE_COL_D
        self.coin_list = current_coin_list

        self.fig.set_facecolor(self.bg_color)

        self.plot_lines = []
        self.growth_rates = []


    def draw_plots(self, coin_list, currency, timeScale, time, lim, view):

        self.sub_plots = []

        # reset array where growth rates are calculated
        self.growth_rates = []

        # get price data for current coinlist
        all_price_data = loop.run_until_complete(main(currency, time, lim, coin_list))

        agregated_volumes = [0 for _ in range(lim+1)]

        if view == 0:
            row, col = make_grid(coin_list)
            pl = 1  # sublots counter
        else:
            sub_plt = self.fig.add_subplot(111)
            self.sub_plots.append(sub_plt)
            sub_plt.xaxis.grid(color=GRID_COL, linestyle='dashed')
            sub_plt.yaxis.grid(color=GRID_COL, linestyle='dashed')
            sub_plt.set_title("Indexed Crypto Prices", color='#000000', size='medium')
            sub_plt.xaxis.label.set_fontsize('x-small')
            sub_plt.tick_params(axis='both', which='major', labelsize=6, labelcolor='#000000')

        for coin in coin_list:
            # flag cases with wrong or missing data
            draw_current_coin = True

            # draw current sublot
            if view == 0:
                sub_plt = self.fig.add_subplot(row, col, pl)
                self.sub_plots.append(sub_plt)
                sub_plt.set_title(coin, color='#000000', size='small')
                pl += 1
                sub_plt.xaxis.label.set_fontsize('x-small')
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

                # if view == 1 (indexed modes, we need to index all prices)
                if view == 1:
                    base = prices[0]
                    for i in range(len(prices)):
                        prices[i] = prices[i] / base * 100

                sub_plt.set_facecolor(self.plot_color)
                sub_plt.xaxis.grid(color=GRID_COL, linestyle='dashed')
                sub_plt.yaxis.grid(color=GRID_COL, linestyle='dashed')

                # drawing the plot
                sub_plt.plot(times, prices, color=coin_list[coin])
                sub_plt.set_facecolor(self.plot_color)

            # Normal case: Coin != base currency
            else:
                for i, data in enumerate(price_data):
                    prices.append(data["close"])
                    times.append(dt.datetime.fromtimestamp(data["time"]))
                    coin_volume = data["volumefrom"] + data["volumeto"]
                    volumes.append(coin_volume)
                    try:
                        agregated_volumes[i] += coin_volume
                    # first coin (agregated volumes still empty)
                    except Exception as e:
                        agregated_volumes.append(coin_volume)

                # if view == 1 (indexed mode, we need to index all prices)
                if view == 1:
                    try:
                        base = prices[0]
                        for i in range(len(prices)):
                            prices[i] = prices[i] / base * 100
                    except ZeroDivisionError:
                        draw_current_coin = False

                # draw plot for current coin
                if draw_current_coin:
                    sub_plt.plot(times, prices, color=coin_list[coin])

                sub_plt.set_facecolor(self.plot_color)
                sub_plt.xaxis.grid(color=GRID_COL, linestyle='dashed')
                sub_plt.yaxis.grid(color=GRID_COL, linestyle='dashed')
                # sub_plt.tick_params(axis='y', labelcolor=color)

                # draw volumes on secondary axis
                if view == 0:
                    ax2 = sub_plt.twinx()
                    ax2.fill_between(times, 0, volumes, facecolor='#000000', alpha=0.3)
                    ax2.axis('off')

            #calculate growth rates mode0 and mode1
            changePct = calcGrowthRate(prices)
            self.growth_rates.append(changePct)

        # END OF COIN LOOP
        # format time axis
        for sp in self.sub_plots:
            format_xaxis(sp, timeScale)

        if view == 1:
            ax2 = sub_plt.twinx()
            ax2.fill_between(times, 0, agregated_volumes, facecolor='#000000', alpha=0.3)
            ax2.axis('off')

        # update figure
        self.fig.tight_layout(h_pad=1)
        self.fig.canvas.draw()

        return self.growth_rates

    def switch_color_mode(self):
        if self.dark_mode:
            self.fig.set_facecolor('gainsboro')
            for plot in self.sub_plots:
                plot.set_facecolor('lightgrey')
            self.plot_color = 'lightgrey'
            self.dark_mode = False
        else:
            self.fig.set_facecolor('#595959')
            for plot in self.sub_plots:
                plot.set_facecolor('#333333')
            self.plot_color = '#333333'
            self.dark_mode = True


class MplGrowthCanvas(FigureCanvasQTAgg):

    def __init__(self, current_coin_list, dark_mode=True, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super(MplGrowthCanvas, self).__init__(self.fig)

        self.bg_color = BG_COL_D
        self.plot_color = FACE_COL_D
        self.dark_mode = dark_mode

        self.fig.set_facecolor(self.bg_color)
        self.coin_list = current_coin_list

    # draws a bar graph given an input of GR (array) and coinList (dictionary)
    def draw_graph(self, growth_rates, coinList):
        ind = [n for n in range(len(coinList))]
        width = 0.5  # the width of the bars
        self.axBar = self.fig.add_subplot(111)
        rects = self.axBar.bar(ind, growth_rates, width, color=list(coinList.values()))

        self.axBar.set_facecolor(self.plot_color)
        self.axBar.set_axisbelow(True)
        self.axBar.set_ylabel('%', color='#000000', size='x-small')
        self.axBar.set_title('Change in %', color='#000000', size='small')
        self.axBar.set_xticks(ind)
        self.axBar.tick_params(axis='both', which='major', labelsize=6, labelcolor='#000000')
        self.axBar.yaxis.grid(color=GRID_COL, linestyle='dashed')

        xLabels = coinList.keys()
        self.axBar.set_xticklabels(xLabels, color='#000000', size='small')

        # put the labels on the graphs
        for rect in rects:
            height = rect.get_height()
            self.axBar.text(rect.get_x() + rect.get_width() / 2., 1.0 * height, "%.1f" % float(height), ha='center',
                            va='bottom', size='small')
        # update figure
        self.fig.canvas.draw()

    def switch_color_mode(self):
        if self.dark_mode:
            self.fig.set_facecolor('gainsboro')
            self.axBar.set_facecolor('lightgrey')
            self.plot_color = 'lightgrey'
            self.dark_mode = False
        else:
            self.fig.set_facecolor('#595959')
            self.axBar.set_facecolor('#333333')
            self.plot_color = '#333333'
            self.dark_mode = True


###############
#  CUSTOMIZE  #
###############

class ListCustomizer(QWidget):

    def __init__(self, coinListIndex, dark_mode=True):

        super().__init__()

        self.coinListIndex = coinListIndex

        # read all coin lists from file
        self.allCoins, self.all_coin_lists_names, self.all_coin_lists, self.all_coin_lists_dict = load_coin_lists()
        self.coinList = self.all_coin_lists[self.coinListIndex]

        # get con infos top 150 by volume
        self.all_coin_infos = get_top_coins(100)

        self.dark_mode = dark_mode

        self.initUI()

    def initUI(self):

        # get screen size and set app size
        #screen_resolution = app.desktop().screenGeometry()
        #self.screenW, self.screenH = screen_resolution.width(), screen_resolution.height()

        #self.setStyleSheet("background-color: #595959")

        myQWidget = QWidget()
        # self.setCentralWidget (myQWidget)

        # the main layout Box (vertical)
        mainVerticalLayout = QVBoxLayout()
        #mainVerticalLayout.setContentsMargins(100,0,100,0)

        # Select the list to edit from a drop down menu (vertical)
        listSeleBox = QHBoxLayout()
        # Selector for the current list to edit
        selectorTitle = QLabel()
        selectorTitle.setText("List to edit:")
        # create buttons
        addListButton = QPushButton("Add List")
        removeListButton = QPushButton("Remove List")
        addListButton.setMaximumWidth(100)
        removeListButton.setMaximumWidth(100)
        # spliter (make some space)
        mySpace = QSplitter()

        # drop down menu
        self.seleComboBox = QComboBox(self)
        for list in self.all_coin_lists_names:
            self.seleComboBox.addItem(list)
        self.seleComboBox.setMaximumWidth(200)
        # connect drop down menu
        self.seleComboBox.activated[int].connect(self.listChoice)
        self.seleComboBox.setCurrentIndex(self.coinListIndex)
        # add widgets to list sele box container
        listSeleBox.addWidget(selectorTitle)
        listSeleBox.addWidget(self.seleComboBox)
        listSeleBox.addWidget(addListButton)
        listSeleBox.addWidget(removeListButton)
        listSeleBox.addWidget(mySpace)

        # create two QList items (horizontal)
        listsTextBox = QHBoxLayout()
        TextLeft = QLabel()
        TextLeft.setText("Available Coins:")
        listsTextBox.addWidget(TextLeft)

        TextRight = QLabel()
        TextRight.setText("Coins in the current List:")
        listsTextBox.addWidget(TextRight)

        listsBox = QHBoxLayout()
        self.listWidgetA = ThumbListWidget(self)
        self.listWidgetA.setAcceptDrops(False)
        # self.listWidgetA.setAlternatingRowColors (True)
        for coin in self.allCoins:
            item = QListWidgetItem(coin, self.listWidgetA)
        self.listWidgetB = ThumbListWidget(self)
        self.listWidgetB.setAcceptDrops(True)
        self.listWidgetB.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        # self.listWidgetB.setAlternatingRowColors (True)
        if self.dark_mode:
            self.listWidgetA.setStyleSheet("""QListWidget{background: #595959;}""")
            self.listWidgetB.setStyleSheet("""QListWidget{background: #595959;}""")
        else:
            self.listWidgetA.setStyleSheet("""QListWidget{background: gainsboro;}""")
            self.listWidgetB.setStyleSheet("""QListWidget{background: gainsboro;}""")

        listsBox.addWidget(self.listWidgetA)
        listsBox.addWidget(self.listWidgetB)

        # create some text below
        infoTextBelow = QHBoxLayout()

        self.infoTextLeft = QLabel()
        self.infoTextLeft.setText("Number of coins: " + str(len(self.allCoins)))
        infoTextBelow.addWidget(self.infoTextLeft)

        self.infoTextRight = QLabel()
        self.infoTextRight.setText("Number of coins in list: " + str(self.listWidgetB.count()))
        infoTextBelow.addWidget(self.infoTextRight)

        # buttons to edit the master list
        masterButtonsBox = QHBoxLayout()
        addCoinMasterButt = QPushButton("Add One Coin")
        loadCoinsMasterButt = QPushButton("Load Top Coins")
        delCoinMasterButt = QPushButton("Remove Coin(s)")

        # buttons for the editing list
        delButton = QPushButton("Delete Item")
        clrButton = QPushButton("Clear List ")
        saveButton = QPushButton("Save List  ")

        # define layout: horizontal box with three buttons in it
        buttonsBox = QHBoxLayout()
        buttonsBox.addWidget(addCoinMasterButt)
        buttonsBox.addWidget(loadCoinsMasterButt)
        buttonsBox.addWidget(delCoinMasterButt)
        buttonsBox.addWidget(mySpace)
        buttonsBox.addWidget(delButton)
        buttonsBox.addWidget(clrButton)
        buttonsBox.addWidget(saveButton)
        buttonsBox.setContentsMargins(0, 0, 0, 0)

        coinInfoTitleBox = QHBoxLayout()
        coinInfoLabel = QLabel()
        coinInfoLabel.setText("Coin Infos:")
        coinInfoTitleBox.addWidget(coinInfoLabel)

        coinInfoBox = QHBoxLayout()
        self.coinInfoText = QLabel()
        self.coinInfoText.setText("")
        self.coin_logo = QLabel()
        self.coin_logo.setMaximumSize(200, 200)
        coinInfoBox.addWidget(mySpace)
        coinInfoBox.addWidget(self.coin_logo)
        coinInfoBox.addWidget(mySpace)
        coinInfoBox.addWidget(self.coinInfoText)
        coinInfoBox.addWidget(mySpace)

        # add all elements to the layout
        mainVerticalLayout.addLayout(listSeleBox)
        mainVerticalLayout.addLayout(listsTextBox)
        mainVerticalLayout.addLayout(listsBox)
        mainVerticalLayout.addLayout(infoTextBelow)
        mainVerticalLayout.addLayout(masterButtonsBox)
        mainVerticalLayout.addLayout(buttonsBox)
        mainVerticalLayout.addLayout(coinInfoTitleBox)
        mainVerticalLayout.addLayout(coinInfoBox)

        myQWidget.setLayout(mainVerticalLayout)

        # connect button to methods on_click
        delButton.clicked.connect(self.deleteItem)
        clrButton.clicked.connect(self.clearList)
        saveButton.clicked.connect(self.saveList)
        addListButton.clicked.connect(self.add_list)
        removeListButton.clicked.connect(self.remove_list)
        loadCoinsMasterButt.clicked.connect(self.load_coins_web)
        addCoinMasterButt.clicked.connect(self.add_one_coin)
        delCoinMasterButt.clicked.connect(self.del_coins_master)

        # connect list widgets
        self.listWidgetA.itemDoubleClicked.connect(self.add_coin_color_to_list)
        self.listWidgetA.itemChanged.connect(self.update_infos)
        self.listWidgetB.itemChanged.connect(self.update_infos)
        self.listWidgetA.itemClicked.connect(self.update_coin_infos)

        self.listChoice(self.coinListIndex)

        self.setLayout(mainVerticalLayout)

        self.show()

    def update_coin_infos(self, arg):
        # update coin infos
        coin_ticker = self.listWidgetA.currentItem().text()
        coin_infos_str = ""
        for item in self.all_coin_infos:
            if item["CoinInfo"]["Name"] == coin_ticker:
                coin_infos = item["CoinInfo"]
                # print(coin_infos)
                coin_infos_str += "Coin: " + item["CoinInfo"]["Name"] + "\n"
                coin_infos_str += "Full Name: " + item["CoinInfo"]["FullName"] + "\n"
                coin_infos_str += "Algorithm: " + item["CoinInfo"]["Algorithm"] + "\n"
                coin_infos_str += "Prooftype: " + item["CoinInfo"]["ProofType"] + "\n"
                coin_infos_str += "Blocktime: " + str(item["CoinInfo"]["BlockTime"]) + "\n"
                coin_infos_str += "Blockreward: " + str(item["CoinInfo"]["BlockReward"]) + "\n"

                coin_infos_str += "Supply: " + str(item["ConversionInfo"]["Supply"]) + "\n"
                coin_infos_str += "Volume 24H: " + str(item["ConversionInfo"]["TotalVolume24H"]) + "\n"

                self.coinInfoText.setText(str(coin_infos_str))

                # get coin logo for selected ticker
                # get image and save to logos folder
                url_file_name = coin_infos["ImageUrl"]
                extension = os.path.splitext(url_file_name)[1]
                if os.path.exists('logos/' + coin_ticker + extension):
                    pass
                    # print (coin_ticker+extension, " exists!")
                else:
                    # print ("Fetching: ", url_file_name)
                    url = 'https://www.cryptocompare.com'
                    full_url = url + url_file_name
                    # print(full_url)
                    response = requests.get(full_url)
                    with open('logos/' + coin_ticker + extension, 'wb') as out_file:
                        out_file.write(response.content)
                    del response

                # load the image
                pixmap = QPixmap('logos/' + coin_ticker + extension)
                pixmap_resized = pixmap.scaledToWidth(128)

                # pixmap = QPixmap()
                # image = QImage()
                # image.load('logos/' + coin_ticker + extension)
                # qimg = image.convertToFormat(QImage.Format_RGB888)
                # pixmap.convertFromImage(qimg)
                self.coin_logo.setPixmap(pixmap_resized)
                # self.coin_logo.setPixmap (pixmap)
                # self.coin_logo.show ()

    def del_coins_master(self):
        reply = QMessageBox.question(self, 'Coin List Management', "Delete coin(s) from master file?", QMessageBox.Ok)
        if reply:
            listItems = self.listWidgetA.selectedItems()
            for item in listItems:
                self.listWidgetA.takeItem(self.listWidgetA.row(item))
                if item.text() in self.allCoins:
                    del self.allCoins[item.text()]
        self.update_infos()
        # overwrite current master file
        with open('all_coins.txt', 'w') as outfile:
            json.dump(self.allCoins, outfile)
        self.allCoins, self.all_coin_lists_names, self.all_coin_lists, self.all_coin_lists_dict = load_coin_lists()

    def add_coin_color_to_list(self):  # add/modify coin color and save it to master list
        current_coin = self.listWidgetA.currentItem().text()
        if current_coin in self.allCoins:
            current_coin_color = self.allCoins[current_coin]
        else:
            current_coin_color = ''
        # open dialog
        text, okPressed = QInputDialog.getText(self, "Coin List Management", "Set color for " + current_coin,
                                               QLineEdit.Normal, current_coin_color)
        if okPressed and text != '':
            current_coin_color = text
            # check if color is accepted by matplotlib
            if not check_color(current_coin_color):
                all_colors = ""
                for color in mcd.CSS4_COLORS:
                    all_colors += color + " "
                QMessageBox.information(self, 'Coin List Management',
                                        'Wrong Color! Use one from this list: ' + all_colors)
            else:
                # retrieve current coins from editing list, covert to dict and add coresponding colors found in allCoins
                new_entry = {current_coin: current_coin_color}
                self.allCoins.update(new_entry)
                # overwrite current master file
                with open('all_coins.txt', 'w') as outfile:
                    json.dump(self.allCoins, outfile)
                QMessageBox.question(self, 'GUI Message', "Coin and color updated in master list ", QMessageBox.Ok)
                self.allCoins, self.all_coin_lists_names, self.all_coin_lists, self.all_coin_lists_dict = load_coin_lists()

    def add_one_coin(self):
        text, okPressed = QInputDialog.getText(self, "Coin List Management",
                                               "Add one coin (Cryptocompare.com Ticker): ", QLineEdit.Normal, "")
        if okPressed and text != '':
            self.listWidgetA.addItem(text.upper())
        self.update_infos()

    def load_coins_web(self):
        data = get_top_coins(100)
        new_ticker_list = []
        for i in range(len(data)):
            new_ticker_list.append(data[i]["CoinInfo"]["Name"])
        for ticker in new_ticker_list:
            all_items_in_list = []
            for index in range(self.listWidgetA.count()):
                all_items_in_list.append(self.listWidgetA.item(index).text())
            if not ticker in all_items_in_list:
                self.listWidgetA.addItem(ticker)
        self.update_infos()

    def add_list(self):
        text, okPressed = QInputDialog.getText(self, "Coin List Management", "New List: ", QLineEdit.Normal, "")
        if okPressed and text != '':
            print("New list " + text + " was created.")
            new_lists_dict = self.all_coin_lists_dict
            # append the new list
            new_entry = {text: {}}
            new_lists_dict.update(new_entry)
            # update combobox and class variables concerning coin lists
            with open('coin_lists.txt', 'w') as outfile:
                json.dump(new_lists_dict, outfile)
                # QMessageBox.information (self, 'Coin List Management', "New list created!")
            self.seleComboBox.addItem(text)
            self.allCoins, self.all_coin_lists_names, self.all_coin_lists, self.all_coin_lists_dict = load_coin_lists()
            self.seleComboBox.setCurrentIndex(self.seleComboBox.count() - 1)
            self.listWidgetB.clear()
            self.listChoice(self.seleComboBox.count() - 1)

    def remove_list(self):
        if len(self.all_coin_lists) < 2:
            QMessageBox.information(self, 'Coin List Management', 'You need at least one list')
        else:
            reply = QMessageBox.question(self, 'Coin List Management',
                                         "Remove list: " + str(self.all_coin_lists_names[self.coinListIndex]),
                                         QMessageBox.Yes |
                                         QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                new_lists_dict = self.all_coin_lists_dict
                # remove current list
                current_list_name = self.all_coin_lists_names[self.seleComboBox.currentIndex()]
                del new_lists_dict[current_list_name]
                print(current_list_name, "deleted!")
                print("New list dict: ", new_lists_dict)
                # update combobox and class variables concerning coin lists
                with open('coin_lists.txt', 'w') as outfile:
                    json.dump(new_lists_dict, outfile)
                print('List removed for ever!')
                self.seleComboBox.removeItem(self.coinListIndex)
                self.allCoins, self.all_coin_lists_names, self.all_coin_lists, self.all_coin_lists_dict = load_coin_lists()

                self.listChoice(self.coinListIndex - 1)

    def listChoice(self, item):
        # print('List', item, 'selected for edition.')
        self.clearList()
        self.currentListToEdit = self.all_coin_lists[item]
        for coin in self.currentListToEdit:
            item = QListWidgetItem(coin, self.listWidgetB)
        self.coinListIndex = self.seleComboBox.currentIndex()
        self.coinListIndex = self.coinListIndex
        self.update_infos()

    def update_infos(self):
        # print('List changed!')
        if self.listWidgetB.count() > 12:
            self.infoTextRight.setStyleSheet('color: red')
        else:
            self.infoTextRight.setStyleSheet('color: black')
        self.infoTextLeft.setText("Number of coins: " + str(self.listWidgetA.count()))
        self.infoTextRight.setText("Number of coins: " + str(self.listWidgetB.count()))

    def deleteItem(self):
        listItems = self.listWidgetB.selectedItems()
        if not listItems:
            if self.listWidgetB.count() > 0:
                # self.deleteItem()
                self.listWidgetB.takeItem(self.listWidgetB.count() - 1)
        for item in listItems:
            self.listWidgetB.takeItem(self.listWidgetB.row(item))
        self.update_infos()

    def clearList(self):
        self.listWidgetB.setCurrentItem(self.listWidgetB.item(0))
        for i in range(self.listWidgetB.count()):
            self.listWidgetB.clear()
        self.update_infos()

    def saveList(self):
        # retrieve current coins from editing list, covert to dict and add coresponding colors found in allCoins
        num_items = self.listWidgetB.count()
        list2save = []
        for i in range(num_items):
            list2save.append(self.listWidgetB.item(i).text())
        name_current_list = self.all_coin_lists_names[self.coinListIndex]
        new_lists_dict = self.all_coin_lists_dict

        if len(list2save) > 12:
            QMessageBox.question(self, 'Coin List Management',
                                 "Sorry, max. 12 coins per list! \nRemove items from list to save it.",
                                 QMessageBox.Ok, QMessageBox.Ok)
        else:
            # create dictionary (coin:color pairs) of currently modified list
            dict_list2save = dict.fromkeys(list2save)
            for key in dict_list2save:
                try:
                    dict_list2save[key] = self.allCoins[key]
                except KeyError:
                    dict_list2save[
                        key] = "gray"  # set default color for new coins (i.e. not present in master coinlist)

            # overwrite current list
            new_lists_dict[name_current_list] = dict_list2save

            with open('coin_lists.txt', 'w') as outfile:
                json.dump(new_lists_dict, outfile)
            QMessageBox.question(self, 'GUI Message', "Current list saved! ", QMessageBox.Ok)
            self.allCoins, self.all_coin_lists_names, self.all_coin_lists, self.all_coin_lists_dict = load_coin_lists()

    def switch_color_mode(self):
        if self.dark_mode:
            self.listWidgetA.setStyleSheet("""QListWidget{background: gainsboro;}""")
            self.listWidgetB.setStyleSheet("""QListWidget{background: gainsboro;}""")
            self.dark_mode = False
        else:
            self.listWidgetA.setStyleSheet("""QListWidget{background: #595959;}""")
            self.listWidgetB.setStyleSheet("""QListWidget{background: #595959;}""")
            self.dark_mode = True


########################
##### MAIN CLASS #######
########################

class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.title = 'Crypto Browser'
        self.setWindowTitle(self.title)
        self.setStyleSheet("background-color: #595959")
        self.canvas_color = BG_COL_D

        screen_width, screen_height = getScreenRes(self)

        self.width = int(screen_width / 2)
        self.height = int(screen_height / 3 * 2)

        self.currency = 'EUR'
        self.coinListIndex = 0

        self.growth_rates = []

        self.timeScale = 1
        self.lim = timeLim[self.timeScale]
        self.time = timeLimScale[self.timeScale]
        self.view = 0

        self.dark_mode = True  # light = 0, dark = 1
        self.show_coinlist_editor = False  # flag that enables list customizer

        self.timeout = TIMEOUT

        self.initUI()

    def initUI(self):

        # Window Geometry
        # self.setStyleSheet("background-color: #595959")
        self.setGeometry(0, 0, self.width, self.height)
        # self.setStyleSheet("background-color: gainsboro")
        self.setAutoFillBackground(True)
        p = self.palette()
        p.setColor(self.backgroundRole(), QColor(self.canvas_color))
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

        toggleViewAct = QAction(QIcon('images/graph.png'), '&Toggle Price Chart View', self)
        toggleViewAct.setShortcut('Ctrl+T')
        toggleViewAct.setStatusTip('toggle view')
        toggleViewAct.triggered.connect(self.toggleView)

        toggledarklight = QAction(QIcon('images/bulb.png'), '&Toggle Dark/Light Mode', self)
        toggledarklight.setShortcut('Ctrl+D')
        toggledarklight.setStatusTip('toggle light/dark mode')
        toggledarklight.triggered.connect(self.switch_color_mode)

        loadMultiAct = QAction(QIcon('images/graph.png'), '&Multi Coins Panel', self)
        loadMultiAct.setShortcut('Ctrl+M')
        loadMultiAct.setStatusTip('Plot Multi Coins Panel')
        loadMultiAct.triggered.connect(self.loadMulti)

        customizeAct = QAction(QIcon('images/settings.png'), '&Customize Coin-Lists', self)
        customizeAct.setShortcut('Ctrl+C')
        customizeAct.setStatusTip('Settings')
        customizeAct.triggered.connect(self.load_customizer)

        loadManyAct = QAction(QIcon('images/graph.png'), '&Indexed Coins Plot', self)
        loadManyAct.setShortcut('Ctrl+I')
        loadManyAct.setStatusTip('Plot Many Coins')
        loadManyAct.triggered.connect(self.loadMany)

        aboutAct = QAction(QIcon('images/about.png'), '&About', self)
        aboutAct.setStatusTip('About')
        aboutAct.triggered.connect(self.dispAbout)

        self.autoupdateAct = QAction(QIcon('images/refresh.png'), '&Auto Update', self)
        self.autoupdateAct.setStatusTip('Auto Update')
        self.autoupdateAct.setChecked(True)
        self.autoupdateAct.triggered.connect(self.toggle_timeout)

        # MENUBAR
        self.menubar = self.menuBar()
        self.menubar.setNativeMenuBar(False)
        self.menubar.setStyleSheet("color: lightgrey")

        fileMenu = self.menubar.addMenu('&File')
        fileMenu.addAction(exitAct)

        viewMenu = self.menubar.addMenu('View')
        viewMenu.addAction(loadMultiAct)
        viewMenu.addAction(loadManyAct)

        settingsMenu = self.menubar.addMenu('&Settings')
        settingsMenu.addAction(customizeAct)
        settingsMenu.addAction(self.autoupdateAct)
        settingsMenu.addAction(toggledarklight)

        aboutMenu = self.menubar.addMenu('&About')
        aboutMenu.addAction(aboutAct)

        # TOOLBAR: define which actions will be shown in the toolbar
        self.toolbar = self.addToolBar('Control')
        self.toolbar.setStyleSheet(
            "QToolButton:hover {background-color: #444444} QToolBar {background: #595959; border: none}")
        self.toolbar.addAction(exitAct)
        self.toolbar.addAction(toggleViewAct)
        self.toolbar.addAction(customizeAct)
        self.toolbar.addAction(toggledarklight)

        self.page_layout = QVBoxLayout()
        page_widget = QWidget()
        page_widget.setLayout(self.page_layout)

        input_layout = QHBoxLayout()
        input_widget = QWidget()
        # input_widget.setStyleSheet("background-color: gainsboro")
        input_widget.setMaximumHeight(40)
        # input_widget.setContentsMargins(100, 0, 100, 0)
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
        self.comboBox1.setStyleSheet(
            "QComboBox{color: lightgrey; padding: 0px 18px 0px 3px;} QComboBox:!editable:off, QComboBox::drop-down:editable {background:#333333}")
        for list in self.all_coin_lists_names:
            self.comboBox1.addItem(list)
        self.comboBox1.activated[int].connect(self.listChoice)
        self.comboBox1.setCurrentIndex(self.coinListIndex)
        self.comboBox1.setMaximumWidth(200)
        input_layout.addWidget(self.comboBox1)
        self.comboBox2 = QComboBox(self)
        self.comboBox2.setStyleSheet(
            "QComboBox{color: lightgrey; padding: 0px 18px 0px 3px;} QComboBox:!editable:off, QComboBox::drop-down:editable {background:#333333}")
        for t in timeWords:
            self.comboBox2.addItem(t)
        self.comboBox2.activated[str].connect(self.timeChoice)
        self.comboBox2.setCurrentIndex(self.timeScale)
        self.comboBox2.setMaximumWidth(200)
        input_layout.addWidget(self.comboBox2)
        self.comboBox3 = QComboBox(self)
        self.comboBox3.setStyleSheet(
            "QComboBox{color: lightgrey; padding: 0px 18px 0px 3px;} QComboBox:!editable:off, QComboBox::drop-down:editable {background:#333333}")
        for curr in currencies:
            self.comboBox3.addItem(curr)
        self.comboBox3.activated[str].connect(self.currencyChoice)
        self.comboBox3.setCurrentText(self.currency)
        self.comboBox3.setMaximumWidth(200)
        input_layout.addWidget(self.comboBox3)

        # create a timer for auto-update of data
        self.timer0 = QTimer(self)
        self.timer0.timeout.connect(self.reload_graphs)

        if self.autoupdateAct.isChecked():
            self.timer0.start(self.timeout)

        # Create the Crypto Prices Plot in maptlotlib FigureCanvas object
        plot_layout = QVBoxLayout()
        self.CL = MplPriceChartsCanvas(self.coinList, width=12, height=4, dpi=100)
        self.growth_rates = self.CL.draw_plots(self.coinList, self.currency, self.timeScale, self.time, self.lim, self.view)
        plot_layout.addWidget(self.CL)
        plot_widget = QWidget()
        # plot_widget.setContentsMargins(0, 0, 0, 0)
        # plot_widget.setMinimumHeight(400)
        plot_widget.setLayout(plot_layout)

        # Create the Crypto price Growth Bar Chart in maptlotlib FigureCanvas object
        self.growth_plot_layout = QVBoxLayout()
        self.GL = MplGrowthCanvas(self.coinList, width=5, height=2, dpi=100)
        self.GL.draw_graph(self.growth_rates, self.coinList)
        self.growth_plot_layout.addWidget(self.GL)
        self.growth_plot_widget = QWidget()
        self.growth_plot_widget.setMaximumHeight(int(self.height / 4))
        self.growth_plot_widget.setLayout(self.growth_plot_layout)

        self.page_layout.addWidget(input_widget)
        self.page_layout.addWidget(plot_widget)
        self.page_layout.addWidget(self.growth_plot_widget)
        self.setCentralWidget(page_widget)

        self.show()

    def reload_graphs(self):
        # load all coins lists from file
        self.allCoins, self.all_coin_lists_names, self.all_coin_lists, self.all_coin_lists_dict = load_coin_lists()
        # current list
        try:
            self.coinList = self.all_coin_lists[self.coinListIndex]
        except:
            self.coinListIndex = 0
            self.coinList = self.all_coin_lists[self.coinListIndex]

        try:
            self.CL.fig.clf()
            self.GL.fig.clf()
        except AttributeError:
            pass
        self.growth_rates = self.CL.draw_plots(self.coinList, self.currency, self.timeScale, self.time, self.lim, self.view)
        self.GL.draw_graph(self.growth_rates, self.coinList)

    def listChoice(self, item):
        self.coinListIndex = item
        self.coinList = self.all_coin_lists[item]
        self.reload_graphs()

    def timeChoice(self, text):  # convert: "hour... year" to int value as defined in the index of timeWords array
        for i, t in enumerate(timeWords):
            if t == text:
                # myApp.timeout = 10000
                self.timeScale = i
                self.time = timeLimScale[i]
                self.lim = timeLim[i]
                self.reload_graphs()

    def currencyChoice(self, text):
        self.currency = text.strip()
        self.reload_graphs()

    def toggle_timeout(self, state):
        try:  # settings mode will have the timer deactivated
            if not state:
                self.timer0.stop()
            else:
                self.timer0.start(self.timeout)
        except Exception as e:
            print(e)

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def closeEvent(self, event):
        reply = QMessageBox.question(self, 'Message',
                                     "Are you sure to quit?", QMessageBox.Yes |
                                     QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()

    def loadMulti(self):
        self.view = 0
        self.reload_graphs()

    def loadMany(self):
        self.view = 1
        self.reload_graphs()

    def toggleView(self):
        if self.view == 0:
            self.view = 1
        else:
            self.view = 0
        self.reload_graphs()

    def load_customizer(self):
        if self.show_coinlist_editor:
            self.CustomView.setMaximumHeight(0)
            self.page_layout.removeWidget(self.CustomView)
            self.growth_plot_widget.setMaximumHeight(int(self.height / 4))
            self.show_coinlist_editor = False
            self.reload_graphs()
        else:
            self.growth_plot_widget.setMaximumHeight(0)
            self.CustomView = ListCustomizer(self.coinListIndex, dark_mode=self.dark_mode)
            self.CustomView.setContentsMargins(100,0,100,0)
            self.page_layout.addWidget(self.CustomView)
            self.show()
            self.show_coinlist_editor = True

    def switch_color_mode(self):
        # switch to LIGHT MODE
        if self.dark_mode == 1:
            self.dark_mode = False
            self.setStyleSheet("background-color: gainsboro")
            self.toolbar.setStyleSheet(
                "QToolButton:hover {background-color: darkgrey} QToolBar {background: gainsboro; border: none}")
            self.menubar.setStyleSheet("color: #333333")
            self.comboBox1.setStyleSheet(
                "QComboBox{color: #333333; padding: 0px 18px 0px 3px;} QComboBox:!editable:off, QComboBox::drop-down:editable {background:lightgrey}")
            self.comboBox2.setStyleSheet(
                "QComboBox{color: #333333; padding: 0px 18px 0px 3px;} QComboBox:!editable:off, QComboBox::drop-down:editable {background:lightgrey}")
            self.comboBox3.setStyleSheet(
                "QComboBox{color: #333333; padding: 0px 18px 0px 3px;} QComboBox:!editable:off, QComboBox::drop-down:editable {background:lightgrey}")
        # switch to DARK MODE
        else:
            self.setStyleSheet("background-color: #595959")
            self.toolbar.setStyleSheet(
                "QToolButton:hover {background-color: #444444} QToolBar {background: #595959; border: none}")
            self.menubar.setStyleSheet("color: lightgrey")
            self.comboBox1.setStyleSheet(
                "QComboBox{color: lightgrey; padding: 0px 18px 0px 3px;} QComboBox:!editable:off, QComboBox::drop-down:editable {background:#333333}")
            self.comboBox2.setStyleSheet(
                "QComboBox{color: lightgrey; padding: 0px 18px 0px 3px;} QComboBox:!editable:off, QComboBox::drop-down:editable {background:#333333}")
            self.comboBox3.setStyleSheet(
                "QComboBox{color: lightgrey; padding: 0px 18px 0px 3px;} QComboBox:!editable:off, QComboBox::drop-down:editable {background:#333333}")
            self.dark_mode = True

        # if editor mode is open switch its color mode
        if self.show_coinlist_editor:
            self.CustomView.switch_color_mode()

        # will always be called
        self.CL.switch_color_mode()
        self.GL.switch_color_mode()

        #
        self.CL.fig.canvas.draw()
        self.GL.fig.canvas.draw()

    def dispAbout(self):
        mes = 'Author: Fernando Garcia Winterling <html><br>GitHub: <a href = ""</a> <br>Data API: <a href = "https://min-api.cryptocompare.com/">CryptoCompare API</a></html>'
        QMessageBox.question(self, 'GUI Message', mes, QMessageBox.Ok, QMessageBox.Ok)


app = QtWidgets.QApplication(sys.argv)
w = MainWindow()
app.exec_()
