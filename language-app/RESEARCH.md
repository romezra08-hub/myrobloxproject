# What the research says, and how this app uses it

Short version: the methods with the strongest evidence are **retrieval practice** (answering beats re-reading) and **spacing** (reviews spread over days). Everything in the app is built around these two. Below: each finding → the feature it led to.

## Core memory science
| Finding | Evidence | In the app |
|---|---|---|
| Retrieval practice: testing yourself beats re-reading | Classroom quizzing meta-analysis g≈0.50; classic retrieval experiments | Every new word is shown once, then **immediately asked** (multiple choice → typing → speaking) |
| Spacing: reviews spread over time | Cepeda et al. 2006 (317 experiments); Kim & Webb 2022 L2 meta-analysis (48 experiments, medium–large effects, longer gaps best on delayed tests) | SM-2 style scheduler with learning steps (1 min, 10 min, 1 day, then growing intervals) |
| Interleaving: mixing types/topics | First interleaving effect for foreign language (verb conjugation), benefit showed after 1 week, not same day | Daily lesson mixes reviews, new words, phrases, listening, speaking |
| Desirable difficulty: a word gets harder questions as it gets stronger | Retrieval effort strengthens memory | Ladder by strength: recognize → choose target word → listen → type → dictation → speak |
| Hypercorrection: confident errors get fixed well with feedback, but old errors come back after a week | Butterfield & Metcalfe 2001; Butler, Fazio & Marsh 2011 | Immediate feedback with audio; wrong items come back **in the same lesson** and in "Fix my mistakes" |
| Dual coding / multisensory | Recommended for older learners (Oxford 2018) | Emoji picture + audio + text + writing + speaking for every word |
| Mnemonics (keyword method) help short-term recall, long-term needs review | Raugh & Atkinson 1974; Wang et al. 1992 | Optional personal "memory hook" note on every word (writing your own hook also uses the generation effect) |
| Sleep helps new words stick | Memrise data: evening learners forget less; high-school experiment | "Bedtime review" card in the evening |

## Short videos (TikTok / Reels)
- Small studies show TikTok-style videos can raise vocabulary and engagement, but evidence is thin and mostly self-reported.
- **Warning from lab research:** fragmented clips that jump between *unrelated* topics lead to worse recall (≈41% vs 53%) and more overnight forgetting than continuous material. Brains struggle to connect the pieces.
- **Dual subtitles** (target language + native language at the same time) help vocabulary recall (Li 2016; Wang & Pellicer-Sánchez 2022), and highlighting the target word is a promising enhancement.

**So the app's "Reels" mode is:**
1. Full-screen vertical cards you swipe through, one word/phrase per card, big picture, audio that **plays automatically**, and **dual captions with the key word highlighted**.
2. **One topic per feed** (stays connected, no random jumping).
3. **A quick tap-quiz every few cards** (retrieval, not passive watching). Answers feed the same review scheduler.
4. **A finite feed** (~15 cards) ending with a recap, so it never becomes endless scrolling.

## Speaking
- Shadowing (listen and repeat immediately) improves fluency, rhythm and intelligibility; evidence for individual sounds is weaker.
  → **Shadowing** in conversations and pronunciation, plus the speech-recognition check for each word.
- Hebrew & Russian speakers learning English: no `th`, `w` → `v`, dropping `-ed`/`-s` endings, no present "to be", no articles (Russian) / only "ה" (Hebrew), strict English word order, vowel reduction.
- Hebrew & English speakers learning Russian: cases, **stress** (moves and changes meaning), ы, rolled р, soft consonants, vowel reduction, aspect.
  → Targeted grammar lessons with "fix the typical mistake" exercises, and a pronunciation trainer with minimal pairs. All Russian is shown with stress marks.

## Motivation
- Streaks really do keep people going (Silverman et al. 2023, J. Consumer Research), but they can become the goal in themselves and turn stressful. → Gentle streak with no punishments, no "lives", no timers.
- Older adult learners: mostly intrinsic motivation, more anxiety about failing, and they benefit from self-pacing and multisensory input. → Big buttons, an optional larger text size, encouraging feedback, no time pressure.
- Social support and relatedness raise motivation (self-determination theory). → **Family page**: both learners' streaks side by side, and **"Quiz each other"**. Mom knows Russian, so she can quiz her son; he knows English, so he can quiz her.
- Comprehensible input: stories and reading-while-listening help. → Conversations with audio and dual text.

