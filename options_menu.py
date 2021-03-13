from PyQt5.QtWidgets import QComboBox, QLabel, QHBoxLayout, QWidget
import json

#################################
##### PARAM SELECTOR CLASS ######
#################################

baseCurrencies = ['EUR', 'USD', 'BTC', 'ETH']
timeWords = ['1-hour', '1-day', '1-week', '1-month', '3-months', '6-months', '1-year']
timeLim = [60, 1440, 168, 720, 90, 180, 365]
timeLimScale = ['minute', 'minute', 'hour', 'hour', 'day', 'day', 'day']

# load all coin list from config files
def load_coin_lists():
    # load all coins lists
    with open('all_coins_colors.txt') as json_file:
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


class ParameterSelector(QWidget):

    def __init__(self, coinListIndex, parent=None, dark_mode=True):

        #super().__init__()
        super(ParameterSelector, self).__init__(parent)
        self.parent = parent

        self.dark_mode = dark_mode

        # read all coin lists from file
        self.coinListIndex = coinListIndex
        self.allCoins, self.all_coin_lists_names, self.all_coin_lists, self.all_coin_lists_dict = load_coin_lists()
        self.coinList = self.all_coin_lists[self.coinListIndex]

        self.currency = 'EUR'
        self.timeScale = 1

        self.initUI()

    def initUI(self):

        # load all coins lists from file
        self.allCoins, self.all_coin_lists_names, self.all_coin_lists, self.all_coin_lists_dict = load_coin_lists()
        self.coinList = self.all_coin_lists[self.coinListIndex]

        input_layout = QHBoxLayout()
        input_widget = QWidget()
        input_widget.setMaximumHeight(40)
        input_widget.setLayout(input_layout)

        # drop down menus
        self.comboBox1 = QComboBox(self)
        self.comboBox1.setStyleSheet(
            "QComboBox{color: lightgrey; padding: 0px 18px 0px 3px;} QComboBox:!editable:off, QComboBox::drop-down:editable {background:#333333}")
        for list in self.all_coin_lists_names:
            self.comboBox1.addItem(list)
        self.comboBox1.activated[int].connect(self.listChoice)
        self.comboBox1.setCurrentIndex(self.coinListIndex)
        self.comboBox1.setMaximumWidth(200)
        self.comboBox1.setMinimumWidth(90)
        input_layout.addWidget(self.comboBox1)
        self.comboBox2 = QComboBox(self)
        self.comboBox2.setStyleSheet(
            "QComboBox{color: lightgrey; padding: 0px 18px 0px 3px;} QComboBox:!editable:off, QComboBox::drop-down:editable {background:#333333}")
        for t in timeWords:
            self.comboBox2.addItem(t)
        self.comboBox2.activated[str].connect(self.timeChoice)
        self.comboBox2.setCurrentIndex(self.timeScale)
        self.comboBox2.setMaximumWidth(200)
        self.comboBox2.setMinimumWidth(90)
        input_layout.addWidget(self.comboBox2)
        self.comboBox3 = QComboBox(self)
        self.comboBox3.setStyleSheet(
            "QComboBox{color: lightgrey; padding: 0px 18px 0px 3px;} QComboBox:!editable:off, QComboBox::drop-down:editable {background:#333333}")
        for curr in baseCurrencies:
            self.comboBox3.addItem(curr)
        self.comboBox3.activated[str].connect(self.currencyChoice)
        self.comboBox3.setCurrentText(self.currency)
        self.comboBox3.setMaximumWidth(200)
        self.comboBox3.setMinimumWidth(90)
        input_layout.addWidget(self.comboBox3)

        self.setLayout(input_layout)
        self.show()

    def listChoice(self, item):
        self.coinListIndex = item
        self.coinList = self.all_coin_lists[item]
        self.parent.coinListIndex = item
        self.parent.coinList = self.all_coin_lists[item]
        self.parent.refresh_data_and_graphs()

    def timeChoice(self, text):  # convert: "hour... year" to int value as defined in the index of timeWords array
        for i, t in enumerate(timeWords):
            if t == text:
                # myApp.timeout = 10000
                self.timeScale = i
                self.time = timeLimScale[i]
                self.lim = timeLim[i]
                self.parent.timeScale = i
                self.parent.time = timeLimScale[i]
                self.parent.lim = timeLim[i]
                self.parent.refresh_data_and_graphs()
                break;

    def currencyChoice(self, text):
        self.currency = text.strip()
        self.parent.currency = text.strip()
        self.parent.refresh_data_and_graphs()

    def set_color_mode(self, dark_mode):
        # switch to DARK MODE
        if dark_mode:
            self.comboBox1.setStyleSheet(
                "QComboBox{color: lightgrey; padding: 0px 18px 0px 3px;} QComboBox:!editable:off, QComboBox::drop-down:editable {background:#333333}")
            self.comboBox2.setStyleSheet(
                "QComboBox{color: lightgrey; padding: 0px 18px 0px 3px;} QComboBox:!editable:off, QComboBox::drop-down:editable {background:#333333}")
            self.comboBox3.setStyleSheet(
                "QComboBox{color: lightgrey; padding: 0px 18px 0px 3px;} QComboBox:!editable:off, QComboBox::drop-down:editable {background:#333333}")
            self.dark_mode = True
        else:
            self.comboBox1.setStyleSheet(
                "QComboBox{color: #333333; padding: 0px 18px 0px 3px;} QComboBox:!editable:off, QComboBox::drop-down:editable {background:lightgrey}")
            self.comboBox2.setStyleSheet(
                "QComboBox{color: #333333; padding: 0px 18px 0px 3px;} QComboBox:!editable:off, QComboBox::drop-down:editable {background:lightgrey}")
            self.comboBox3.setStyleSheet(
                "QComboBox{color: #333333; padding: 0px 18px 0px 3px;} QComboBox:!editable:off, QComboBox::drop-down:editable {background:lightgrey}")
            self.dark_mode = False
