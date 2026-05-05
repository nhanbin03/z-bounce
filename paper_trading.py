import os
import asyncio
from decimal import Decimal
from collections import deque
from datetime import time, datetime
import pandas as pd
import pandas_ta as ta
import json
import pytz

from dotenv import load_dotenv
from paperbroker.client import PaperBrokerClient
from paperbroker.market_data import RedisMarketDataClient, KafkaMarketDataClient

load_dotenv()

# === Configuration constants ===
SYMBOL = "HNXDS:VN30F2605"
WINDOW_SIZE = 12
Z_THRESHOLD = Decimal("1.5")
POSITION_SCALING_FACTOR = Decimal("0.02")
# =========================

class LiveStrategy:
    def __init__(self, client, symbol, window_size=10):
        self.client = client
        self.symbol = symbol

        # === Strategy state ===
        self.window_size = window_size
        self.price_window = deque(maxlen=window_size)

        self.inventory = 0
        self.inventory_price = Decimal("0")

        self.last_minute = None
        self.latest_price = None

        self.current_bar = None
        self.last_bar_time = None

        self.highs = []
        self.lows = []
        self.closes = []

        self.order_side = None

        # Track active order
        self.active_order_id = None

    def save_state(self):
        state = {
            "price_window": [float(x) for x in self.price_window],
            "highs": self.highs,
            "lows": self.lows,
            "closes": self.closes,
            "inventory": float(self.inventory),
        }

        with open("state.json", "w") as f:
            json.dump(state, f)

        print("[STATE] Saved")

    def load_state(self):
        try:
            with open("state.json", "r") as f:
                state = json.load(f)

            self.price_window = deque(
                [Decimal(str(x)) for x in state["price_window"]],
                maxlen=self.window_size
            )

            self.highs = state["highs"]
            self.lows = state["lows"]
            self.closes = state["closes"]

            self.inventory = Decimal(str(state["inventory"]))

            print("[STATE] Loaded successfully")

        except FileNotFoundError:
            print("[STATE] No saved state found (cold start)")

    def is_trading_time(self):
        tz = pytz.timezone("Asia/Ho_Chi_Minh")
        now = datetime.now(tz).time()

        morning_start = time(9, 15)
        morning_end   = time(11, 30)

        afternoon_start = time(13, 0)
        afternoon_end   = time(14, 45)

        return (
            (morning_start <= now <= morning_end) or
            (afternoon_start <= now <= afternoon_end)
        )

    # =========================
    # 📊 Indicators
    # =========================
    def get_mean_std(self):
        if len(self.price_window) < self.window_size:
            return None, None

        mean = sum(self.price_window) / Decimal(len(self.price_window))
        variance = sum((p - mean) ** 2 for p in self.price_window) / Decimal(len(self.price_window))
        std = Decimal(float(variance) ** 0.5)

        return mean, std

    def place_order(self, price: Decimal, order_type: str, qty: int):
        self.active_order_id = self.client.place_order(self.symbol, order_type, qty, float(price))
        self.order_side = order_type
        print(
            f"[ORDER] side={self.order_side} qty={qty} price={price} "
            f"(inv before={self.inventory})"
        )

    # =========================
    # 🧠 Strategy Logic
    # =========================
    def try_place_order(self, price: Decimal, adx_value=None):
        self.price_window.append(price)

        mean, std = self.get_mean_std()
        if mean is None or std == 0:
            return

        z = (price - mean) / std

        threshold = Z_THRESHOLD
        position_scaling_factor = POSITION_SCALING_FACTOR

        if adx_value is None:
            return
        
        if self.active_order_id: # Shouldn't happen, because order is cancelled before calling this function
            return
        
        print(
            f"[SIGNAL] price={price} z={round(z, 3)} "
            f"adx={round(adx_value, 2)} inv={self.inventory}"
        )
        
        if adx_value > 40:
            if z > threshold + max(Decimal(0), Decimal(self.inventory)) * threshold * position_scaling_factor:
                if self.inventory >= 0:
                    self.place_order(price, "BUY", 1)
                else:
                    self.place_order(price, "BUY", abs(self.inventory))
            elif z < -threshold - max(Decimal(0), Decimal(-self.inventory)) * threshold * position_scaling_factor:
                if self.inventory <= 0:
                    self.place_order(price, "SELL", 1)
                else:
                    self.place_order(price, "SELL", abs(self.inventory))

        if adx_value < 30:
            if z > threshold + max(Decimal(0), Decimal(-self.inventory)) * threshold * position_scaling_factor:
                if self.inventory <= 0:
                    self.place_order(price, "SELL", 1)
                else:
                    self.place_order(price, "SELL", abs(self.inventory))
            elif z < -threshold - max(Decimal(0), Decimal(self.inventory)) * threshold * position_scaling_factor:
                if self.inventory >= 0:
                    self.place_order(price, "BUY", 1)
                else:
                    self.place_order(price, "BUY", abs(self.inventory))

        if self.active_order_id is None:
            print("[DECISION] No trade")


    # =========================
    # 🔔 Event Handlers
    # =========================
    def on_filled(self, cl_ord_id, last_px, last_qty, **kw):
        print(
            f"[FILL] id={cl_ord_id} {self.order_side} {last_qty} @ {last_px} "
            f"(before inv={self.inventory})"
        )

        if cl_ord_id != self.active_order_id:
            return

        # Update inventory
        if self.order_side == "BUY":
            # BUY
            self.inventory += last_qty
        if self.order_side == "SELL":
            # SELL
            self.inventory -= last_qty

        print(f"[POSITION] inventory now = {self.inventory}")

        self.active_order_id = None
        self.order_side = None

    def compute_adx(self):
        if len(self.closes) < self.window_size:
            return None

        df = pd.DataFrame({
            "high": self.highs,
            "low": self.lows,
            "close": self.closes
        })

        adx = ta.adx(
            high=df["high"],
            low=df["low"],
            close=df["close"],
            length=self.window_size
        )

        return adx[f"ADX_{self.window_size}"].iloc[-1]

    def on_bar_close(self):
        bar = self.current_bar
        if bar is None:
            return
        
        if not self.is_trading_time():
            print("[SKIP] Outside trading hours")
            return

        # store history
        self.highs.append(bar["high"])
        self.lows.append(bar["low"])
        self.closes.append(bar["close"])

        tz = pytz.timezone("Asia/Ho_Chi_Minh")
        print(
            f"\n[BAR] {datetime.now(tz).strftime('%H:%M:%S')} "
            f"O={bar['open']} H={bar['high']} L={bar['low']} C={bar['close']} "
            f"INV={self.inventory}"
        )

        price = Decimal(str(bar["close"]))

        adx_value = self.compute_adx()

        # === cancel old order ===
        if self.active_order_id:
            print(f"[CANCEL] Canceling order {self.active_order_id}")
            self.client.cancel_order(self.active_order_id)
            self.active_order_id = None
            self.order_side = None

        self.try_place_order(price, adx_value)
        self.save_state()

    def on_market(self, instrument, quote):
        price = quote.latest_matched_price
        if price is None:
            return

        self.latest_price = Decimal(str(price))
    
        price = float(price)
        tz = pytz.timezone("Asia/Ho_Chi_Minh")
        now = datetime.now(tz).replace(second=0, microsecond=0)

        # New minute → finalize previous bar
        if self.last_bar_time and now != self.last_bar_time:
            self.on_bar_close()

            # reset bar
            self.current_bar = {
                "open": price,
                "high": price,
                "low": price,
                "close": price
            }
        else:
            if self.current_bar is None:
                self.current_bar = {
                    "open": price,
                    "high": price,
                    "low": price,
                    "close": price
                }
            else:
                self.current_bar["high"] = max(self.current_bar["high"], price)
                self.current_bar["low"] = min(self.current_bar["low"], price)
                self.current_bar["close"] = price

        self.last_bar_time = now


