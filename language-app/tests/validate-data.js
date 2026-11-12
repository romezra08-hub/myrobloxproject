// Validates all content files. Run: node tests/validate-data.js
const fs = require("fs");
const path = require("path");
const U = require("../js/util.js");

global.window = global;
const dir = path.join(__dirname, "..", "data");
const files = ["topics.js", "vocab1.js", "vocab2.js", "phrases.js", "dialogues.js", "grammar_en.js", "grammar_ru.js", "alphabet.js", "sounds.js"];
const errors = [], warnings = [];
files.forEach((f) => {
  const p = path.join(dir, f);
  if (!fs.existsSync(p)) { errors.push(`missing file ${f}`); return; }
  try { require(p); } catch (e) { errors.push(`${f}: ${e.message}`); }
});
const D = global.LS_DATA || {};

// Russian stress check: every word with 2+ vowels should have exactly one U+0301 or contain ё.
const RU_UNSTRESSED_OK = new Set(["это", "что", "чтобы", "или", "через", "перед", "между", "около", "надо", "нибудь", "либо", "будто", "ведь", "даже", "уже", "ещё", "оно", "мои", "твои", "свои", "ему", "ими", "его", "её", "сегодня", "под", "над", "без", "при", "про"]);
function checkRu(text, where) {
  if (!text) return;
  String(text).split(/[\s,.!?;:()«»"—–\-\/]+/).filter(Boolean).forEach((w) => {
    if (!/[а-яё]/i.test(w)) return;
    const vowels = U.ruVowelCount(w);
    const marks = (w.match(/́/g) || []).length;
    const hasYo = /ё/i.test(w);
    if (marks > 1) warnings.push(`${where}: "${w}" has ${marks} stress marks`);
    if (vowels >= 2 && marks === 0 && !hasYo && !RU_UNSTRESSED_OK.has(U.stripStress(w).toLowerCase())) warnings.push(`${where}: "${w}" missing stress`);
    if (hasYo && marks > 0) warnings.push(`${where}: "${w}" has ё and an accent`);
    if (/́/.test(w) && !/[аеиоуыэюяАЕИОУЫЭЮЯ]́/.test(w)) errors.push(`${where}: "${w}" accent not after a vowel`);
  });
}

// vocab
const ids = new Set();
const topicIds = new Set((D.topics || []).map((t) => t.id));
const seenWords = {};
(D.vocab || []).forEach((v, i) => {
  const where = `vocab[${v.id || i}]`;
  if (!v.id) errors.push(`${where}: no id`);
  if (ids.has(v.id)) errors.push(`${where}: duplicate id`);
  ids.add(v.id);
  ["en", "ru", "he", "topic"].forEach((k) => { if (!v[k]) errors.push(`${where}: missing ${k}`); });
  if (v.topic && !topicIds.has(v.topic)) errors.push(`${where}: unknown topic ${v.topic}`);
  if (v.g && !["m", "f", "n", "pl"].includes(v.g)) errors.push(`${where}: bad gender ${v.g}`);
  ["ru", "ruEx", "ruPf", "ruPres"].forEach((k) => checkRu(v[k], `${where}.${k}`));
  if (!v.enEx || !v.ruEx || !v.heEx) warnings.push(`${where}: missing example`);
  const key = v.topic + "|" + U.normalize(v.en);
  if (seenWords[key]) warnings.push(`${where}: same English as ${seenWords[key]}`);
  seenWords[key] = v.id;
});

// phrases
const sitIds = new Set((D.situations || []).map((s) => s.id));
(D.phrases || []).forEach((p, i) => {
  const where = `phrase[${p.id || i}]`;
  if (ids.has(p.id)) errors.push(`${where}: duplicate id`);
  ids.add(p.id);
  ["en", "ru", "he", "sit"].forEach((k) => { if (!p[k]) errors.push(`${where}: missing ${k}`); });
  if (p.sit && !sitIds.has(p.sit)) errors.push(`${where}: unknown situation ${p.sit}`);
  checkRu(p.ru, where);
  if (U.tokenize(p.en).length > 10 || U.tokenize(p.ru).length > 10) warnings.push(`${where}: long for tiles`);
});

// dialogues
(D.dialogues || []).forEach((d) => {
  const where = `dialogue[${d.id}]`;
  if (!d.title || !d.title.en || !d.title.ru || !d.title.he) errors.push(`${where}: title`);
  (d.lines || []).forEach((l, i) => {
    ["en", "ru", "he"].forEach((k) => { if (!l[k]) errors.push(`${where}.line${i}: missing ${k}`); });
    if (!["A", "B"].includes(l.who)) errors.push(`${where}.line${i}: who`);
    checkRu(l.ru, `${where}.line${i}`);
  });
});

