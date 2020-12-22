from PyQt5.QtWidgets import QComboBox, QLabel, QHBoxLayout, QVBoxLayout, QWidget, QPushButton, QSplitter, QListWidgetItem, QMessageBox, QInputDialog, QLineEdit
from PyQt5 import QtCore
from PyQt5.QtGui import QIcon, QPixmap, QImage, QColor

import json
import os
import requests

import matplotlib._color_data as mcd

from list_widget import ThumbListWidget


########################
##  Helper functions  ##
########################

def check_color(color_name):
    if color_name in mcd.CSS4_COLORS:
        return True
    else:
        return False


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


# load all coin list from config files
def load_coin_lists_from_file():
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


##################
#  EDITOR CLASS  #
##################

class CoinListEditor(QWidget):

    def __init__(self, parent, coinListIndex, dark_mode=True):

        super().__init__()
        self.parent = parent

        self.coinListIndex = coinListIndex

        # read all coin lists from file
        self.allCoins, self.all_coin_lists_names, self.all_coin_lists, self.all_coin_lists_dict = load_coin_lists_from_file()
        self.coinList = self.all_coin_lists[self.coinListIndex]

        # get con infos top 150 by volume
        self.all_coin_infos = get_top_coins(100)

        self.dark_mode = dark_mode

        self.initUI()

    def initUI(self):

        myQWidget = QWidget()

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
        self.listWidgetA.setAcceptDrops(True)
        for coin in self.allCoins:
            item = QListWidgetItem(coin, self.listWidgetA)
        self.listWidgetB = ThumbListWidget(self)
        self.listWidgetB.setAcceptDrops(True)
        self.listWidgetB.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        #self.listWidgetB.setAlternatingRowColors (True)
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
        self.coin_logo.setMinimumSize(140,140)
        # create empty Pixmap
        # self.coin_logo.setPixmap(empty_pixmap)
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
                try:
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
                except Exception as e:
                    print(f"Error retrieving coin infos ({e})")

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
        with open('all_coins_colors.txt', 'w') as outfile:
            json.dump(self.allCoins, outfile)
        self.allCoins, self.all_coin_lists_names, self.all_coin_lists, self.all_coin_lists_dict = load_coin_lists_from_file()

    def add_coin_color_to_list(self):  # add/modify coin color and save it to master list
        current_coin = self.listWidgetA.currentItem().text()
        # open dialog
        possible_colors = mcd.CSS4_COLORS
        text, okPressed = QInputDialog.getItem(self, "Get item", "Color:", possible_colors, 3, False)

        if okPressed and text != '':
            current_coin_color = text
            # check if color is accepted by matplotlib
            # retrieve current coins from editing list, covert to dict and add coresponding colors found in allCoins
            new_entry = {current_coin: current_coin_color}
            self.allCoins.update(new_entry)
            # overwrite current master file
            with open('all_coins_colors.txt', 'w') as outfile:
                json.dump(self.allCoins, outfile)
            QMessageBox.question(self, 'GUI Message', "Coin and color updated in master list ", QMessageBox.Ok)
            with open('coin_lists.txt') as json_file:
                clist_data = json.load(json_file)
                for clist in clist_data:
                    print(clist_data[clist])
                    if current_coin in clist_data[clist]:
                        clist_data[clist][current_coin] = current_coin_color
                        print(f"Coin color set in coinlist {clist} custom coinlists file")

            self.allCoins, self.all_coin_lists_names, self.all_coin_lists, self.all_coin_lists_dict = load_coin_lists_from_file()

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
            self.allCoins, self.all_coin_lists_names, self.all_coin_lists, self.all_coin_lists_dict = load_coin_lists_from_file()
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
                self.allCoins, self.all_coin_lists_names, self.all_coin_lists, self.all_coin_lists_dict = load_coin_lists_from_file()

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
            self.allCoins, self.all_coin_lists_names, self.all_coin_lists, self.all_coin_lists_dict = load_coin_lists_from_file()

            self.parent.reload_coinlist_files()
            self.parent.refresh_data_and_graphs()

    def set_color_mode(self, dark_mode):
        if dark_mode:
            self.listWidgetA.setStyleSheet("""QListWidget{background: #595959;} QListWidget::item:selected { background: #444444}""")
            self.listWidgetB.setStyleSheet("""QListWidget{background: #595959;} QListWidget::item:selected { background: #444444}""")
            self.dark_mode = True
        else:
            self.listWidgetA.setStyleSheet("""QListWidget{background: gainsboro;} QListWidget::item:selected { background: lightgrey}""")
            self.listWidgetB.setStyleSheet("""QListWidget{background: gainsboro;} QListWidget::item:selected { background: lightgrey}""")
            self.dark_mode = False
