import ccxt
import pandas as pd
import pandas_ta as ta
import requests
import time

from telegram import Bot

# =========================================
# TELEGRAM
# =========================================

TELEGRAM_TOKEN = "8871882804:AAEvTqmg_zW55_QPxSWZe06kP3wNlKDu77Q"

CHAT_ID = "1901963655"

bot = Bot(token=TELEGRAM_TOKEN)

# =========================================
# EXCHANGES
# =========================================

spot = ccxt.binance({
    'enableRateLimit': True
})

futures = ccxt.binance({
    'enableRateLimit': True,
    'options': {
        'defaultType': 'swap'
    }
})

print("Loading markets...")

spot.load_markets()
futures.load_markets()

print("Markets loaded.")

# =========================================
# SYMBOLS
# =========================================

symbols = [

    {
        'spot': 'BTC/USDT',
        'future': 'BTC/USDT:USDT'
    },

    {
        'spot': 'ETH/USDT',
        'future': 'ETH/USDT:USDT'
    },

    {
        'spot': 'SOL/USDT',
        'future': 'SOL/USDT:USDT'
    },

    {
        'spot': 'BNB/USDT',
        'future': 'BNB/USDT:USDT'
    }

]

# =========================================
# PREVENT DUPLICATES
# =========================================

last_alerts = {}

# =========================================
# GET DATA
# =========================================

def get_data(spot_symbol, future_symbol):

    try:

        # =========================
        # FUNDING
        # =========================

        funding = futures.fetch_funding_rate(
            future_symbol
        )

        funding_rate = (
            funding['fundingRate'] * 100
        )

        # =========================
        # OPEN INTEREST
        # =========================

        oi = futures.fetch_open_interest(
            future_symbol
        )

        open_interest = oi[
            'openInterestAmount'
        ]

        # =========================
        # OHLCV
        # =========================

        bars = spot.fetch_ohlcv(
            spot_symbol,
            timeframe='15m',
            limit=100
        )

        df = pd.DataFrame(
            bars,
            columns=[
                'timestamp',
                'open',
                'high',
                'low',
                'close',
                'volume'
            ]
        )

        # =========================
        # VOLUME BUILDUP
        # =========================

        df['VOL_MEAN'] = (
            df['volume']
            .rolling(20)
            .mean()
        )

        df['VOL_RATIO'] = (
            df['volume']
            / df['VOL_MEAN']
        )

        # =========================
        # ATR
        # =========================

        df['ATR'] = ta.atr(
            df['high'],
            df['low'],
            df['close'],
            length=14
        )

        df['ATR_MEAN'] = (
            df['ATR']
            .rolling(20)
            .mean()
        )

        # =========================
        # COMPRESSION
        # =========================

        recent_high = (
            df['high']
            .tail(20)
            .max()
        )

        recent_low = (
            df['low']
            .tail(20)
            .min()
        )

        compression = (
            (
                recent_high - recent_low
            )
            / recent_low
        ) * 100

        # =========================
        # VOLUME BUILD
        # =========================

        recent_vol = (
            df['VOL_RATIO']
            .tail(5)
            .mean()
        )

        # =========================
        # PRICE CHANGE
        # =========================

        price_now = df.iloc[-1]['close']

        price_prev = df.iloc[-10]['close']

        price_change = (
            (
                price_now - price_prev
            )
            / price_prev
        ) * 100

        # =========================
        # ATR EXPANSION
        # =========================

        atr_expansion = (
            df.iloc[-1]['ATR']
            >
            df.iloc[-1]['ATR_MEAN']
        )

        return {

            'funding': funding_rate,

            'oi': open_interest,

            'compression': compression,

            'recent_vol': recent_vol,

            'price_change': price_change,

            'atr_expansion': atr_expansion,

            'price': price_now
        }

    except Exception as e:

        print(spot_symbol, e)

        return None

# =========================================
# SCORE ENGINE
# =========================================

def calculate_score(data):

    score = 0

    # NEGATIVE FUNDING

    if data['funding'] < -0.01:
        score += 30

    elif data['funding'] < 0:
        score += 15

    # HIGH OI

    if data['oi'] > 500000:
        score += 20

    # PRICE HOLDING

    if data['price_change'] > -1:
        score += 15

    # COMPRESSION

    if data['compression'] < 3:
        score += 20

    # VOLUME BUILD

    if data['recent_vol'] > 1.1:
        score += 15

    # ATR EXPANSION

    if data['atr_expansion']:
        score += 10

    return score

# =========================================
# SEND ALERT
# =========================================

def send_alert(symbol, score, data):

    message = f"""
🚨 HIGH EARLY SQUEEZE

Coin: {symbol}

Score: {score}/100

Price: {round(data['price'], 4)}

Funding: {round(data['funding'], 4)}%

Compression: {round(data['compression'], 2)}%

Volume Build: {round(data['recent_vol'], 2)}

Price Change: {round(data['price_change'], 2)}%

Open Interest: {round(data['oi'], 2)}

Potential squeeze pressure building.
"""

    bot.send_message(
        chat_id=CHAT_ID,
        text=message
    )

# =========================================
# MAIN LOOP
# =========================================

print()
print("SQUEEZE ALERT BOT RUNNING...")
print()

while True:

    try:

        for item in symbols:

            spot_symbol = item['spot']

            future_symbol = item['future']

            data = get_data(
                spot_symbol,
                future_symbol
            )

            if not data:
                continue

            score = calculate_score(data)

            print(
                f"{spot_symbol} -> Score: {score}"
            )

            # =====================
            # ALERT CONDITION
            # =====================

            if score >= 80:

                # Prevent spam

                last_time = last_alerts.get(
                    spot_symbol,
                    0
                )

                now = time.time()

                if now - last_time > 3600:

                    print(
                        f"ALERT SENT: {spot_symbol}"
                    )

                    send_alert(
                        spot_symbol,
                        score,
                        data
                    )

                    last_alerts[
                        spot_symbol
                    ] = now

        # =========================
        # WAIT
        # =========================

        print()
        print("Waiting 5 minutes...")
        print()

        time.sleep(300)

    except Exception as e:

        print("MAIN LOOP ERROR:", e)

        time.sleep(60)