from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import math
import datetime as dt

import matplotlib.dates as mdates
import matplotlib._color_data as mcd


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


    def draw_plots(self, coin_list, currency, timeScale, time, lim, all_price_data):

        self.sub_plots = []

        # reset array where growth rates are calculated
        self.growth_rates = []

        agregated_volumes = [0 for _ in range(lim+1)]

        row, col = make_grid(coin_list)
        pl = 1  # sublots counter

        for coin in coin_list:
            # flag cases with wrong or missing data
            draw_current_coin = True

            # draw current sublot
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
                    base = prices[0]
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
        self.format_xaxis(sub_plt, timeScale)

        ax2 = sub_plt.twinx()
        ax2.fill_between(times, 0, agregated_volumes, facecolor='#000000', alpha=0.3)
        ax2.axis('off')

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
            self.dark_mode = True
        else:
            self.fig.set_facecolor(BG_COL_L)
            for plot in self.sub_plots:
                plot.set_facecolor(FACE_COL_L)
            self.face_color = FACE_COL_L
            self.dark_mode = False


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
        self.axBar.set_ylabel('%', color='#000000', size='x-small')
        self.axBar.set_title('Change in %', color='#000000', size='small')
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
            self.face_color = '#333333'
            self.dark_mode = True
        else:
            self.fig.set_facecolor('gainsboro')
            self.axBar.set_facecolor('lightgrey')
            self.face_color = 'lightgrey'
            self.dark_mode = False


class MplCorrelationCanvas(FigureCanvasQTAgg):

    def __init__(self, current_coin_list, dark_mode=True, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super(MplCorrelationCanvas, self).__init__(self.fig)

        self.bg_color = BG_COL_D
        self.face_color = FACE_COL_D
        self.dark_mode = dark_mode

        self.fig.set_facecolor(self.bg_color)
        self.coin_list = current_coin_list

    # draws a bar graph given an input of GR (array) and coinList (dictionary)
    def draw_correlations(self, coinList):
        ind = [n for n in range(len(coinList))]
        # update figure
        self.fig.canvas.draw()

    def set_color_mode(self, dark_mode):
        if dark_mode:
            self.dark_mode = True
        else:
            self.dark_mode = False