## Sources
- Cognitive-science strategies review (spacing, retrieval, interleaving): https://par.nsf.gov/servlets/purl/10518320
- Spaced repetition overview: https://migaku.com/blog/language-fun/spaced-repetition-for-language-learners-a-2026-guide
- Short videos & memory: https://www.psypost.org/brain-scans-reveal-how-short-videos-impair-memory-and-disrupt-neural-pathways/ ; https://scienceblog.com/t-short-form-videos-may-make-newly-learned-information-harder-to-remember-but-the-experiment-tested-fragmented-travel-clips-rather-than-every-brief-lesson-or-every-persons-scrolling-habit/
- TikTok vocabulary studies: https://www.researchgate.net/publication/365367552_Is_TikTok_an_Effective_Technology_Tool_in_English_Vocabulary_Expansion ; https://www.researchgate.net/publication/389651047_Exploring_the_Impact_of_TikTok_on_Second-Language_Vocabulary_Acquisition_Benefits_Challenges_and_Learner_Perceptions
- Dual subtitles: https://era.ed.ac.uk/handle/1842/22013 ; https://www.cambridge.org/core/journals/recall/article/vocabulary-learning-through-viewing-dualsubtitled-videos-immediate-repetition-versus-spaced-repetition-as-an-enhancement-strategy/CD13EC929B3F7B7EEEFAC0E367325770
- Shadowing systematic review: https://ora.ox.ac.uk/objects/uuid:3104cae1-3a6b-400a-b173-de44384238d2
- Senior learners: https://www.teachingenglish.org.uk/professional-development/teachers/understanding-learners/how-maximise-language-learning-senior
- Streaks: https://knowledge.insead.edu/marketing/consumer-streaks-are-motivating-the-key-is-keeping-them-alive-19011 ; https://thedecisionlab.com/insights/consumer-insights/streak-creep-the-perils-of-too-much-gamification
- Keyword mnemonic: https://suppescorpus.stanford.edu/sites/g/files/sbiybj32751/files/media/file/imsss_224.pdf ; https://archive.memory-key.com/research/Wang95
- Sleep & vocabulary: https://www.acamh.org/research-digest/do-we-remember-more-when-learning-before-bedtime/ ; https://pmc.ncbi.nlm.nih.gov/articles/PMC7137956
- Hypercorrection: https://pubmed.ncbi.nlm.nih.gov/21989771/
- Graded input / reading-while-listening: https://www2.hawaii.edu/~readfl/rfl/October2008/brown/brown.html
- L1-specific errors: https://boldvoice.com/blog/english-pronunciation-hebrew-speakers ; https://llexi.com/l1-errors/common-english-errors-russian-speakers/ ; https://www.verbalplanet.com/learn-russian/blog/mistakes-english-speakers-make-when-learning-russian.asp

## Habit-forming design (Hook model, used for good)
Nir Eyal's Hook model has four steps: **trigger → action → variable reward → investment**. It draws on Skinner's variable reinforcement and BJ Fogg's behavior model. Habits form gradually, and how long it takes varies a lot from person to person (Lally et al.; there's no real "21 days" rule).
- **Trigger:** a daily reminder (calendar event with an alarm) plus an "if-then plan" ("After my morning coffee I'll do one lesson"). Implementation intentions are one of the best-supported habit tools (Gollwitzer).
- **Action:** one big "Start lesson" button, and a lesson takes about 10 minutes.
- **Variable reward:** a **mystery bonus** at the end of each lesson (random bonus XP, a fun fact or a surprise word) and varied praise. Rewards stay tied to real learning.
- **Investment:** levels that grow with XP, your own memory hooks for words, the family board.
- **Ethics:** no guilt trips and no endless feed. Once the daily goal is met the app says "rest helps memory".
Sources: https://umbrex.com/?p=242458 ; https://uxmag.com/?p=21127

## Round 3
- **Pretesting / guess first:** guessing a word's meaning *before* studying it improves later memory, even when the guess is wrong (Potts & Shanks 2014; Chua & Pan 2026 tested word↔picture guessing like language apps use; older adults benefit too). → Every new word now starts with a no-penalty "Guess!" question, then the reveal, then a harder retrieval.
- **Review snowball:** there's no proven "best" number of new words a day, but practitioners agree on 10–20, and the real limit is the review load. → When more than 30 reviews are due, the daily lesson automatically cuts new words (minimum 2).
- **Chunks (formulaic language):** using ready-made phrases goes with better fluency (Boers & Lindstromberg 2012), though the best way to teach them is still unclear. → The phrase builder, Reels phrase feeds and role-play conversations all practice whole chunks.
Sources: https://sc-pan.github.io/pdf/CP_2026.pdf ; https://link.springer.com/article/10.3758/s13421-021-01218-6 ; https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9379275/ ; https://actualfluency.com/spaced-repetition-snowball-how-to-become-overwhelmed-by-learning-vocabulary

## Round 4
- **Self-reference:** Hebrew speakers learning English remembered words better (immediately and after a week) when they related them to themselves (Pruss, Karni & Prior 2025, Psychonomic Bulletin & Review). One earlier study found no advantage over imagery. → New words ask "Is this word part of your life? 👍/👎".
- **High-variability phonetic training:** a meta-analysis of 79 studies supports training listening with varied input. The benefit of multiple talkers specifically is small and mixed (Zhang et al. 2021). → Listening questions and the similar-pairs quiz use varied voices and speeds.
- **Production beats recognition:** writing or typing words beats multiple choice. A handwriting advantage over typing isn't established (Van Hove 2017; Ose Askvik et al. 2021 EEG). → Typing questions now appear earlier in a word's progression.
Sources: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12426137/ ; https://www.cambridge.org/core/product/6ABB8C1F32D88D53EA8D05A4565E76F6/core-reader ; https://experts.umn.edu/en/publications/the-role-of-talker-variability-in-nonnative-phonetic-learning-a-s/ ; https://scipedia.com/public/Van-Hove_et_al_2017a ; https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8222525/
