// Run: node --test tests/
const test = require("node:test");
const assert = require("node:assert/strict");
const U = require("../js/util.js");
const SRS = require("../js/srs.js");

test("normalize strips stress marks, ё, punctuation, case", () => {
  assert.equal(U.normalize("Молоко́!"), "молоко");
  assert.equal(U.normalize("Ещё"), "еще");
  assert.equal(U.normalize("  Hello,   World? "), "hello world");
  assert.equal(U.normalize("to eat", { lang: "en", loose: true }), "eat");
  assert.equal(U.normalize("the apple", { lang: "en", loose: true }), "apple");
  assert.equal(U.normalize("you (formal)"), "you");
});

test("checkAnswer exact, typo tolerance, alternatives", () => {
  assert.equal(U.checkAnswer("молоко", "молоко́", { lang: "ru" }).ok, true);
  assert.equal(U.checkAnswer("малоко", "молоко́", { lang: "ru", acceptTypos: true }).ok, true);
  assert.equal(U.checkAnswer("малоко", "молоко́", { lang: "ru", acceptTypos: false }).ok, false);
  assert.equal(U.checkAnswer("кот", "кит", { lang: "ru", acceptTypos: true }).ok, false, "3-letter words need exact match");
  assert.equal(U.checkAnswer("large", "big / large", { lang: "en", splitAlternatives: true }).ok, true);
  assert.equal(U.checkAnswer("eat", "to eat", { lang: "en", loose: true }).ok, true);
  assert.equal(U.checkAnswer("", "to eat", { lang: "en" }).ok, false);
  assert.equal(U.checkAnswer("isn't", ["is not", "isn't"], { lang: "en" }).ok, true);
});

test("compareWords scores spoken sentences", () => {
  const r = U.compareWords("my name is anna", "My name is Anna.", "en");
  assert.equal(r.score, 1);
  const r2 = U.compareWords("my name anna", "My name is Anna.", "en");
  assert.ok(r2.score > 0.7 && r2.score < 1);
  assert.equal(r2.words.find((w) => w.w === "is").ok, false);
  const r3 = U.compareWords("меня зовут анна", "Меня́ зову́т А́нна.", "ru");
  assert.equal(r3.score, 1);
});

test("tilesKey ignores punctuation/case", () => {
  assert.equal(U.tilesKey("Where do you live?"), U.tilesKey("where do you live"));
});

test("dayKey/addDays", () => {
  assert.equal(U.addDays("2026-01-31", 1), "2026-02-01");
  assert.equal(U.addDays("2026-03-01", -1), "2026-02-28");
});

test("SRS: new card learning steps then graduation", () => {
  const now = Date.now();
  let c = SRS.newCard(now);
  c = SRS.review(c, 3, now);
  assert.equal(c.state, "learn");
  assert.ok(c.due - now <= 10 * 60 * 1000);
  c = SRS.review(c, 3, now + 11 * 60 * 1000);
  assert.equal(c.state, "review");
  assert.equal(c.ivl, 1);
  const c2 = SRS.review(c, 3, c.due);
  assert.ok(c2.ivl >= 2, "interval grows");
  const c3 = SRS.review(c2, 1, c2.due);
  assert.equal(c3.state, "relearn");
  assert.equal(c3.lapses, 1);
  assert.ok(c3.ease < c2.ease);
  const c4 = SRS.review(c3, 3, c3.due);
  assert.equal(c4.state, "review");
});

test("SRS: easy on new card jumps to 4 days", () => {
  const c = SRS.review(SRS.newCard(0), 4, 0);
  assert.equal(c.state, "review");
  assert.equal(c.ivl, 4);
});

test("SRS: intervals grow geometrically and cap", () => {
  let c = SRS.review(SRS.newCard(0), 4, 0);
  let t = 0;
  for (let i = 0; i < 30; i++) { t = c.due; c = SRS.review(c, 3, t, () => 0.5); }
  assert.ok(c.ivl <= 365);
  assert.ok(SRS.isMastered(c));
  assert.equal(SRS.strength(c), 5);
});

test("SRS: strength ladder", () => {
  assert.equal(SRS.strength(null), 0);
  assert.equal(SRS.strength(SRS.newCard()), 0);
  assert.equal(SRS.strength({ state: "learn", reps: 1 }), 1);
  assert.equal(SRS.strength({ state: "review", ivl: 5 }), 3);
});

test("gradeFrom", () => {
  assert.equal(SRS.gradeFrom(false), 1);
  assert.equal(SRS.gradeFrom(true), 3);
  assert.equal(SRS.gradeFrom(true, { close: true }), 2);
});
