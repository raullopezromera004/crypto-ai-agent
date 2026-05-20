import ccxt
import pandas as pd

# =========================================
# EXCHANGE
# =========================================

exchange = ccxt.binance({

    'enableRateLimit': True,

    'timeout': 30000
})

# =========================================
# LOAD CSV
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
# VALIDATION
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

        # =====================================
        # CURRENT PRICE
        # =====================================

        ticker = exchange.fetch_ticker(
            symbol.replace("USDT", "/USDT")
        )

        current_price = ticker['last']

        # =====================================
        # RETURN %
        # =====================================

        pnl = (

            (
                current_price - entry_price
            )

            / entry_price

        ) * 100

        results.append({

            'symbol': symbol,

            'score': row['score'],

            'entry_price': entry_price,

            'current_price': current_price,

            'return_pct': pnl

        })

    except Exception as e:

        print(symbol, e)

# =========================================
# RESULTS DATAFRAME
# =========================================

results_df = pd.DataFrame(results)

print()
print("=" * 70)
print("SIGNAL VALIDATION RESULTS")
print("=" * 70)
print()

print(results_df)

# =========================================
# METRICS
# =========================================

if len(results_df) > 0:

    winrate = (

        (
            results_df['return_pct'] > 0
        ).mean()

    ) * 100

    avg_return = (
        results_df['return_pct']
        .mean()
    )

    best_trade = (
        results_df['return_pct']
        .max()
    )

    worst_trade = (
        results_df['return_pct']
        .min()
    )

    print()
    print("=" * 70)
    print("PERFORMANCE METRICS")
    print("=" * 70)
    print()

    print(
        f"Signals: {len(results_df)}"
    )

    print(
        f"Winrate: {round(winrate, 2)}%"
    )

    print(
        f"Average Return: {round(avg_return, 2)}%"
    )

    print(
        f"Best Trade: {round(best_trade, 2)}%"
    )

    print(
        f"Worst Trade: {round(worst_trade, 2)}%"
    )

    print()
    print("=" * 70)

else:

    print("No signals found.")