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
   valuation and inflation tables, crypto market data and the last day's headlines. It computes every indicator
   and score and writes `snapshot.json`. Standard library only.
2. **Claude writes the brief** from the headlines and its own web research, scoring how events lean on each part
   of the plan. The rules are in `pipeline/REFRESH.md`.
3. **The page** (`app/market-compass.html`) reads both documents from the artifact's database, combines them with
   your answers about timeline and nerve, and shows the plan. All of the allocation maths is in
   `app/src/engine.js`.

## The model in brief

The first version was rebuilt after six research passes through the investing books and the studies behind
them. Where the evidence pointed against an original choice, the choice changed. The page's Learn tab lists the
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
US-listed ones, and the steady part held in shekels. US bond readings are not applied to shekel bonds, so that
part stays at its baseline. The figures come from published summaries of the rules and need a yearly check.

## Layout

| Path | What it is |
|---|---|
| `pipeline/refresh.py` | Data fetch, indicators and scoring |
| `pipeline/test_refresh.py` | Offline tests for the maths |
| `pipeline/REFRESH.md` | Refresh procedure and the brief's schema |
| `app/src/engine.js` | Allocation engine: pure functions, shared by the page and the tests |
| `app/src/engine.test.js` | Engine tests |
| `app/src/app.js`, `styles.css`, `page.html` | The interface |
| `app/build.py` | Stitches `src/` into the single published file |
| `app/market-compass.html` | The built page |

## Working on it

```bash
python3 market-compass/pipeline/test_refresh.py
```

```bash
node --test market-compass/app/src/engine.test.js
```

```bash
python3 market-compass/app/build.py
```

After a build, publish `app/market-compass.html` to the same artifact to update the live page.

## Limits

This is an educational tool, not financial advice. Every reading describes what has already happened; none of
them predicts. Prices can be delayed, a feed can fail, and the brief is a judgment that can be wrong.
