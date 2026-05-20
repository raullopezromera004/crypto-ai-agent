import ccxt
import pandas as pd
import pandas_ta as ta

from tabulate import tabulate

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
        # PRICE DATA
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

        # ATR mean

        df['ATR_MEAN'] = (
            df['ATR']
            .rolling(20)
            .mean()
        )

        # =========================
        # PRICE STABILITY
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
        # VOLUME BUILDUP
        # =========================

        recent_vol = (
            df['VOL_RATIO']
            .tail(5)
            .mean()
        )

        # =========================
        # PRICE HOLDING
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

            'atr_expansion': atr_expansion
        }

    except Exception as e:

        print(spot_symbol, e)

        return None

# =========================================
# ENGINE
# =========================================

rows = []

for item in symbols:

    spot_symbol = item['spot']

    future_symbol = item['future']

    data = get_data(
        spot_symbol,
        future_symbol
    )

    if not data:
        continue

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
    # VOLUME BUILDUP
    # =====================================

    if data['recent_vol'] > 1.1:
        score += 15

    # =====================================
    # ATR EXPANSION
    # =====================================

    if data['atr_expansion']:
        score += 10

    # =====================================
    # SIGNAL
    # =====================================

    if score >= 80:
        signal = "HIGH EARLY SQUEEZE"

    elif score >= 60:
        signal = "BUILDING PRESSURE"

    else:
        signal = "LOW"

    rows.append([

        spot_symbol,

        round(score, 2),

        signal,

        round(data['funding'], 4),

        round(data['compression'], 2),

        round(data['recent_vol'], 2),

        round(data['price_change'], 2),

        round(data['oi'], 2)

    ])

# =========================================
# DISPLAY
# =========================================

print()
print("=" * 100)

print("SQUEEZE ENGINE V2")

print("=" * 100)

print()

print(tabulate(

    rows,

    headers=[

        "Symbol",
        "Score",
        "Signal",
        "Funding %",
        "Compression %",
        "Volume Build",
        "Price Change %",
        "Open Interest"

    ],

    tablefmt="pretty"

))

print()

print("=" * 100)