# =========================
# 🚀 Main
# =========================
async def main():
    # FIX client
    client = PaperBrokerClient(
      default_sub_account=os.getenv("DEFAULT_SUB_ACCOUNT", "main"),
      username=os.getenv("PAPERBROKER_USERNAME"),
      password=os.getenv("PAPERBROKER_PASSWORD"),
      rest_base_url=os.getenv("PAPERBROKER_REST_BASE_URL"),
      socket_connect_host=os.getenv("PAPERBROKER_SOCKET_HOST"),
      socket_connect_port=int(os.getenv("PAPERBROKER_SOCKET_PORT", "5001")),
      sender_comp_id=os.getenv("PAPERBROKER_SENDER_COMP_ID"),
      target_comp_id=os.getenv("PAPERBROKER_TARGET_COMP_ID", "SERVER"),    
    )

    # Strategy
    strategy = LiveStrategy(client, SYMBOL, WINDOW_SIZE)

    strategy.load_state()

    # Register events
    client.on("fix:order:filled", strategy.on_filled)

    # Connect
    client.connect()
    if not client.wait_until_logged_on(10):
        print("Login failed")
        return

    print("Connected!")

    print("[INIT] Recovering state...")

    orders = client.recover_pending_orders()

    portfolio = client.get_portfolio_by_sub()

    inventory = 0
    if portfolio.get("success"):
        for pos in portfolio["items"]:
            if pos["instrument"] == SYMBOL:
                inventory = pos["quantity"]
                break

    strategy.inventory = inventory

    print(f"[INIT] Recovered inventory = {inventory}")
    if orders:
        strategy.active_order_id = orders[0]["cl_ord_id"]
        strategy.order_side = None
        print(f"[INIT] Recovered active order {strategy.active_order_id}")
    else:
        print("[INIT] No active orders")

    # Market data
    md = KafkaMarketDataClient(
        bootstrap_servers=os.getenv("PAPERBROKER_KAFKA_BOOTSTRAP_SERVERS"),
        username=os.getenv("PAPERBROKER_KAFKA_USERNAME"),
        password=os.getenv("PAPERBROKER_KAFKA_PASSWORD"),
        env_id=os.getenv("PAPERBROKER_ENV_ID"),
        merge_updates=True
    )
    await md.subscribe(SYMBOL, strategy.on_market)
    await md.start()

    # Keep running
    while True:
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())