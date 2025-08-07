from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner
import yfinance as yf
import matplotlib.pyplot as plt
from kivy_garden.matplotlib import FigureCanvasKivyAgg
import matplotlib.dates as mdates
from kivy.core.window import Window

# Maximize the application window on startup
Window.maximize()

#Attempts to resolve a stock ticker by checking if it's a US ticker first.
#If not, it falls back to trying the UK (.L) ticker suffix.
def resolveTicker(userInput):
    userInput = userInput.upper().strip()

    if '.' in userInput:
        return userInput

    try:
        stock = yf.Ticker(userInput)
        data = stock.history(period="1d")
        if not data.empty:
            return userInput
    except Exception:
        pass

    return userInput + ".L"

#Fetches the current stock price and currency for a given ticker symbol.
def getStockInfo(symbol):
    try:
        stock = yf.Ticker(symbol)
        data = stock.history(period="1d")
        if data.empty:
            return None, None
        price = data["Close"].iloc[-1]
        currency = stock.info.get("currency", "USD")
        return float(price), currency
    except Exception:
        return None, None

#Gets historical closing prices and corresponding datetime objects for a given stock.
def getStockHistory(symbol, period="1d", interval="15m"):
    try:
        stock = yf.Ticker(symbol)
        data = stock.history(period=period, interval=interval)
        if data.empty:
            return None, None
        prices = data["Close"].tolist()
        dates = data.index.to_pydatetime().tolist()
        return prices, dates
    except Exception:
        return None, None

#Main Kivy application class for the stock viewer
class StockApp(App):
    #Main Kivy build method to construct the UI layout
    def build(self):
        self.title = "Stock Viewer"
        self.mainLayout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        self.symbolInput = TextInput(
            hint_text='Enter stock symbol (e.g., AAPL, VWRP, NVDA, etc.) Funds on multiple exchanges may require the exchange ticker for local pricing (e.g., TSCO.L, NA.TA, SHEL.L, etc.) Similar rules needed for cryptoassets for currency equivalents (e.g., BTC-GBP, ETH-AUD, BTC-JPY, etc.)',
            multiline=False
        )
        fetchButton = Button(text='Get Stock Data', size_hint=(1, None), height=40)
        fetchButton.bind(on_press=self.fetchData)

        self.periodSpinner = Spinner(
            text='1 Day',
            values=('1 Day', '1 Week', '1 Month', '3 Months', '1 Year'),
            size_hint=(None, None),
            size=(150, 44)
        )
        self.periodSpinner.bind(text=self.onPeriodSelect)

        self.resultLabel = Label(text='Price and currency will appear here', size_hint=(1, None), height=40)

        self.chartBox = BoxLayout(size_hint_y=2)

        self.mainLayout.add_widget(self.symbolInput)
        self.mainLayout.add_widget(fetchButton)
        self.mainLayout.add_widget(self.periodSpinner)
        self.mainLayout.add_widget(self.resultLabel)
        self.mainLayout.add_widget(self.chartBox)

        self.currentSymbol = None
        self.currentCurrency = None
        self.currentCanvas = None
        self.hoverCid = None

        return self.mainLayout
    
    #Triggered when the user selects a new period in the dropdown
    def onPeriodSelect(self, spinner, text):
        if self.currentSymbol:
            self.updateChart(self.currentSymbol, text)

    #Fetch stock data when the user presses the fetch button
    def fetchData(self, instance):
        rawInput = self.symbolInput.text
        symbol = resolveTicker(rawInput)
        price, currency = getStockInfo(symbol)
        if price is None:
            self.resultLabel.text = "Error fetching data. Check symbol."
            self.clearChart()
            return
        
        #Try to get the full name of the asset
        try:
            stock = yf.Ticker(symbol)
            info = stock.info
            name = info.get("shortName") or info.get("longName") or "Unknown Name"
        except Exception:
            name = "Unknown Name"

        self.resultLabel.text = f"{name} ({symbol}): {price:.2f} {currency}"
        self.currentSymbol = symbol
        self.currentCurrency = currency

        self.updateChart(symbol, self.periodSpinner.text)

    #Updates the matplotlib chart with new data for the selected period
    def updateChart(self, symbol, periodText):
        periodMap = {
            '1 Day': ("1d", "15m"),
            '1 Week': ("5d", "1h"),
            '1 Month': ("1mo", "1d"),
            '3 Months': ("3mo", "1d"),
            '1 Year': ("1y", "1d"),
        }
        period, interval = periodMap.get(periodText, ("1d", "15m"))
        prices, dates = getStockHistory(symbol, period=period, interval=interval)

        if prices and dates:
            self.showChart(prices, dates, self.currentCurrency)
        else:
            self.clearChart()
            self.resultLabel.text = "No data available for selected period."

    #Clears the currently displayed chart from the UI
    def clearChart(self):
        if self.currentCanvas:
            if self.hoverCid is not None:
                self.currentCanvas.figure.canvas.mpl_disconnect(self.hoverCid)
                self.hoverCid = None

            self.chartBox.remove_widget(self.currentCanvas)
            self.currentCanvas.figure.clf()
            plt.close(self.currentCanvas.figure)
            self.currentCanvas = None

    # Displays the stock price chart with hover annotations
    def showChart(self, prices, dates, currency):
        self.clearChart()

        fig, ax = plt.subplots(figsize=(10, 6))
        line, = ax.plot(dates, prices, marker='o')
        ax.set_title("Stock Prices")
        ax.set_xlabel("Date / Time")
        ax.set_ylabel(f"Price ({currency})")

        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
        fig.autofmt_xdate(rotation=20)

        xMin = min(dates)
        xMax = max(dates)
        xRange = xMax - xMin
        ax.set_xlim(xMin - xRange * 0.05, xMax + xRange * 0.05)

        #Tooltip setup
        annot = ax.annotate("", xy=(0, 0), xytext=(15, 15),
                            textcoords="offset points",
                            bbox=dict(boxstyle="round", fc="w"),
                            arrowprops=dict(arrowstyle="->"))
        annot.set_visible(False)

        datesNum = mdates.date2num(dates)

        #Updates tooltip annotation
        def updateAnnot(idx):
            y = prices[idx]
            dt = dates[idx]
            annot.xy = (dates[idx], y)
            text = f"{dt.strftime('%Y-%m-%d %H:%M')}\nPrice: {y:.2f} {currency}"
            annot.set_text(text)
            annot.get_bbox_patch().set_alpha(0.9)

        #Handles hover interactions with the chart
        def hover(event):
            vis = annot.get_visible()
            if event.inaxes == ax:
                mouseX = event.xdata
                if mouseX is None:
                    return

                idx = min(range(len(datesNum)), key=lambda i: abs(datesNum[i] - mouseX))

                threshold = (datesNum[-1] - datesNum[0]) * 0.03

                if abs(datesNum[idx] - mouseX) < threshold:
                    updateAnnot(idx)
                    if not vis:
                        annot.set_visible(True)
                    fig.canvas.draw_idle()
                else:
                    if vis:
                        annot.set_visible(False)
                        fig.canvas.draw_idle()
            else:
                if vis:
                    annot.set_visible(False)
                    fig.canvas.draw_idle()

        self.hoverCid = fig.canvas.mpl_connect("motion_notify_event", hover)

        self.currentCanvas = FigureCanvasKivyAgg(fig)
        self.chartBox.add_widget(self.currentCanvas)

#Only runs when executed directly
if __name__ == '__main__':
    StockApp().run()
