import sys
import requests
import datetime as dt
import json
import asyncio
import concurrent.futures

from PyQt5.QtWidgets import QAction, qApp, QMessageBox, QDesktopWidget, QVBoxLayout, QWidget
from PyQt5.QtGui import QIcon, QColor
from PyQt5.QtCore import QTimer
from PyQt5 import QtWidgets

from options_menu import ParameterSelector
from mpl_price_charts import MplPriceChartsCanvas, MplGrowthCanvas, MplCorrelationCanvas
from coinlist_editor import CoinListEditor

########################
##  Global variables  ##
########################

# API url
PRICE_URL = "https://min-api.cryptocompare.com/data/histo"

baseCurrencies = ['EUR', 'USD', 'BTC', 'ETH']
timeWords = ['1-hour', '1-day', '1-week', '1-month', '3-months', '6-months', '1-year']
timeLim = [60, 1440, 168, 720, 90, 180, 365]
timeLimScale = ['minute', 'minute', 'hour', 'hour', 'day', 'day', 'day']

# custom colors
BG_COL_D = "#595959"
FACE_COL_D = "#333333"

BG_COL_L = "gainsboro"
FACE_COL_L = "lightgrey"

TITLE_COL = "k"
GRID_COL = "grey"

custom_colors = {"BG_COL_D":"#595959", "FACE_COL_D":"#333333", "BG_COL_L":"gainsboro", "FACE_COL_L":"lightgrey", "TITLE_COL":"k", "GRID_COL":"grey"}

# auto refresh timeout
UPDATE_TIMEOUT = 300000 # 5 min

########################
##  Helper functions  ##
########################


def getScreenRes():
    screen_resolution = app.desktop().screenGeometry()
    width, height = screen_resolution.width(), screen_resolution.height()
    return width, height

def load_coin_lists_from_file():
    # load all coins lists
    with open('all_coins_colors.txt') as json_file:
        allCoins = json.load(json_file)
    # load coinList names and data
    all_coin_lists = []
    try:
        with open('coin_lists.txt') as json_file:
            clist_data = json.load(json_file)
        for listname in clist_data:
            all_coin_lists.append(clist_data[listname])
        print(f"{get_time_now()}: config files loaded")
    except Exception:
        print(f"{get_time_now()}: ERROR loading config files!")
    return allCoins, all_coin_lists


### ASYNCIO MAGIC for concurrent http requests, use with caution, may trigger API limits ###
loop = asyncio.get_event_loop()

async def main(currency, time, lim, coinList):
    price_data = []
    price_data_dict = dict.fromkeys(coinList.keys())
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [loop.run_in_executor(None, get_ticker_prices, coin, currency, time, lim) for coin in coinList]
        for response in await asyncio.gather(*futures):
            price_data.append(response)

    for index, coin in enumerate(price_data_dict):
        price_data_dict[coin] = price_data[index]
    return price_data_dict


# Cryptocompare API wrapper
def get_ticker_prices(ticker='BTC', currency='USD', time='minute', lim=60):
    # build URL and call api
    fullURL = PRICE_URL + time + '?fsym=' + ticker + '&tsym=' + currency + '&limit=' + str(lim)
    try:
        r = requests.get(fullURL)
        tickerData = r.json()
        priceData = tickerData["Data"]
        return priceData
    except Exception as e:
        print(e)
        priceData = {}
        return priceData


# PRE: an array of floats
# POST: returns % change between sum of first three vs sum of last three items
def calc_growth_percentage(prices):
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

# PRE: 
# POST: returns an array of % changes
def calc_growth_rates(coinList, all_price_data):
    growth_rates = []
    for coin in coinList:
        price_data = all_price_data[coin]
        prices = []
        for data in price_data:
            prices.append(data["close"])
        # calculate growth rates
        changePct = calc_growth_percentage(prices)
        growth_rates.append(changePct)
    return growth_rates

# returns current date and time DD-MM-YY HH:MM:SS
def get_time_now():
    now = dt.datetime.now()
    return now.strftime('%d-%m-%Y %H:%M:%S')


########################
##### MAIN CLASS #######
########################

