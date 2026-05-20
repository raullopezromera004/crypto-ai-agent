import ccxt
import pandas as pd
import pandas_ta as ta
import csv
import os
import time

# =========================================
# EXCHANGES
# =========================================

spot = ccxt.binance({

    'enableRateLimit': True,

    'timeout': 30000,

    'rateLimit': 1200
})

futures = ccxt.binance({

    'enableRateLimit': True,

    'timeout': 30000,

    'rateLimit': 1200,

    'options': {
        'defaultType': 'swap'
    }
})

# =========================================
# SYMBOLS
# =========================================

symbols = [

    {
        'spot': 'BTCUSDT',
        'future': 'BTC/USDT:USDT'
    },

    {
        'spot': 'ETHUSDT',
        'future': 'ETH/USDT:USDT'
    },

    {
        'spot': 'SOLUSDT',
        'future': 'SOL/USDT:USDT'
    },

    {
        'spot': 'BNBUSDT',
        'future': 'BNB/USDT:USDT'
    }

]

# =========================================
# CSV FILE
# =========================================

CSV_FILE = "signals.csv"

print("Creating CSV file...")

# =========================================
# CREATE CSV
# =========================================

if not os.path.exists(CSV_FILE):

    with open(
        CSV_FILE,
        mode='w',
        newline='',
        encoding='utf-8'
    ) as file:

        writer = csv.writer(
            file,
            delimiter=';'
        )

        writer.writerow([

            "timestamp",

            "symbol",

            "score",

            "price",

            "funding",

            "compression",

            "volume_build",

            "price_change",

            "open_interest"

        ])

# =========================================
# GET DATA
# =========================================

def get_data(spot_symbol, future_symbol):

    try:

        # =====================================
        # FUNDING
        # =====================================

        funding = futures.fetch_funding_rate(
            future_symbol
        )

        funding_rate = (
            funding['fundingRate'] * 100
        )

        # =====================================
        # OPEN INTEREST
        # =====================================

        oi = futures.fetch_open_interest(
            future_symbol
        )

        open_interest = oi[
            'openInterestAmount'
        ]

        # =====================================
        # KLINES DIRECT BINANCE API
        # =====================================

        bars = spot.publicGetKlines({

            'symbol': spot_symbol,

            'interval': '15m',

            'limit': 100

        })

        # =====================================
        # DATAFRAME
        # =====================================

        df = pd.DataFrame(
            bars
        )

        df = df.iloc[:, :6]

        df.columns = [
            'timestamp',
            'open',
            'high',
            'low',
            'close',
            'volume'
        ]

        df = df.astype(float)

        # =====================================
        # VOLUME BUILDUP
        # =====================================

        df['VOL_MEAN'] = (
            df['volume']
            .rolling(20)
            .mean()
        )

        df['VOL_RATIO'] = (
            df['volume']
            / df['VOL_MEAN']
        )

        # =====================================
        # ATR
        # =====================================

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

        # =====================================
        # COMPRESSION
        # =====================================

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

        # =====================================
        # VOLUME BUILD
        # =====================================

        recent_vol = (

            df['VOL_RATIO']
            .tail(5)
            .mean()
        )

        # =====================================
        # PRICE CHANGE
        # =====================================

        price_now = df.iloc[-1]['close']

        price_prev = df.iloc[-10]['close']

        price_change = (

            (
                price_now - price_prev
            )

            / price_prev

        ) * 100

        # =====================================
        # ATR EXPANSION
        # =====================================

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

    # =====================================
    # NEGATIVE FUNDING
    # =====================================

    if data['funding'] < -0.01:

        score += 30

    elif data['funding'] < 0:

        score += 15

    # =====================================
    # HIGH OPEN INTEREST
    # =====================================

    if data['oi'] > 500000:

        score += 20

    # =====================================
    # PRICE HOLDING
    # =====================================

    if data['price_change'] > -1:

        score += 15

    # =====================================
    # COMPRESSION
    # =====================================

    if data['compression'] < 3:

        score += 20

    # =====================================
    # VOLUME BUILD
    # =====================================

    if data['recent_vol'] > 1.1:

        score += 15

    # =====================================
    # ATR EXPANSION
    # =====================================

    if data['atr_expansion']:

        score += 10

    return score

# =========================================
# MAIN LOOP
# =========================================

print()
print("SIGNAL LOGGER RUNNING...")
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

            # =====================================
            # SAVE HIGH SCORES
            # =====================================

            if score >= 70:

                print(
                    f"SAVING SIGNAL: {spot_symbol}"
                )

                with open(
                    CSV_FILE,
                    mode='a',
                    newline='',
                    encoding='utf-8'
                ) as file:

                    writer = csv.writer(
                        file,
                        delimiter=';'
                    )

                    writer.writerow([

                        str(pd.Timestamp.now()),

                        spot_symbol,

                        score,

                        round(data['price'], 4),

                        round(data['funding'], 4),

                        round(data['compression'], 2),

                        round(data['recent_vol'], 2),

                        round(data['price_change'], 2),

                        round(data['oi'], 2)

                    ])

        print()
        print("Waiting 5 minutes...")
        print()

        time.sleep(300)

    except Exception as e:

        print("MAIN LOOP ERROR:", e)

        time.sleep(60)