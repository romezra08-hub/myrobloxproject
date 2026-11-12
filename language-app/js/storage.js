// Profiles + progress persistence (localStorage, with an in-memory fallback).
(function (root) {
  const U = root.LSUtil;
  const KEY_PROFILES = "ls_profiles_v1";
  const KEY_ACTIVE = "ls_active_v1";
  const PKEY = (id) => "ls_progress_v1_" + id;

  const mem = {};
  const store = {
    get(k) { try { const v = root.localStorage.getItem(k); return v == null ? mem[k] || null : v; } catch (e) { return mem[k] || null; } },
    set(k, v) { mem[k] = v; try { root.localStorage.setItem(k, v); } catch (e) { /* private mode: keep in memory */ } },
    del(k) { delete mem[k]; try { root.localStorage.removeItem(k); } catch (e) {} },
  };

  function readJSON(k, fallback) {
    try { const v = store.get(k); return v ? JSON.parse(v) : fallback; } catch (e) { return fallback; }
  }

  function profiles() { return readJSON(KEY_PROFILES, []); }
  function saveProfiles(list) { store.set(KEY_PROFILES, JSON.stringify(list)); }

  function createProfile(p) {
    const list = profiles();
    const prof = Object.assign({
      id: "p" + Date.now().toString(36) + Math.random().toString(36).slice(2, 6),
      name: "?", avatar: "🙂", target: "en", ui: "he", help: "he",
      dailyGoal: 50, newPerDay: 8, ttsRate: 0.9, created: Date.now(),
    }, p);
    list.push(prof);
    saveProfiles(list);
    return prof;
  }

  function updateProfile(id, patch) {
    const list = profiles().map((p) => (p.id === id ? Object.assign({}, p, patch) : p));
    saveProfiles(list);
    return list.find((p) => p.id === id);
  }

  function deleteProfile(id) {
    saveProfiles(profiles().filter((p) => p.id !== id));
    store.del(PKEY(id));
    if (store.get(KEY_ACTIVE) === id) store.del(KEY_ACTIVE);
  }

  function activeId() { return store.get(KEY_ACTIVE); }
  function setActive(id) { store.set(KEY_ACTIVE, id); }
  function active() { const id = activeId(); return profiles().find((p) => p.id === id) || null; }

  function emptyProgress() {
    return {
      v: 1,
      cards: {},          // vocab + phrase SRS cards keyed by item id
      letters: {},        // letter -> { seen, right, wrong, traced, best }
      grammar: {},        // lessonId -> { best: 0..1, done: count, last }
      sounds: {},         // soundId -> { done, best }
      dialogues: {},      // dialogueId -> { best, done }
      xp: {},             // dayKey -> xp
      minutes: {},        // dayKey -> seconds studied
      newToday: {},       // dayKey -> count of new items introduced
      log: [],            // recent mistakes [{id, t}]
      achievements: {},
    };
  }

  const cache = {};
  function progress(id) {
    if (!cache[id]) cache[id] = Object.assign(emptyProgress(), readJSON(PKEY(id), {}));
    return cache[id];
  }
  let saveTimer = null;
  function saveProgress(id) {
    if (!cache[id]) return;
    clearTimeout(saveTimer);
    saveTimer = setTimeout(() => store.set(PKEY(id), JSON.stringify(cache[id])), 150);
  }
  function flush(id) {
    clearTimeout(saveTimer);
    if (cache[id]) store.set(PKEY(id), JSON.stringify(cache[id]));
  }

  function addXp(id, n) {
    const p = progress(id);
    const k = U.dayKey();
    p.xp[k] = (p.xp[k] || 0) + n;
    saveProgress(id);
  }

  function addSeconds(id, s) {
    const p = progress(id);
    const k = U.dayKey();
    p.minutes[k] = (p.minutes[k] || 0) + s;
    saveProgress(id);
  }

  // Current streak in days (today counts if studied; yesterday keeps the streak alive).
  function streak(id) {
    const p = progress(id);
    let k = U.dayKey();
    let n = 0;
    if (!p.xp[k]) k = U.addDays(k, -1);
    while (p.xp[k] > 0) { n++; k = U.addDays(k, -1); }
    return n;
  }

  function exportAll() {
    const out = { app: "ls", v: 1, exported: new Date().toISOString(), profiles: profiles(), progress: {} };
    out.profiles.forEach((p) => (out.progress[p.id] = progress(p.id)));
    return JSON.stringify(out);
  }

  function importAll(json) {
    const data = JSON.parse(json);
    if (!data || data.app !== "ls" || !Array.isArray(data.profiles)) throw new Error("bad file");
    const list = profiles();
    data.profiles.forEach((p) => {
      const i = list.findIndex((x) => x.id === p.id);
      if (i >= 0) list[i] = p; else list.push(p);
      cache[p.id] = Object.assign(emptyProgress(), data.progress[p.id] || {});
      store.set(PKEY(p.id), JSON.stringify(cache[p.id]));
    });
    saveProfiles(list);
  }

  function resetProgress(id) {
    cache[id] = emptyProgress();
    store.set(PKEY(id), JSON.stringify(cache[id]));
  }

  const api = { profiles, createProfile, updateProfile, deleteProfile, active, activeId, setActive, progress, saveProgress, flush, addXp, addSeconds, streak, exportAll, importAll, resetProgress, _store: store };
  root.LSStore = api;
  if (typeof module !== "undefined") module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
