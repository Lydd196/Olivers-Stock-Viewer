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


# Set window size to screen resolution
Window.size = (1920, 1080)



def get_stock_info(symbol):
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


def get_stock_history(symbol, period="1d", interval="15m"):
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


class StockApp(App):
    def build(self):
        self.layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        self.symbol_input = TextInput(
            hint_text='Enter stock symbol (e.g., AAPL, VOD.L)', multiline=False
        )
        fetch_button = Button(text='Get Stock Data', size_hint=(1, None), height=40)
        fetch_button.bind(on_press=self.fetch_data)

        self.period_spinner = Spinner(
            text='1 Day',
            values=('1 Day', '1 Week', '1 Month', '3 Months', '1 Year'),
            size_hint=(None, None),
            size=(150, 44)
        )
        self.period_spinner.bind(text=self.on_period_select)

        self.result_label = Label(text='Price and currency will appear here', size_hint=(1, None), height=40)

        self.chart_box = BoxLayout(size_hint_y=2)

        self.layout.add_widget(self.symbol_input)
        self.layout.add_widget(fetch_button)
        self.layout.add_widget(self.period_spinner)
        self.layout.add_widget(self.result_label)
        self.layout.add_widget(self.chart_box)

        self.current_symbol = None
        self.current_currency = None

        return self.layout

    def on_period_select(self, spinner, text):
        if self.current_symbol:
            self.update_chart(self.current_symbol, text)

    def fetch_data(self, instance):
        symbol = self.symbol_input.text.strip().upper()
        price, currency = get_stock_info(symbol)
        if price is None:
            self.result_label.text = "Error fetching data. Check symbol."
            self.chart_box.clear_widgets()
            return

        self.result_label.text = f"{symbol}: {price:.2f} {currency}"
        self.current_symbol = symbol
        self.current_currency = currency

        self.update_chart(symbol, self.period_spinner.text)

    def update_chart(self, symbol, period_text):
        period_map = {
            '1 Day': ("1d", "15m"),
            '1 Week': ("5d", "1h"),
            '1 Month': ("1mo", "1d"),
            '3 Months': ("3mo", "1d"),
            '1 Year': ("1y", "1d"),
        }
        period, interval = period_map.get(period_text, ("1d", "15m"))
        prices, dates = get_stock_history(symbol, period=period, interval=interval)

        if prices and dates:
            self.show_chart(prices, dates, self.current_currency)
        else:
            self.chart_box.clear_widgets()
            self.result_label.text = "No data available for selected period."

    def show_chart(self, prices, dates, currency):
        self.chart_box.clear_widgets()
        fig, ax = plt.subplots(figsize=(10, 6))  # Bigger figure

        line, = ax.plot(dates, prices, marker='o')
        ax.set_title("Stock Prices")
        ax.set_xlabel("Date / Time")
        ax.set_ylabel(f"Price ({currency})")

        # Format x-axis with date/time
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
        fig.autofmt_xdate(rotation=20)

        # Add padding on x-axis so points aren't squeezed at edges
        x_min = min(dates)
        x_max = max(dates)
        x_range = x_max - x_min
        ax.set_xlim(x_min - x_range * 0.05, x_max + x_range * 0.05)

        annot = ax.annotate("", xy=(0, 0), xytext=(15, 15),
                            textcoords="offset points",
                            bbox=dict(boxstyle="round", fc="w"),
                            arrowprops=dict(arrowstyle="->"))
        annot.set_visible(False)

        # Convert dates to matplotlib float format for easier distance calc
        dates_num = mdates.date2num(dates)

        def update_annot(idx):
            y = prices[idx]
            dt = dates[idx]
            annot.xy = (dates[idx], y)
            text = f"{dt.strftime('%Y-%m-%d %H:%M')}\nPrice: {y:.2f} {currency}"
            annot.set_text(text)
            annot.get_bbox_patch().set_alpha(0.9)

        def hover(event):
            vis = annot.get_visible()
            if event.inaxes == ax:
                mouse_x = event.xdata
                if mouse_x is None:
                    return

                # Find index of closest date point on x axis
                idx = min(range(len(dates_num)), key=lambda i: abs(dates_num[i] - mouse_x))

                # Threshold for horizontal proximity (3% of x-axis range)
                threshold = (dates_num[-1] - dates_num[0]) * 0.03

                if abs(dates_num[idx] - mouse_x) < threshold:
                    update_annot(idx)
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

        fig.canvas.mpl_connect("motion_notify_event", hover)

        self.chart_box.add_widget(FigureCanvasKivyAgg(fig))


if __name__ == '__main__':
    StockApp().run()
