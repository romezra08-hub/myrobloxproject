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

- Your timeline caps how much can sit in stocks and crypto. Your answer to "what would you do after a 30% fall"
  picks a level under that cap. That baseline matters far more than any signal.
- Each part (US stocks, international stocks, crypto, gold, bonds) gets a reading from -1 to +1. Trend carries
  the most weight, then valuation, risk conditions, yields, liquidity and the news brief, depending on the part.
- A full reading moves a part by 35% of its size ("a little") or 70% ("a lot"). What is trimmed waits in T-bills.
- Crypto never exceeds the ceiling you choose. Growth assets never exceed your timeline cap.

The Method tab on the page explains each choice and links the research behind it.

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
