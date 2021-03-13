from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import math
import numpy as np
import datetime as dt
from scipy.stats import linregress

import matplotlib.dates as mdates
import matplotlib.artist as marts
from matplotlib.colors import LinearSegmentedColormap

# custom colors
# dark mode
BG_COL_D = "#595959"
FACE_COL_D = "#333333"

# light mode
BG_COL_L = "gainsboro"
FACE_COL_L = "lightgrey"

# other colors
TITLE_COL = "k"
GRID_COL = "grey"


# HELPER FUNCTIONS

# adjust grid structure depending on number of items to show (hacky)
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
        self.face_color = FACE_COL_D

        self.fig.set_facecolor(self.bg_color)

        self.coin_list = current_coin_list
        self.growth_rates = []
        self.all_price_data = []


    def draw_plots(self, coin_list, currency, timeScale, time, lim, all_price_data, vertical_mode=False):

        self.sub_plots = []

        # reset array where growth rates are calculated
        self.growth_rates = []

        agregated_volumes = [0 for _ in range(lim+1)]

        if vertical_mode:
            col = 1
            row = len(coin_list)
        else:
            row, col = make_grid(coin_list)
        pl = 1  # sublots counter

        for coin in coin_list:
            # flag cases with wrong or missing data
            draw_current_coin = True

            # draw current sublot
            sub_plt = self.fig.add_subplot(row, col, pl)
            self.sub_plots.append(sub_plt)
            if not vertical_mode:
                sub_plt.set_title(coin, color='#000000', size='small')
            sub_plt.tick_params(axis='both', which='major', labelsize=6, labelcolor='#000000')
            pl += 1
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

                sub_plt.set_facecolor(self.face_color)
                sub_plt.xaxis.grid(color=GRID_COL, linestyle='dashed')
                sub_plt.yaxis.grid(color=GRID_COL, linestyle='dashed')

                # drawing the plot
                sub_plt.plot(times, prices, color=coin_list[coin])
                sub_plt.set_facecolor(self.face_color)

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

                # draw plot for current coin
                if draw_current_coin:
                    sub_plt.plot(times, prices, color=coin_list[coin])

                sub_plt.set_facecolor(self.face_color)
                sub_plt.xaxis.grid(color=GRID_COL, linestyle='dashed')
                sub_plt.yaxis.grid(color=GRID_COL, linestyle='dashed')
                # sub_plt.tick_params(axis='y', labelcolor=color)

                if vertical_mode:
                    sub_plt.xaxis.label.set_fontsize('xx-small')
                else:
                    sub_plt.xaxis.label.set_fontsize('small')

                try:
                    price_info = 'Low: {} - High: {} - Last: {}'.format(min(prices), max(prices), prices[lim-1])
                except ValueError:
                    price_info = 'n/a'
                sub_plt.set(xlabel=price_info, facecolor='#3a3a3a', xticklabels=[])

                # draw volumes on secondary axis
                ax2 = sub_plt.twinx()
                ax2.fill_between(times, 0, volumes, facecolor='#000000', alpha=0.3)
                ax2.axis('off')
            # END OF COIN LOOP

        # format time axis
        for sp in self.sub_plots:
            self.format_xaxis(sp, timeScale)

        # update figure
        self.fig.tight_layout(h_pad=1)
        self.fig.canvas.draw()



    def draw_indexed_plots(self, coin_list, currency, timeScale, time, lim, all_price_data):

        self.sub_plots = []

        # reset array where growth rates are calculated
        self.growth_rates = []

        agregated_volumes = [0 for _ in range(lim+1)]

        sub_plt = self.fig.add_subplot(111)
        self.sub_plots.append(sub_plt)
        sub_plt.set_title("Indexed Crypto Prices", color='#000000', size='medium')
        sub_plt.xaxis.label.set_fontsize('x-small')
        sub_plt.tick_params(axis='both', which='major', labelsize=6, labelcolor='#000000')

        for coin in coin_list:
            # flag cases with wrong or missing data
            draw_current_coin = True

            # extract prices for current coin from all_price_data
            price_data = all_price_data[coin]
            prices = []
            times = []
            volumes = []

            # mambojambo to catch special case: coin == base currency (no data provided by api)
            # write prices/volumes (with 1.0) and date/times created manually avoiding exceptions and ugly graphs further down
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

                # indexed mode -> we need to index all prices
                base = prices[0]
                for i in range(len(prices)):
                    prices[i] = prices[i] / base * 100

                # drawing the plot
                sub_plt.plot(times, prices, color=coin_list[coin])
                #sub_plt.set_facecolor(self.face_color)

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

                # indexed mode -> we need to index all prices
                try:
                    try:
                        base = prices[0]
                    except IndexError:
                        base = 0
                    for i in range(len(prices)):
                        prices[i] = prices[i] / base * 100
                except ZeroDivisionError:
                    draw_current_coin = False

                # draw plot for current coin
                if draw_current_coin:
                    sub_plt.plot(times, prices, color=coin_list[coin])

                # sub_plt.tick_params(axis='y', labelcolor=color)

        # END OF COIN LOOP
        sub_plt.set_facecolor(self.face_color)
        sub_plt.xaxis.grid(color=GRID_COL, linestyle='dashed')
        sub_plt.yaxis.grid(color=GRID_COL, linestyle='dashed')

        if draw_current_coin:
            ax2 = sub_plt.twinx()
            ax2.fill_between(times, 0, agregated_volumes, facecolor='#000000', alpha=0.3)
            ax2.axis('off')

        self.format_xaxis(sub_plt, timeScale)

        # update figure
        self.fig.tight_layout(h_pad=1)
        self.fig.canvas.draw()

    # custom formatter for date labels in x-axis
    def format_xaxis(self, plt, timeScale):
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


    def set_color_mode(self, dark_mode):
        if dark_mode:
            self.fig.set_facecolor(BG_COL_D)
            for plot in self.sub_plots:
                plot.set_facecolor(FACE_COL_D)
            self.face_color = FACE_COL_D
        else:
            self.fig.set_facecolor(BG_COL_L)
            for plot in self.sub_plots:
                plot.set_facecolor(FACE_COL_L)
            self.face_color = FACE_COL_L


