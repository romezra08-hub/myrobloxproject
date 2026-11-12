// End-to-end smoke test with Playwright. Run: node tests/e2e.js [outDir]
// Serves the app, creates both learner profiles, runs lessons, visits every screen,
// takes phone-size screenshots and fails on any page error.
const { chromium } = require("playwright");
const http = require("http");
const fs = require("fs");
const path = require("path");

const ROOT = path.join(__dirname, "..");
const OUT = process.argv[2] || path.join(ROOT, "tests", "screens");
fs.mkdirSync(OUT, { recursive: true });
const TYPES = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".svg": "image/svg+xml", ".webmanifest": "application/manifest+json", ".json": "application/json" };

function serve() {
  return new Promise((resolve) => {
    const srv = http.createServer((req, res) => {
      let p = decodeURIComponent(req.url.split("?")[0]);
      if (p === "/") p = "/index.html";
      const f = path.join(ROOT, p);
      if (!f.startsWith(ROOT) || !fs.existsSync(f)) { res.writeHead(404); return res.end(); }
      res.writeHead(200, { "content-type": TYPES[path.extname(f)] || "application/octet-stream" });
      fs.createReadStream(f).pipe(res);
    });
    srv.listen(0, () => resolve(srv));
  });
}

const errors = [];
async function shot(page, name) { await page.screenshot({ path: path.join(OUT, name + ".png"), fullPage: false }); }

// Answer whatever exercise is on screen (sometimes right, sometimes wrong).
async function answerStep(page, i) {
  const ex = await page.$(".ex");
  if (!ex) return false;
  const cls = await ex.getAttribute("class");
  if (/\bmatch\b/.test(cls)) {
    // solve by ids
    const left = await page.$$(".match-item[data-side=L]");
    for (const l of left) {
      const id = await l.getAttribute("data-id");
      await l.click();
      await page.click(`.match-item[data-side=R][data-id="${id}"]`);
    }
  } else if (/\bmc\b|letter-quiz|gchoice/.test(cls)) {
    const opts = await page.$$(".option");
    if (opts.length) await opts[i % opts.length].click();
  } else if (/\btype\b|dictation|gfill/.test(cls)) {
    const inp = await page.$("input.answer");
    if (inp) { await inp.fill(i % 2 ? "abc" : "тест"); await page.click(".main-btn"); }
  } else if (/\bbuild\b|gorder/.test(cls)) {
    const tiles = await page.$$(".tiles-bank .tile:not(.used)");
    for (const t of tiles.slice(0, 3)) await t.click();
    await page.click(".main-btn");
  } else {
    // intro / speak / letter intro: main button (Got it / Skip)
    await page.click(".main-btn");
  }
  await page.waitForTimeout(60);
  // advance past feedback
  const btn = await page.$(".main-btn:not([disabled])");
  if (btn && (await btn.getAttribute("data-mode")) === "next") await btn.click();
  return true;
}

async function runLesson(page, tag, maxSteps) {
  let n = 0;
  while (n < (maxSteps || 120)) {
    if (await page.$(".summary")) break;
    const ok = await answerStep(page, n);
    if (!ok) break;
    if (n === 2) await shot(page, `${tag}-step`);
    n++;
  }
  await page.waitForTimeout(100);
  await shot(page, `${tag}-end`);
  return n;
}

