import ccxt
import requests
import pandas as pd

from tabulate import tabulate

# =========================================
# EXCHANGE
# =========================================

spot = ccxt.binance({
    'enableRateLimit': True,
    'timeout': 30000
})

futures = ccxt.binance({
    'enableRateLimit': True,
    'timeout': 30000,
    'options': {
        'defaultType': 'swap'
    }
})
print("Loading Binance markets...")

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
# BTC DOMINANCE
# =========================================

def get_btc_dominance():

    try:

        url = "https://api.coingecko.com/api/v3/global"

        response = requests.get(url)

        data = response.json()

        return data['data'][
            'market_cap_percentage'
        ]['btc']

    except:
        return None

# =========================================
# FEAR & GREED
# =========================================

def get_fear_greed():

    try:

        url = "https://api.alternative.me/fng/"

        response = requests.get(url)

        data = response.json()

        value = int(data['data'][0]['value'])

        classification = data['data'][0][
            'value_classification'
        ]

        return value, classification

    except:
        return None, None

# =========================================
# MARKET DATA
# =========================================

def get_market_data(
    spot_symbol,
    future_symbol
):

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
        # VOLUME
        # =========================

        ticker = spot.fetch_ticker(
            spot_symbol
        )

        volume = ticker['quoteVolume']

        # =========================
        # OHLCV
        # =========================

        bars = spot.fetch_ohlcv(
            spot_symbol,
            timeframe='1h',
            limit=200
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
        # EMA50
        # =========================

        df['EMA50'] = (
            df['close']
            .rolling(50)
            .mean()
        )

        price = df.iloc[-1]['close']

        ema50 = df.iloc[-1]['EMA50']

        trend_bullish = price > ema50

        return {

            'funding': funding_rate,

            'oi': open_interest,

            'volume': volume,

            'trend_bullish': trend_bullish
        }

    except Exception as e:

        print(spot_symbol, e)

        return None
# =========================================
# CONTEXT
# =========================================

btc_d = get_btc_dominance()

fg_value, fg_class = get_fear_greed()

# =========================================
# SCORE ENGINE
# =========================================

rows = []

for item in symbols:

    spot_symbol = item['spot']

    future_symbol = item['future']

    # =========================
    # GET DATA
    # =========================

    data = get_market_data(
        spot_symbol,
        future_symbol
    )

    if not data:
        continue

    # =========================
    # INITIAL SCORE
    # =========================

    score = 50

    # =========================
    # TREND
    # =========================

    if data['trend_bullish']:
        score += 20
    else:
        score -= 20

    # =========================
    # FUNDING
    # =========================

    funding = data['funding']

    if funding < 0:
        score += 15

    elif funding > 0.03:
        score -= 15

    # =========================
    # BTC DOMINANCE
    # =========================

    if btc_d:

        if (
            btc_d > 62 and
            spot_symbol != 'BTC/USDT'
        ):
            score -= 10

        elif (
            btc_d < 58 and
            spot_symbol != 'BTC/USDT'
        ):
            score += 10

    # =========================
    # FEAR & GREED
    # =========================

    if fg_value:

        if fg_value < 25:
            score -= 10

        elif fg_value > 55:
            score += 10

    # =========================
    # CLASSIFICATION
    # =========================

    if score >= 75:
        signal = "STRONG BULLISH"

    elif score >= 60:
        signal = "BULLISH"

    elif score <= 35:
        signal = "BEARISH"

    else:
        signal = "NEUTRAL"

    # =========================
    # TABLE
    # =========================

    rows.append([

        spot_symbol,

        round(score, 2),

        signal,

        round(data['funding'], 4),

        round(data['oi'], 2),

        round(data['volume'] / 1_000_000, 2)

    ])

# =========================================
# DISPLAY
# =========================================

print()
print("=" * 80)

print("MARKET SCORE ENGINE")

print("=" * 80)

print()

if btc_d is not None:

    print(
        f"BTC Dominance: "
        f"{round(btc_d, 2)}%"
    )

else:

    print(
        "BTC Dominance: API ERROR"
    )

if fg_value is not None:

    print(
        f"Fear & Greed: "
        f"{fg_value} ({fg_class})"
    )

else:

    print(
        "Fear & Greed: API ERROR"
    )

print()

print(tabulate(

    rows,

    headers=[

        "Symbol",
        "Score",
        "Signal",
        "Funding %",
        "Open Interest",
        "24H Volume (M)"

    ],

    tablefmt="pretty"

))

print()

print("=" * 80)