class MplGrowthCanvas(FigureCanvasQTAgg):

    def __init__(self, current_coin_list, dark_mode=True, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super(MplGrowthCanvas, self).__init__(self.fig)

        self.dark_mode = dark_mode
        self.bg_color = BG_COL_D
        self.face_color = FACE_COL_D

        self.fig.set_facecolor(self.bg_color)
        self.coin_list = current_coin_list

    # draws a bar graph given an input of GR (array) and coinList (dictionary)
    def draw_graph(self, growth_rates, coinList):
        ind = [n for n in range(len(coinList))]
        width = 0.5  # the width of the bars
        self.axBar = self.fig.add_subplot(111)
        self.rects = self.axBar.bar(ind, growth_rates, width, color=list(coinList.values()))

        self.axBar.set_facecolor(self.face_color)
        self.axBar.set_axisbelow(True)
        self.axBar.set_ylabel('Growth in %', color='#000000', size='x-small')
        #self.axBar.set_title('Change in %', color='#000000', size='small')
        self.axBar.set_xticks(ind)
        self.axBar.tick_params(axis='both', which='major', labelsize=6, labelcolor='#000000')
        self.axBar.yaxis.grid(color=GRID_COL, linestyle='dashed')

        xLabels = coinList.keys()
        self.axBar.set_xticklabels(xLabels, color='#000000', size='small')

        # put labels on the graphs
        for rect in self.rects:
            height = rect.get_height()
            self.axBar.text(rect.get_x() + rect.get_width() / 2., 1.0 * height, "%.1f" % float(height), ha='center',
                            va='bottom', size='small')
        # update figure
        self.fig.canvas.draw()

    def set_color_mode(self, dark_mode):
        if dark_mode:
            self.fig.set_facecolor('#595959')
            self.axBar.set_facecolor('#333333')
        else:
            self.fig.set_facecolor('gainsboro')
            self.axBar.set_facecolor('lightgrey')
        self.fig.canvas.draw()

class MplCorrelationCanvas(FigureCanvasQTAgg):

    def __init__(self, current_coin_list, dark_mode=True, width=5, height=4, dpi=100):
        self.bg_color = BG_COL_D
        self.face_color = FACE_COL_D
        self.dark_mode = dark_mode

        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super(MplCorrelationCanvas, self).__init__(self.fig)

        self.fig.set_facecolor(self.bg_color)
        self.coin_list = current_coin_list

    # draws a correlation matrix
    def draw_graph(self, coinList, price_data, dark_mode=True):
        priceDict = {}
        for coin in coinList:
            prices = []
            for data in price_data[coin]:
                prices.append(data["close"])
            priceDict[coin] = prices
        l = len(coinList)
        corrMatrix = [[0 for x in range(l)] for y in range(l)]
        for i, coin1 in enumerate(priceDict):
            for p, coin2 in enumerate(priceDict):
                if p > i:
                    rvalue = 0.0
                elif coin1 == coin2:
                    rvalue = 1.0
                else:
                    a = priceDict[coin1]
                    b = priceDict[coin2]
                    try:
                        lr = linregress(a, b)
                        rvalue = lr.rvalue
                    except ValueError:
                        rvalue = 0
                corrMatrix[i][p] = rvalue

        # plot correlation heatmap
        self.ax = self.fig.add_subplot(111)
        self.ax.set_title('Crypto Correlations Matrix', size='medium')

        # convert tu numpy array
        numpy_correlations = np.array(corrMatrix)

        # coin labels
        labels = coinList.keys()
        # We want to show all ticks...
        self.ax.set_xticks(np.arange(len(labels)))
        self.ax.set_yticks(np.arange(len(labels)))
        # ... and label them with the respective list entries
        self.ax.set_xticklabels(labels)
        self.ax.set_yticklabels(labels)

        # Rotate the tick labels and set their alignment.
        marts.setp(self.ax.get_xticklabels(), rotation=40, ha="right", rotation_mode="anchor")

        # custom colormap
        colors = [(1, 0.1, 0.1), (0.2, 0.2, 0.2), (1, 0.1, 0.1)]
        colors = [(0, (0.5, 0.5, 0.5)), (1, (1, 0.1, 0.1))]
        #colors = [(255/255,133/255,133/255), (186/255,0,0), (255/255,71/255,71/255)]
        colormap = LinearSegmentedColormap.from_list('cmap_name', colors, 256, 1)

        # Loop over data dimensions and create text annotations.
        for i in range(len(labels)):
            for j in range(len(labels)):
                # set cell text color to give it readable contrast
                if abs(numpy_correlations[i, j]) > 0.5:
                    text_col = FACE_COL_D
                else:
                    text_col = BG_COL_L
                if i >= j:
                    self.ax.text(j, i, '%.2f' % numpy_correlations[i, j], ha="center", va="center", color=text_col, size='small')
        self.ax.imshow(numpy_correlations, alpha=1, cmap=colormap)
        #self.fig.canvas.draw()
        #self.fig.subplots_adjust(left=0.1, bottom=0.3)


    def set_color_mode(self, dark_mode):
        if dark_mode:
            self.fig.set_facecolor('#595959')
            self.ax.set_facecolor('#333333')
            self.ax.legend(facecolor=BG_COL_D)
        else:
            self.fig.set_facecolor('gainsboro')
            self.ax.set_facecolor('lightgrey')
            self.ax.legend(facecolor=BG_COL_L)
        self.fig.canvas.draw()