class CryptoGui(QtWidgets.QMainWindow):

    def __init__(self, *args, **kwargs):
        super(CryptoGui, self).__init__(*args, **kwargs)
        self.title = 'Crypto Browser'
        self.canvas_color = custom_colors["BG_COL_D"]
        self.setStyleSheet("background-color: {}".format(self.canvas_color))

        screen_width, screen_height = getScreenRes()
        self.width = int(screen_width / 2)
        self.height = int(screen_height / 3 * 2)

        self.currency = 'EUR'
        self.coinListIndex = 0

        self.timeScale = 1
        self.lim = timeLim[self.timeScale]
        self.time = timeLimScale[self.timeScale]

        self.dark_mode = True  # light = 0, dark = 1
        self.vertical = False

        self.show_growth_rates_view = False
        self.show_coinlist_editor_view = False  # flag that enables list customizer
        self.show_correlations_view = False
        self.show_indexed_view = False

        self.timeout = UPDATE_TIMEOUT

        self.all_price_data = []
        self.growth_rates = []

        self.initUI()


    def initUI(self):

        # Window Geometry
        # self.setStyleSheet("background-color: gainsboro")
        self.setGeometry(self.width, 0, self.width, self.height) #width*2 > window will be displayed on secondary monitor
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

        toggleViewBars = QAction(QIcon('images/bars.png'), '&Toggle Growth Rates View', self)
        toggleViewBars.setShortcut('Ctrl+T')
        toggleViewBars.setStatusTip('toggle view')
        toggleViewBars.triggered.connect(self.toggle_growth_rates_view)

        toggleViewIndexed = QAction(QIcon('images/plot.png'), '&Toggle Price Chart View', self)
        toggleViewIndexed.setShortcut('Ctrl+I')
        toggleViewIndexed.setStatusTip('toggle view')
        toggleViewIndexed.triggered.connect(self.toggle_indexed_view)

        toggledarklight = QAction(QIcon('images/bulb.png'), '&Toggle Dark Mode', self)
        toggledarklight.setShortcut('Ctrl+D')
        toggledarklight.setStatusTip('toggle light/dark mode')
        toggledarklight.triggered.connect(self.switch_color_mode)

        customizeAct = QAction(QIcon('images/settings.png'), '&Coin-Lists Editor', self)
        customizeAct.setShortcut('Ctrl+C')
        customizeAct.setStatusTip('Settings')
        customizeAct.triggered.connect(self.toggle_coinlist_editor_view)

        refreshDataAct = QAction(QIcon('images/refresh.png'), '&Refresh Data and Graphs', self)
        refreshDataAct.setShortcut('Ctrl+R')
        refreshDataAct.setStatusTip('Refresh Data')
        refreshDataAct.triggered.connect(self.refresh_data_and_graphs)

        toggleViewCorr = QAction(QIcon('images/correlation.png'), '&Show / Hide Correlations', self)
        toggleViewCorr.setShortcut('Ctrl+C')
        toggleViewCorr.setStatusTip('Correlations')
        toggleViewCorr.triggered.connect(self.toggle_correlations_view)

        toggle_landscape = QAction(QIcon('images/size.png'), '&Toggle Portrait / Landscape mode', self)
        toggle_landscape.setShortcut('Ctrl+Z')
        toggle_landscape.setStatusTip('Resize')
        toggle_landscape.triggered.connect(self.switch_vertical_mode)

        aboutAct = QAction(QIcon('images/about.png'), '&About', self)
        aboutAct.setStatusTip('About')
        aboutAct.triggered.connect(self.dispAbout)

        self.autoupdateAct = QAction(QIcon('images/refresh.png'), '&Auto Update', self, checkable=True)
        self.autoupdateAct.setStatusTip('Auto Update')
        self.autoupdateAct.setChecked(True)
        self.autoupdateAct.triggered.connect(self.toggle_timeout)

        # MENUBAR
        self.menubar = self.menuBar()
        self.menubar.setNativeMenuBar(False)
        # self.menubar.setStyleSheet("color: lightgrey")
        #self.menubar.setStyleSheet("QMenuBar{background-color: transparent}; QMenuBar::item{color: white; margin-top: 4px; spacing: 3px; padding: 1px 10px; background: transparent; border - radius: 4px}; QMenuBar::item: hover{background: blue; color: red;}")
        self.menubar.setStyleSheet("QMenuBar{color: lightgrey}")

        fileMenu = self.menubar.addMenu('&File')
        fileMenu.addAction(exitAct)

        viewMenu = self.menubar.addMenu('View')
        viewMenu.addAction(toggleViewIndexed)
        viewMenu.addAction(toggleViewBars)
        viewMenu.addAction(toggleViewCorr)

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
        self.toolbar.addAction(toggleViewIndexed)
        self.toolbar.addAction(toggleViewBars)
        self.toolbar.addAction(toggleViewCorr)
        self.toolbar.addAction(customizeAct)
        self.toolbar.addAction(refreshDataAct)
        self.toolbar.addAction(toggledarklight)
        self.toolbar.addAction(toggle_landscape)

        # create a timer for auto-update of data
        self.timer0 = QTimer(self)
        self.timer0.timeout.connect(self.refresh_data_and_graphs)

        if self.autoupdateAct.isChecked():
            self.timer0.start(self.timeout)

        # Load coin data
        # read all coin lists from file
        self.allCoins, self.all_coin_lists = load_coin_lists_from_file()
        #current master coinlist
        self.coinList = self.all_coin_lists[self.coinListIndex]


        # MAIN LAYOUT
        self.page_layout = QVBoxLayout()
        page_widget = QWidget()
        page_widget.setLayout(self.page_layout)

        # Create drop down menus that select data parameters
        self.ParamInputWidget = ParameterSelector(self.coinListIndex, parent=self)
        self.ParamInputWidget.setMaximumHeight(40)

        # fetch new data from API
        self.all_price_data = self.fetch_price_data(self.currency, self.time, self.lim, self.coinList)
        self.growth_rates = calc_growth_rates(self.coinList, self.all_price_data)

        # Create the Crypto Prices Plot in maptlotlib FigureCanvas object
        self.PriceChartCanvas = MplPriceChartsCanvas(self.coinList, width=12, height=4, dpi=100)
        self.PriceChartCanvas.draw_plots(self.coinList, self.currency, self.timeScale, self.time, self.lim, self.all_price_data)

        # show the price Growth Bar Chart in maptlotlib FigureCanvas object
        self.toggle_growth_rates_view()

        # add widgets to page layout
        self.page_layout.addWidget(self.ParamInputWidget)
        # self.page_layout.addWidget(self.plot_widget)
        self.page_layout.addWidget(self.PriceChartCanvas)
        # self.page_layout.addWidget(self.growth_rates_view_widget)
        self.page_layout.addWidget(self.GrowthRatesWidget)
        self.setCentralWidget(page_widget)

        self.show()


    def toggle_timeout(self, state):
        try:
            if not state:
                self.timer0.stop()
            else:
                self.timer0.start(self.timeout)
        except Exception as e:
            print(e)
        print(f"AutoUpdate data set to: {state}")

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


    # reload data from API and reloads the currently displayed graphs
    def refresh_data_and_graphs(self):
        self.all_price_data = self.fetch_price_data(self.currency, self.time, self.lim, self.coinList)
        self.growth_rates = calc_growth_rates(self.coinList, self.all_price_data)
        self.redraw_graphs()

    # toggles between individual price charts (one for each coin) and one big indexed plot (all coins indexed to 100)
    def toggle_indexed_view(self):
        if self.show_indexed_view:
            self.show_indexed_view = False
        else:
            self.show_indexed_view = True
        self.redraw_graphs()

    # shows growth rates bar graph in the secondary graph frame
    # show state variable will be inverted
    def toggle_growth_rates_view(self):
        if self.show_growth_rates_view:
            self.show_growth_rates_view = False
            self.GrowthRatesWidget.setParent(None)
            self.redraw_graphs()
        else:
            if self.show_coinlist_editor_view:
                self.toggle_coinlist_editor_view()
            if self.show_correlations_view:
                self.toggle_correlations_view()
            self.show_growth_rates_view = True
            self.GrowthRatesWidget = MplGrowthCanvas(self.coinList, dark_mode=self.dark_mode, width=5, height=2, dpi=100)
            self.GrowthRatesWidget.setMaximumHeight(int(self.height / 3))
            self.GrowthRatesWidget.draw_graph(self.growth_rates, self.coinList)
            self.page_layout.addWidget(self.GrowthRatesWidget)
            self.GrowthRatesWidget.set_color_mode(self.dark_mode)
        self.show()

    def toggle_correlations_view(self):
        if self.show_correlations_view:
            self.show_correlations_view = False
            self.CorrelationsWidget.setParent(None)
            self.redraw_graphs()
        else:
            if self.show_growth_rates_view:
                self.toggle_growth_rates_view()
            if self.show_coinlist_editor_view:
                self.toggle_coinlist_editor_view()
            self.show_correlations_view = True
            self.CorrelationsWidget = MplCorrelationCanvas(self.coinList, dark_mode=self.dark_mode, width=5, height=2, dpi=100)
            self.CorrelationsWidget.setMinimumHeight(int(self.height / 2))
            self.CorrelationsWidget.draw_graph(self.coinList, self.all_price_data)
            self.page_layout.addWidget(self.CorrelationsWidget)
        self.show()


    def toggle_coinlist_editor_view(self):
        if self.show_coinlist_editor_view:
            # self.page_layout.removeWidget(self.CoinListEditorWidget)
            self.CoinListEditorWidget.setParent(None)
            self.show_coinlist_editor_view = False
        else:
            # show editor mode, hide growth rates view if needed
            if self.show_growth_rates_view:
                self.toggle_growth_rates_view()
            if self.show_correlations_view:
                self.toggle_correlations_view()
            self.CoinListEditorWidget = CoinListEditor(self, self.coinListIndex, dark_mode=self.dark_mode)
            self.CoinListEditorWidget.set_color_mode(self.dark_mode)
            self.CoinListEditorWidget.setMinimumHeight(int(self.height / 2))
            self.CoinListEditorWidget.setContentsMargins(100, 0, 100, 0)
            self.page_layout.addWidget(self.CoinListEditorWidget)
            self.show_coinlist_editor_view = True
            self.CoinListEditorWidget.set_color_mode(self.dark_mode)
        self.show()


    def fetch_price_data(self, currency, time, lim, coinList):
        print(f"{get_time_now()}: fetching new data from API")
        all_price_data = loop.run_until_complete(main(currency, time, lim, coinList))
        return all_price_data


    def reload_coinlist_files(self):
        # load all coins lists from file
        self.allCoins, self.all_coin_lists = load_coin_lists_from_file()
        # set current coin list
        self.coinList = self.all_coin_lists[self.coinListIndex]


    def redraw_graphs(self):
        # clear previous figures
        if self. show_growth_rates_view:
            self.GrowthRatesWidget.fig.clf()
            self.GrowthRatesWidget.draw_graph(self.growth_rates, self.coinList)
        if self.show_correlations_view:
            self.CorrelationsWidget.fig.clf()
            self.CorrelationsWidget.draw_graph(self.coinList, self.all_price_data, dark_mode=self.dark_mode)
            self.CorrelationsWidget.fig.canvas.draw()

        # is always present so we clear it directly
        self.PriceChartCanvas.fig.clf()
        # redraw price charts
        if self.show_indexed_view:
            self.PriceChartCanvas.draw_indexed_plots(self.coinList, self.currency, self.timeScale, self.time, self.lim, self.all_price_data)
        else:
            self.PriceChartCanvas.draw_plots(self.coinList, self.currency, self.timeScale, self.time, self.lim,
                                             self.all_price_data, vertical_mode=self.vertical)
        self.PriceChartCanvas.set_color_mode(self.dark_mode)

    def switch_color_mode(self):
        if self.dark_mode:
            self.dark_mode = False
        else:
            self.dark_mode = True

        # main window color
        self.set_color_mode(self.dark_mode)

        # if growth rates , editor, ... modes are open switch their color modes
        if self.show_growth_rates_view:
            self.GrowthRatesWidget.set_color_mode(self.dark_mode)

        if self.show_coinlist_editor_view:
            self.CoinListEditorWidget.set_color_mode(self.dark_mode)
            
        if self.show_correlations_view:
            self.CorrelationsWidget.set_color_mode(self.dark_mode)

        # will always be called (as there always will be a PriceChartCanvas as well as the input widgets (for now)
        self.PriceChartCanvas.set_color_mode(self.dark_mode)
        self.ParamInputWidget.set_color_mode(self.dark_mode)

        # redraw canvas
        #self.PriceChartCanvas.fig.canvas.update()
        self.PriceChartCanvas.fig.canvas.draw()


    def set_color_mode(self, dark_mode):
        if dark_mode:
            self.setStyleSheet("background-color: #595959")
            self.toolbar.setStyleSheet(
                "QToolButton:hover {background-color: #444444} QToolBar {background: #595959; border: none}")
            self.menubar.setStyleSheet("QMenuBar{color: lightgrey}")
        else:
            self.setStyleSheet("background-color: gainsboro")
            self.toolbar.setStyleSheet(
                "QToolButton:hover {background-color: darkgrey} QToolBar {background: gainsboro; border: none}")
            self.menubar.setStyleSheet("QMenuBar{color: #333333}")


    def dispAbout(self):
        mes = 'Author: ferbcn <html><br>GitHub: <a href = ""</a> <br>Data API: <a href = "https://min-api.cryptocompare.com/">CryptoCompare API</a></html>'
        QMessageBox.question(self, 'GUI Message', mes, QMessageBox.Ok, QMessageBox.Ok)


    def switch_vertical_mode(self):
        if self.vertical:
            self.width *= 4
            self.height /= 2
            self.setGeometry(self.width, 0, self.width, self.height)
            self.vertical = False
        else:
            self.width /= 4
            self.height *= 2
            self.setGeometry(self.width*7, 0, self.width, self.height)
            self.vertical = True
        self.redraw_graphs()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    w = CryptoGui()
    app.exec_()
