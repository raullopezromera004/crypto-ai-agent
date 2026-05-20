import ccxt
import pandas as pd
from datetime import datetime

# =========================================
# EXCHANGE
# =========================================

exchange = ccxt.binance({

    'enableRateLimit': True,

    'timeout': 30000
})

# =========================================
# LOAD SIGNALS
# =========================================

CSV_FILE = "signals.csv"

print("Loading signals...")

df = pd.read_csv(

    CSV_FILE,

    delimiter=';'
)

print()
print(df)

# =========================================
# RESULTS
# =========================================

results = []

# =========================================
# LOOP SIGNALS
# =========================================

for index, row in df.iterrows():

    try:

        symbol = row['symbol']

        entry_price = float(
            row['price']
        )

        timestamp = pd.to_datetime(
            row['timestamp']
        )

        # =====================================
        # CONVERT SYMBOL
        # =====================================

        market_symbol = (
            symbol.replace(
                "USDT",
                "/USDT"
            )
        )

        # =====================================
        # FETCH 15M DATA
        # =====================================

        bars = exchange.fetch_ohlcv(

            market_symbol,

            timeframe='15m',

            limit=200
        )

        ohlcv_df = pd.DataFrame(

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

        ohlcv_df['timestamp'] = pd.to_datetime(

            ohlcv_df['timestamp'],

            unit='ms'
        )

        # =====================================
        # FIND CLOSEST SIGNAL BAR
        # =====================================

        closest_index = (
            ohlcv_df['timestamp']
            .sub(timestamp)
            .abs()
            .idxmin()
        )

        # =====================================
        # FUTURE PRICES
        # =====================================

        def get_future_return(offset):

            future_index = (
                closest_index + offset
            )

            if future_index >= len(ohlcv_df):

                return None

            future_price = (
                ohlcv_df.iloc[
                    future_index
                ]['close']
            )

            pnl = (

                (
                    future_price - entry_price
                )

                / entry_price

            ) * 100

            return round(pnl, 2)

        # =====================================
        # RETURNS
        # =====================================

        return_1h = get_future_return(4)

        return_4h = get_future_return(16)

        return_24h = get_future_return(96)

        # =====================================
        # SAVE RESULT
        # =====================================

        results.append({

            'symbol': symbol,

            'score': row['score'],

            'entry_price': entry_price,

            'return_1h': return_1h,

            'return_4h': return_4h,

            'return_24h': return_24h

        })

    except Exception as e:

        print(symbol, e)

# =========================================
# RESULTS DATAFRAME
# =========================================

results_df = pd.DataFrame(results)

print()
print("=" * 80)
print("TEMPORAL VALIDATION RESULTS")
print("=" * 80)
print()

print(results_df)

# =========================================
# METRICS
# =========================================

def calculate_metrics(column_name):

    valid = results_df[
        column_name
    ].dropna()

    if len(valid) == 0:

        return

    winrate = (
        (valid > 0).mean()
    ) * 100

    avg_return = valid.mean()

    best = valid.max()

    worst = valid.min()

    print()
    print("=" * 50)
    print(column_name.upper())
    print("=" * 50)

    print(
        f"Winrate: {round(winrate, 2)}%"
    )

    print(
        f"Average Return: {round(avg_return, 2)}%"
    )

    print(
        f"Best Return: {round(best, 2)}%"
    )

    print(
        f"Worst Return: {round(worst, 2)}%"
    )

# =========================================
# PERFORMANCE
# =========================================

print()
print("=" * 80)
print("PERFORMANCE BY TIMEFRAME")
print("=" * 80)

calculate_metrics('return_1h')

calculate_metrics('return_4h')

calculate_metrics('return_24h')

print()
print("=" * 80)