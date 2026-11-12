# Market Compass

A personal investing dashboard. It turns live market data and a researched news brief into one answer:
where should my next dollar go, and why.

It runs as a hosted Claude artifact. This folder is its source. It is separate from the Roblox project in the
rest of this repository and shares no code with it.

## How it works

```
 free public feeds ──> pipeline/refresh.py ──> market/snapshot ─┐
 news + web search ──> Claude (REFRESH.md) ──> market/brief ────┼──> page ──> your plan
                                          your answers (private) ┘
```

1. **`pipeline/refresh.py`** pulls two years of daily prices for 42 instruments, Treasury yields, the VIX,
   valuation and inflation tables, crypto market data, official Israeli figures (Bank of Israel rate and
   government bond yields, Central Bureau of Statistics inflation) and the last day's headlines. It computes
   every indicator and score and writes `snapshot.json`. Standard library only.
2. **Claude writes the brief** from the headlines and its own web research, scoring how events lean on each part
   of the plan. The rules are in `pipeline/REFRESH.md`.
3. **The page** (`app/market-compass.html`) reads both documents from the artifact's database, combines them with
   your answers about timeline and nerve, and shows the plan. All of the allocation maths is in
   `app/src/engine.js`.

## The model in brief

The first version was rebuilt after six research passes through the investing books and the studies behind
them, and a second round added Israeli costs and tax checks, housing, the evidence on news events, and what
goes wrong for young investors. Where the evidence pointed against an original choice, the choice changed. The page's Learn tab lists the
lessons and the Method tab lists what changed.

- **Baseline.** Your timeline caps the share in stocks and crypto (0% within a year, rising to 90% beyond
  fifteen years; never 100%). Your answer to "what would you do if this fell 30% for three years", asked in
  dollars, picks a level under that cap. That baseline matters far more than any signal.
- **Readings.** Each part gets a reading from -1 to +1. Stocks are 70% trend, 20% risk conditions and 10%
  valuation. Bonds weigh trend, yield after inflation and inflation itself. Gold is three-quarters trend.
  Crypto is two-thirds trend on shorter averages. The yield curve, the VIX and the earnings-yield comparison
  are displayed but not scored, because they have not predicted stock returns.
- **Leans.** On the default setting a full negative reading trims a part by 35% of its size and a full positive
  one adds 20%. What is trimmed waits in T-bills. "Not at all" is offered and is a sound choice.
- **News.** It can make a reading more careful by a tenth at most. It never makes the plan bolder.
- **Limits.** Crypto never exceeds your ceiling or a tenth of your stock money, and is left out for money
  needed within four years. Growth assets never exceed the timeline cap.
- **Beyond the mix.** Share of risk by part, a growth range built from today's yields, three real crisis
  scenarios, a three-fund version, and a one-page written plan.

## Your situation, and Israel

The plan can take a few private facts (income, spending, savings, the costliest debt, whether an employer pays
into a study fund and a pension). With them it redirects money in order: debt costing 7% or more first, then a
cushion of three months of spending, then investing. They are stored under the viewer's own private path.

Country rules live in `COUNTRIES` in `app/src/app.js`. Israel is built in: amounts in shekels, tax year 2026
figures for Keren Hishtalmut, Kupat Gemel LeHashkaa and capital gains, Israeli fund suggestions instead of
US-listed ones, and the steady part held in shekels. The tax figures come from published summaries of the
rules and need a yearly check; gov.il and Kol Zchut refuse automated requests, so they are not read directly.

Shekel bonds get their own reading (`snapshot.israel.bonds`), built like the US one from official data:

- **Trend, 45%.** No free price history exists for a shekel bond fund, so the pipeline models one from the Bank
  of Israel's monthly 5-year yield: each month earns a twelfth of the yield and gains or loses 4.8 times the
  change in yield. That index is read against its 10-month average and against what a one-year Makam paid.
- **Yield after inflation, 30%.** The yield on 5-year inflation-linked government bonds.
- **Inflation, 25%.** The official 12-month figure against the Bank of Israel's 1 to 3% target, and its direction.

US bond readings and the US news brief are never applied to shekel bonds. If the Israeli feeds fail, that part
stays at its baseline.

## Forecasts

The owner asked for predictions made from the news. The Forecasts tab carries them: each weekday, the chance that
US stocks, the Tel Aviv 125, Bitcoin, gold and the dollar in shekels will be higher in a week, and on Mondays in
a month, each with an 80% range and a reason. `pipeline/forecasts.py` sets the starting price and due date and
scores every call from prices, so the forecaster never marks its own work. The page compares the record with a
coin flip and with the naive rule (each asset's own base rate), and gives no verdict on fewer than 60 calls.
Forecasts are deliberately kept out of the plan.

## A home as the goal

Choosing "A home" tells the engine the money has a date. The ceiling on stocks and crypto is then lower for each
year remaining (none under two years, 15% at two to three, 30% at three to five, 45% at five to seven, 60% at
seven to ten), and crypto is left out inside five years. Given a price, the page works out the cash the purchase
needs: the down payment, purchase tax from the bands in `COUNTRIES`, and about 3% of costs.

## Tested on history

`research/` replays the model on the past. `history_fetch.py` rebuilds each month-end's readings from 1997 with
the pipeline's own functions and only the data available that day; `backtest.js` hands them to the page's engine
and holds each plan for the following month.

```bash
python3 market-compass/research/history_fetch.py --out market-compass/research/history.json
```

```bash
node market-compass/research/backtest.js market-compass/research/history.json --json market-compass/research/results.json
```

`app/build.py` puts `results.json` into the page, and the Method tab shows it. Over June 1997 to October 2026 the
default lean cut the middle saver's worst fall from 34% to 28% and added about half a point a year, almost all of
it in 2000-02 and 2007-09, while trading three times as much and lagging in every recovery. Treat it as a sanity
check: it is one history, in US funds, of rules written with hindsight. `--lag N` on the fetch script takes the
readings N trading days early, and `--late FILE` on the backtest reports such a run beside the main one.

## Layout

| Path | What it is |
|---|---|
| `pipeline/refresh.py` | Data fetch, indicators and scoring |
| `pipeline/test_refresh.py` | Offline tests for the maths |
| `pipeline/forecasts.py`, `test_forecasts.py` | The forecast record: adding, scoring, and its tests |
| `pipeline/REFRESH.md` | Refresh procedure and the brief's schema |
| `app/src/engine.js` | Allocation engine: pure functions, shared by the page and the tests |
| `app/src/engine.test.js` | Engine tests |
| `app/src/app.js`, `styles.css`, `page.html` | The interface |
| `app/build.py` | Stitches `src/` and the test results into the single published file |
| `research/history_fetch.py` | Replays the pipeline's readings on history |
| `research/backtest.js`, `backtest.test.js` | Runs the engine over that history; its tests |
| `research/history.json`, `results.json` | The replayed history and the results the page shows |
| `app/market-compass.html` | The built page |

## Working on it

```bash
python3 market-compass/pipeline/test_refresh.py
```

```bash
python3 market-compass/pipeline/test_forecasts.py
```

```bash
node --test market-compass/app/src/engine.test.js
```

```bash
node --test market-compass/research/backtest.test.js
```

```bash
python3 market-compass/app/build.py
```

After a build, publish `app/market-compass.html` to the same artifact to update the live page.

## Limits

This is an educational tool, not financial advice. Every reading describes what has already happened; none of
them predicts. Prices can be delayed, a feed can fail, and the brief is a judgment that can be wrong.
