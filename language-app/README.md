# Learn Together 🗣️

A family language app: **Mom** (Hebrew + Russian) learns **English**, and her son (Hebrew + English) learns **Russian**.
The interface is in Hebrew, Russian or English, and every explanation comes in a language you already know.

## What's inside
| Section | What you do |
|---|---|
| 🎯 Daily lesson | ~10 min mix: reviews due today, 8 new words (see → hear → answer), phrases, speaking |
| 🎬 Reels | TikTok-style swipe feed per topic, auto audio, dual captions, a quick quiz every 3 cards |
| 🔤 Alphabet | All letters with sounds, example words, reading rules, letter quizzes |
| ✍️ Handwriting | Trace letters with your finger (print or cursive), then write alone, with a score |
| 📖 Vocabulary | ~620 words in 18 topics with pictures, audio, examples, Russian stress marks |
| 💬 Phrases | 164 everyday sentences in 12 situations: build them from word tiles, listen, say them |
| 🧩 Grammar | 17 English + 18 Russian lessons aimed at Hebrew/Russian speakers' typical mistakes, 350 exercises |
| 👄 Pronunciation | The hard sounds (th, w/v, ы, р, soft signs, stress…), similar-sounding pairs, speaking check |
| 🎭 Conversations | 13 role-plays: the app speaks one side and you answer out loud |
| 👨‍👩‍👦 Family | Both learners' streaks, and "quiz each other" (Mom knows Russian, her son knows English) |
| 📈 Progress | Streak, level, 30-day chart, upcoming reviews, hardest words |

It's built on learning research (spaced repetition, retrieval practice, interleaving, shadowing, dual subtitles, habit loops). See [RESEARCH.md](RESEARCH.md).

## Run it
Open `index.html` in Chrome, or serve the folder (`python3 -m http.server`) and open it on a phone (it installs with "Add to Home screen").
Progress is saved in the browser. Use Settings → Back up to move it to another device.
Speech recognition works in Chrome and Edge. For voices, the device needs English and Russian text-to-speech voices installed.

## Develop
- `node --test tests/`: unit tests (answer checking, spaced repetition)
- `node tests/validate-data.js`: checks all content (stress marks, translations, exercises)
- `node tests/e2e.js`: clicks through the whole app in a phone-size browser and saves screenshots
- `python3 build-artifact.py`: builds a single-file `dist/index.html`