(async () => {
  const srv = await serve();
  const base = `http://localhost:${srv.address().port}/index.html`;
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1, hasTouch: true });
  const page = await ctx.newPage();
  page.on("pageerror", (e) => errors.push("pageerror: " + e.message));
  page.on("console", (m) => { if (m.type() === "error" && !/fonts\.g|ERR_|Failed to load resource/.test(m.text())) errors.push("console: " + m.text()); });
  await page.route(/fonts\.(googleapis|gstatic)\.com/, (r) => r.abort());

  await page.goto(base);
  await page.waitForSelector(".welcome");
  await shot(page, "01-welcome");

  // --- Mom: learns English ---
  await page.click(".preset >> nth=0");
  await page.waitForSelector(".home");
  await shot(page, "02-home-mom");
  await page.click(".hero-card");
  await page.waitForSelector(".session");
  await shot(page, "03-lesson-first");
  const steps = await runLesson(page, "04-mom-daily");
  console.log("mom daily lesson steps:", steps);
  await page.click(".main-btn");
  await page.waitForSelector(".home");

  const routes = ["learn", "alphabet", "letter/A", "writing", "writing/B", "words", "topic/food", "phrases", "grammar", "sounds", "dialogues", "progress", "settings", "family", "reels", "mistakes"];
  for (const r of routes) {
    await page.goto(base + "#/" + r);
    await page.waitForTimeout(250);
    await shot(page, "mom-" + r.replace(/\//g, "_"));
  }
  // a grammar lesson + practice
  const g = await page.evaluate(() => (LS_DATA.grammar || []).find((x) => x.target === "en"));
  if (g) {
    await page.goto(base + "#/grammar/" + g.id);
    await page.waitForTimeout(200);
    await shot(page, "mom-grammar-lesson");
    await page.click(".btn.primary.wide");
    await runLesson(page, "mom-grammar-practice", 40);
  }
  // reels feed
  await page.goto(base + "#/reels/topic/food");
  await page.waitForTimeout(500);
  await shot(page, "mom-reels-1");
  await page.keyboard.press("ArrowDown");
  await page.waitForTimeout(700);
  await page.keyboard.press("ArrowDown");
  await page.waitForTimeout(700);
  await page.keyboard.press("ArrowDown");
  await page.waitForTimeout(700);
  await shot(page, "mom-reels-quiz");
  // dialogue
  const d = await page.evaluate(() => (LS_DATA.dialogues || [])[0] && LS_DATA.dialogues[0].id);
  if (d) { await page.goto(base + "#/dialogue/" + d); await page.waitForTimeout(250); await shot(page, "mom-dialogue"); }
  const s = await page.evaluate(() => ((LS_DATA.sounds || {}).en || [])[0] && LS_DATA.sounds.en[0].id);
  if (s) { await page.goto(base + "#/sound/" + s); await page.waitForTimeout(250); await shot(page, "mom-sound"); }
  // writing: draw a stroke and score
  await page.goto(base + "#/writing/A");
  await page.waitForSelector(".trace-canvas");
  const box = await (await page.$(".trace-canvas")).boundingBox();
  await page.mouse.move(box.x + box.width * 0.3, box.y + box.height * 0.8);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * 0.5, box.y + box.height * 0.25, { steps: 10 });
  await page.mouse.move(box.x + box.width * 0.7, box.y + box.height * 0.8, { steps: 10 });
  await page.mouse.up();
  await page.click(".btn.primary");
  await page.waitForTimeout(200);
  await shot(page, "mom-writing-scored");
  console.log("trace score:", await page.textContent(".trace-score"));

  // --- Son: learns Russian ---
  await page.goto(base + "#/setup");
  await page.waitForSelector(".form");
  await page.fill(".text-in", "Rom");
  await page.click(".seg >> nth=0 >> .seg-btn >> nth=1"); // Russian
  await page.click(".btn.primary.wide");
  await page.waitForSelector(".home");
  await shot(page, "10-home-son");
  await page.click(".hero-card");
  await page.waitForSelector(".session");
  const steps2 = await runLesson(page, "11-son-daily");
  console.log("son daily lesson steps:", steps2);
  // second lesson to exercise reviews path
  await page.click(".main-btn");
  await page.waitForSelector(".home");
  await page.click(".hero-card");
  await runLesson(page, "12-son-daily2");
  for (const r of ["alphabet", "letter/Ж", "writing/Ж", "topic/basics", "grammar", "sounds", "progress", "family", "reels/topic/basics"]) {
    await page.goto(base + "#/" + encodeURI(r));
    await page.waitForTimeout(300);
    await shot(page, "son-" + r.replace(/\//g, "_"));
  }
  const gr = await page.evaluate(() => (LS_DATA.grammar || []).find((x) => x.target === "ru"));
  if (gr) {
    await page.goto(base + "#/grammar/" + gr.id);
    await page.waitForTimeout(200);
    await shot(page, "son-grammar-lesson");
    await page.click(".btn.primary.wide");
    await runLesson(page, "son-grammar-practice", 40);
  }
  // family quiz
  await page.goto(base + "#/family");
  await page.waitForTimeout(200);
  const famBtns = await page.$$(".family .row.wrap .btn");
  if (famBtns[0]) { await famBtns[0].click(); await page.waitForTimeout(150); await shot(page, "son-family-quiz"); }

  // desktop + dark mode quick check
  const ctx2 = await browser.newContext({ viewport: { width: 1200, height: 900 }, colorScheme: "dark" });
  const p2 = await ctx2.newPage();
  p2.on("pageerror", (e) => errors.push("pageerror(desktop): " + e.message));
  await p2.route(/fonts\.(googleapis|gstatic)\.com/, (r) => r.abort());
  await p2.goto(base);
  await p2.waitForSelector(".welcome");
  await p2.click(".preset >> nth=1");
  await p2.waitForSelector(".home");
  await p2.screenshot({ path: path.join(OUT, "20-desktop-dark.png") });

  // horizontal overflow check on phone
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
  if (overflow) errors.push("horizontal overflow on phone");

  await browser.close();
  srv.close();
  console.log(errors.length ? "ERRORS:\n" + errors.join("\n") : "E2E OK — no page errors");
  process.exit(errors.length ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(1); });