// grammar
const gids = new Set();
(D.grammar || []).forEach((g) => {
  const where = `grammar[${g.id}]`;
  if (gids.has(g.id)) errors.push(`${where}: duplicate`);
  gids.add(g.id);
  const expl = g.target === "en" ? ["he", "ru"] : ["he", "en"];
  expl.forEach((l) => { if (!g.explain || !g.explain[l]) errors.push(`${where}: explain.${l} missing`); });
  (g.examples || []).forEach((e, i) => { if (g.target === "ru") checkRu(e.t, `${where}.ex${i}`); expl.forEach((l) => { if (!e[l]) warnings.push(`${where}.ex${i}: missing ${l}`); }); });
  (g.exercises || []).forEach((x, i) => {
    const w = `${where}.x${i}`;
    if (!["choice", "fill", "order", "fix"].includes(x.type)) errors.push(`${w}: type ${x.type}`);
    if (x.type === "choice") {
      if (!Array.isArray(x.options) || typeof x.answer !== "number" || x.answer < 0 || x.answer >= x.options.length) errors.push(`${w}: bad choice`);
    }
    if (x.type === "fill") {
      if ((x.q.match(/___/g) || []).length !== 1) errors.push(`${w}: fill needs one ___`);
      if (!Array.isArray(x.answer) || !x.answer.length) errors.push(`${w}: fill answer`);
    }
    if (x.type === "fix" && (!Array.isArray(x.answer) || !x.answer.length)) errors.push(`${w}: fix answer`);
    if (x.type === "fix" && Array.isArray(x.answer) && x.answer.some((a) => U.normalize(a) === U.normalize(x.q))) errors.push(`${w}: fix answer equals question`);
    if (x.type === "order" && typeof x.answer !== "string") errors.push(`${w}: order answer`);
    if (g.target === "ru") { checkRu(x.q, w); [].concat(x.answer).forEach((a) => typeof a === "string" && checkRu(a, w)); (x.options || []).forEach((o) => checkRu(o, w)); }
    if (!x.tr) warnings.push(`${w}: no tr`);
  });
  if ((g.exercises || []).length < 6) warnings.push(`${where}: few exercises`);
});

// alphabet
const A = D.alphabet || {};
if ((A.en || []).length !== 26) errors.push(`alphabet.en has ${(A.en || []).length}`);
if ((A.ru || []).length !== 33) errors.push(`alphabet.ru has ${(A.ru || []).length}`);
["en", "ru"].forEach((lang) => {
  const all = (A[lang] || []).map((l) => l.upper);
  const inGroups = [].concat(...(((D.alphabetLessons || {})[lang]) || []));
  all.forEach((u) => { const n = inGroups.filter((x) => x === u).length; if (n !== 1) errors.push(`alphabetLessons.${lang}: ${u} appears ${n} times`); });
  (A[lang] || []).forEach((l) => {
    if (!l.sound) errors.push(`alphabet.${lang}.${l.upper}: no sound`);
    if (lang === "ru" && l.example) checkRu(l.example.word, `alphabet.ru.${l.upper}`);
  });
});
// sounds
["en", "ru"].forEach((lang) => ((D.sounds || {})[lang] || []).forEach((s) => {
  if (!s.tip || !s.title) errors.push(`sounds.${s.id}: missing tip/title`);
  if (lang === "ru") { (s.pairs || []).forEach((p) => p.forEach((w) => checkRu(w, `sounds.${s.id}`))); (s.words || []).forEach((w) => checkRu(w, `sounds.${s.id}`)); }
}));

const counts = {
  vocab: (D.vocab || []).length, phrases: (D.phrases || []).length, dialogues: (D.dialogues || []).length,
  grammar_en: (D.grammar || []).filter((g) => g.target === "en").length, grammar_ru: (D.grammar || []).filter((g) => g.target === "ru").length,
  exercises: (D.grammar || []).reduce((s, g) => s + (g.exercises || []).length, 0),
  sounds: ((D.sounds || {}).en || []).length + ((D.sounds || {}).ru || []).length,
};
console.log("counts", JSON.stringify(counts));
console.log(`errors: ${errors.length}, warnings: ${warnings.length}`);
errors.slice(0, 80).forEach((e) => console.log("ERROR", e));
if (process.argv.includes("--warn")) warnings.slice(0, 200).forEach((w) => console.log("warn", w));
process.exit(errors.length ? 1 : 0);
