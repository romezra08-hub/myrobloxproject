window.LS_DATA = window.LS_DATA || {};
LS_DATA.grammar = LS_DATA.grammar || [];

LS_DATA.grammar.push({
  id: "ru_no_to_be", target: "ru", level: 1, order: 1,
  title: { he: "אין 'להיות' בהווה, ו־э́то", en: "No 'to be' in the present & э́то", ru: "Без глаго́ла «быть» и сло́во «э́то»" },
  explain: {
    he: "<p>ברוסית אין פועל 'להיות' בהווה — בדיוק כמו בעברית! אומרים <b>Я студе́нт</b> — 'אני סטודנט', בלי שום מילה באמצע.</p><p>כששני חלקי המשפט הם שמות עצם, בכתב שמים לפעמים מקף במקום 'הוא/היא': <b>Мой па́па — врач.</b> (אבא שלי רופא.)</p><p><b>Э́то</b> פירושו 'זה / זאת / אלה'. המילה לא משתנה: <b>Э́то мой брат</b> (זה אח שלי), <b>Э́то мои́ кни́ги</b> (אלה הספרים שלי).</p><ul><li><b>Кто э́то?</b> — מי זה? (לאנשים ולבעלי חיים)</li><li><b>Что э́то?</b> — מה זה? (לחפצים)</li></ul><p>ברוסית גם <b>אין יידוע</b> — אין 'ה' ואין a/the כמו באנגלית. <b>Э́то дом</b> = 'זה בית' או 'זה הבית'. ההקשר מסביר.</p>",
    en: "<p>In Russian the verb <b>'to be'</b> is simply dropped in the present tense — exactly like in Hebrew! Hebrew says 'אני סטודנט' and Russian says <b>Я студе́нт</b> (literally 'I student').</p><p>When both parts are nouns, writing often puts a dash where English has 'is': <b>Мой па́па — врач.</b> (My dad is a doctor.)</p><p><b>Э́то</b> means 'this is / that is / it is / these are'. It never changes: <b>Э́то мой брат</b> (This is my brother), <b>Э́то мои́ кни́ги</b> (These are my books).</p><ul><li><b>Кто э́то?</b> — Who is this? (people and animals)</li><li><b>Что э́то?</b> — What is this? (things)</li></ul><p>Russian also has <b>no articles</b> — no 'a' and no 'the'. <b>Э́то дом</b> = 'This is a house' or 'This is the house'. Context tells you which.</p>"
  },
  examples: [
    { t: "Я студе́нт.", he: "אני סטודנט.", en: "I am a student." },
    { t: "Э́то мой брат.", he: "זה אח שלי.", en: "This is my brother." },
    { t: "Мой па́па — врач.", he: "אבא שלי רופא.", en: "My dad is a doctor." },
    { t: "Что э́то? — Э́то кни́га.", he: "מה זה? — זה ספר.", en: "What is this? — It's a book." },
    { t: "Москва́ — большо́й го́род.", he: "מוסקבה היא עיר גדולה.", en: "Moscow is a big city." }
  ],
  exercises: [
    { type: "choice", q: "___ мой дом.", options: ["Э́то", "Есть", "Он есть"], answer: 0,
      tr: { he: "זה הבית שלי.", en: "This is my house." },
      why: { he: "Э́то = 'זה'. אין צורך בפועל 'להיות'.", en: "Э́то = 'this is'. No verb 'to be' is needed." } },
    { type: "choice", q: "Ма́ма ___ врач.", options: ["—", "есть", "э́то есть"], answer: 0,
      tr: { he: "אמא רופאה.", en: "Mom is a doctor." },
      why: { he: "בין שני שמות עצם כותבים מקף, לא 'есть'.", en: "Between two nouns you write a dash, not 'есть'." } },
    { type: "choice", q: "Кто э́то?", options: ["Э́то Ива́н.", "Э́то есть Ива́н.", "Ива́н э́то есть."], answer: 0,
      tr: { he: "מי זה?", en: "Who is this?" },
      why: { he: "עונים פשוט: Э́то + שם. בלי 'есть'.", en: "Just answer Э́то + name, without 'есть'." } },
    { type: "fill", q: "___ моя́ сестра́.", answer: ["Э́то", "Это"],
      tr: { he: "זו אחותי.", en: "This is my sister." },
      why: { he: "Э́то משמש גם לזכר וגם לנקבה — הוא לא משתנה.", en: "Э́то is used for any gender — it never changes." } },
    { type: "fill", q: "Кто ___? — Э́то мой друг.", answer: ["э́то", "это"],
      tr: { he: "מי זה? — זה החבר שלי.", en: "Who is this? — This is my friend." },
      why: { he: "Кто э́то? = מי זה?", en: "Кто э́то? = Who is this?" } },
    { type: "fill", q: "Что э́то? — Э́то ___. (table)", answer: ["стол"],
      tr: { he: "מה זה? — זה שולחן.", en: "What is this? — It's a table." },
      why: { he: 'שולחן = стол. אין מילה ל־"a".', en: "Table = стол. There is no word for 'a'." } },
    { type: "order", answer: "Э́то мой брат.",
      tr: { he: "זה אח שלי.", en: "This is my brother." } },
    { type: "order", answer: "Он о́чень хоро́ший учи́тель.",
      tr: { he: "הוא מורה טוב מאוד.", en: "He is a very good teacher." } },
    { type: "fix", q: "Я есть студе́нт.", answer: ["Я студе́нт."],
      tr: { he: "אני סטודנט.", en: "I am a student." },
      why: { he: "בהווה לא אומרים 'есть' במובן 'הוא/אני'. כמו בעברית: 'אני סטודנט'.", en: "In the present, 'to be' is dropped. Just: Я студе́нт." } },
    { type: "fix", q: "Э́то есть мой дом.", answer: ["Э́то мой дом."],
      tr: { he: "זה הבית שלי.", en: "This is my house." },
      why: { he: "Э́то כבר אומר 'זה'. לא מוסיפים 'есть'.", en: "Э́то already means 'this is'. Don't add 'есть'." } }
  ]
});

LS_DATA.grammar.push({
  id: "ru_gender", target: "ru", level: 1, order: 2,
  title: { he: "מין של שמות עצם", en: "Noun gender", ru: "Род существи́тельных" },
  explain: {
    he: "<p>כמו בעברית, לכל שם עצם ברוסית יש מין. אבל ברוסית יש <b>שלושה</b> מינים: זכר, נקבה ו<b>סתמי</b> (neuter). את המין מזהים לפי הסוף של המילה:</p><table><tr><th>מין</th><th>סוף</th><th>דוגמה</th><th>'הוא/היא'</th></tr><tr><td>זכר</td><td>עיצור, ‎-й</td><td>стол, музе́й</td><td>он</td></tr><tr><td>נקבה</td><td>‎-а, ‎-я</td><td>ма́ма, неде́ля</td><td>она́</td></tr><tr><td>סתמי</td><td>‎-о, ‎-е</td><td>окно́, мо́ре</td><td>оно́</td></tr></table><p>מילים שנגמרות ב־<b>ь</b> (סימן רך) יכולות להיות זכר או נקבה — צריך לזכור: <b>слова́рь</b> (מילון) זכר, <b>дверь</b> (דלת) נקבה.</p><p>שימו לב: <b>па́па</b> ו־<b>дя́дя</b> נגמרים ב־‎-а/-я, אבל הם זכר, כי הם גברים.</p><p>גם חפצים הם 'הוא' או 'היא' — בדיוק כמו בעברית: Где кни́га? — Вот <b>она́</b>.</p>",
    en: "<p>Like Hebrew, every Russian noun has a gender. But Russian has <b>three</b>: masculine, feminine and <b>neuter</b>. You can usually tell the gender from the ending:</p><table><tr><th>Gender</th><th>Ending</th><th>Example</th><th>'it'</th></tr><tr><td>masculine</td><td>consonant, -й</td><td>стол, музе́й</td><td>он</td></tr><tr><td>feminine</td><td>-а, -я</td><td>ма́ма, неде́ля</td><td>она́</td></tr><tr><td>neuter</td><td>-о, -е</td><td>окно́, мо́ре</td><td>оно́</td></tr></table><p>Nouns ending in the soft sign <b>ь</b> can be masculine or feminine — memorize them: <b>слова́рь</b> (dictionary) is masculine, <b>дверь</b> (door) is feminine.</p><p>Careful: <b>па́па</b> and <b>дя́дя</b> end in -а/-я but are masculine, because they are men.</p><p>Things are 'he' or 'she', just like in Hebrew: Где кни́га? — Вот <b>она́</b>. (Where is the book? — Here it is.)</p>"
  },
  examples: [
    { t: "Э́то стол. Он большо́й.", he: "זה שולחן. הוא גדול.", en: "This is a table. It is big." },
    { t: "Где ла́мпа? — Вот она́.", he: "איפה המנורה? — הנה היא.", en: "Where is the lamp? — Here it is." },
    { t: "Э́то окно́. Оно́ откры́то.", he: "זה חלון. הוא פתוח.", en: "This is a window. It is open." },
    { t: "Па́па до́ма. Он отдыха́ет.", he: "אבא בבית. הוא נח.", en: "Dad is at home. He is resting." },
    { t: "Мо́ре тёплое.", he: "הים חמים.", en: "The sea is warm." }
  ],
  exercises: [
    { type: "choice", q: "Где кни́га? — Вот ___.", options: ["он", "она́", "оно́"], answer: 1,
      tr: { he: "איפה הספר? — הנה הוא.", en: "Where is the book? — Here it is." },
      why: { he: "кни́га נגמרת ב־‎-а — נקבה, לכן она́. (בעברית 'ספר' זכר, ברוסית נקבה!)", en: "кни́га ends in -а, so it is feminine: она́." } },
    { type: "choice", q: "Где окно́? — Вот ___.", options: ["он", "она́", "оно́"], answer: 2,
      tr: { he: "איפה החלון? — הנה הוא.", en: "Where is the window? — Here it is." },
      why: { he: "окно́ נגמרת ב־‎-о — סתמי, לכן оно́.", en: "окно́ ends in -о, so it is neuter: оно́." } },
    { type: "choice", q: "Где слова́рь? — Вот ___.", options: ["он", "она́", "оно́"], answer: 0,
      tr: { he: "איפה המילון? — הנה הוא.", en: "Where is the dictionary? — Here it is." },
      why: { he: "слова́рь הוא זכר. מילים עם ь צריך לזכור.", en: "слова́рь is masculine. Nouns in -ь must be memorized." } },
    { type: "choice", q: "Па́па до́ма? — Да, ___ до́ма.", options: ["он", "она́", "оно́"], answer: 0,
      tr: { he: "אבא בבית? — כן, הוא בבית.", en: "Is Dad home? — Yes, he is home." },
      why: { he: "па́па נגמר ב־‎-а, אבל הוא גבר — לכן он.", en: "па́па ends in -а but is a man, so он." } },
    { type: "fill", q: "Где мо́ре? — Вот ___.", answer: ["оно́", "оно"],
      tr: { he: "איפה הים? — הנה הוא.", en: "Where is the sea? — Here it is." },
      why: { he: "мо́ре נגמר ב־‎-е — סתמי.", en: "мо́ре ends in -е, so it is neuter." } },
    { type: "fill", q: "Где ма́ма? — ___ на рабо́те.", answer: ["Она́", "Она"],
      tr: { he: "איפה אמא? — היא בעבודה.", en: "Where is Mom? — She is at work." },
      why: { he: "ма́ма — נקבה, она́.", en: "ма́ма is feminine: она́." } },
    { type: "order", answer: "Где мой телефо́н?",
      tr: { he: "איפה הטלפון שלי?", en: "Where is my phone?" } },
    { type: "order", answer: "Музе́й о́чень большо́й.",
      tr: { he: "המוזיאון גדול מאוד.", en: "The museum is very big." } },
    { type: "fix", q: "Где кни́га? — Вот он.", answer: ["Где кни́га? — Вот она́."],
      tr: { he: "איפה הספר? — הנה הוא.", en: "Where is the book? — Here it is." },
      why: { he: "кни́га היא נקבה ברוסית, לכן она́.", en: "кни́га is feminine, so use она́." } },
    { type: "fix", q: "Э́то мо́ре. Она́ тёплое.", answer: ["Э́то мо́ре. Оно́ тёплое."],
      tr: { he: "זה הים. הוא חמים.", en: "This is the sea. It is warm." },
      why: { he: "мо́ре הוא סתמי — оно́.", en: "мо́ре is neuter — оно́." } }
  ]
});

LS_DATA.grammar.push({
  id: "ru_plural", target: "ru", level: 1, order: 3,
  title: { he: "רבים", en: "Plurals", ru: "Мно́жественное число́" },
  explain: {
    he: "<p>ברבים, רוב המילים מקבלות <b>‎-ы</b> או <b>‎-и</b> (מקביל ל־ים/־ות בעברית), ומילים סתמיות מקבלות <b>‎-а/-я</b>:</p><table><tr><th>יחיד</th><th>רבים</th></tr><tr><td>стол</td><td>столы́</td></tr><tr><td>ма́ма</td><td>ма́мы</td></tr><tr><td>музе́й, неде́ля, слова́рь</td><td>музе́и, неде́ли, словари́</td></tr><tr><td>окно́</td><td>о́кна</td></tr><tr><td>мо́ре</td><td>моря́</td></tr></table><p><b>כלל כתיב חשוב:</b> אחרי г, к, х, ж, ш, ч, щ כותבים תמיד <b>и</b> ולא ы: кни́га → <b>кни́ги</b>, язы́к → <b>языки́</b>, каранда́ш → <b>карандаши́</b>.</p><p>יש מילים יוצאות דופן שצריך לזכור: друг → <b>друзья́</b>, брат → <b>бра́тья</b>, челове́к → <b>лю́ди</b>, ребёнок → <b>де́ти</b>, го́род → <b>города́</b>, дом → <b>дома́</b>.</p><p>שימו לב: לפעמים ההטעמה זזה ברבים (окно́ → о́кна).</p>",
    en: "<p>Most nouns form the plural with <b>-ы</b> or <b>-и</b>, and neuter nouns take <b>-а/-я</b>:</p><table><tr><th>Singular</th><th>Plural</th></tr><tr><td>стол</td><td>столы́</td></tr><tr><td>ма́ма</td><td>ма́мы</td></tr><tr><td>музе́й, неде́ля, слова́рь</td><td>музе́и, неде́ли, словари́</td></tr><tr><td>окно́</td><td>о́кна</td></tr><tr><td>мо́ре</td><td>моря́</td></tr></table><p><b>Important spelling rule:</b> after г, к, х, ж, ш, ч, щ always write <b>и</b>, never ы: кни́га → <b>кни́ги</b>, язы́к → <b>языки́</b>, каранда́ш → <b>карандаши́</b>.</p><p>Some common irregulars to memorize: друг → <b>друзья́</b>, брат → <b>бра́тья</b>, челове́к → <b>лю́ди</b>, ребёнок → <b>де́ти</b>, го́род → <b>города́</b>, дом → <b>дома́</b>. (English has these too: man → men, child → children.)</p><p>Note that stress can move in the plural (окно́ → о́кна).</p>"
  },
  examples: [
    { t: "Э́то мой друг. А э́то мои́ друзья́.", he: "זה החבר שלי. ואלה החברים שלי.", en: "This is my friend. And these are my friends." },
    { t: "Где кни́ги? — Вот они́.", he: "איפה הספרים? — הנה הם.", en: "Where are the books? — Here they are." },
    { t: "Там ма́льчики и де́вочки.", he: "שם יש בנים ובנות.", en: "There are boys and girls over there." },
    { t: "Де́ти игра́ют.", he: "הילדים משחקים.", en: "The children are playing." },
    { t: "Москва́ и Санкт-Петербу́рг — больши́е города́.", he: "מוסקבה וסנקט פטרבורג הן ערים גדולות.", en: "Moscow and Saint Petersburg are big cities." }
  ],
  exercises: [
    { type: "choice", q: "кни́га → ___ (plural)", options: ["кни́гы", "кни́ги", "кни́га"], answer: 1,
      tr: { he: "ספר → ספרים", en: "book → books" },
      why: { he: "אחרי г כותבים и, לא ы.", en: "After г you write и, not ы." } },
    { type: "choice", q: "окно́ → ___ (plural)", options: ["окны́", "о́кна", "окне́"], answer: 1,
      tr: { he: "חלון → חלונות", en: "window → windows" },
      why: { he: "סתמי ב־‎-о מקבל ‎-а ברבים. ההטעמה זזה.", en: "Neuter -о becomes -а; the stress moves." } },
    { type: "choice", q: "друг → ___ (plural)", options: ["дру́ги", "друзья́", "дру́гы"], answer: 1,
      tr: { he: "חבר → חברים", en: "friend → friends" },
      why: { he: "друг יוצא דופן: друзья́.", en: "друг is irregular: друзья́." } },
    { type: "fill", q: "Там ___. (студе́нт)", answer: ["студе́нты", "студенты"],
      tr: { he: "שם יש סטודנטים.", en: "There are students there." },
      why: { he: "זכר שנגמר בעיצור: מוסיפים ‎-ы.", en: "Masculine ending in a consonant: add -ы." } },
    { type: "fill", q: "Э́то ___. (маши́на)", answer: ["маши́ны", "машины"],
      tr: { he: "אלה מכוניות.", en: "These are cars." },
      why: { he: "נקבה ‎-а → ‎-ы.", en: "Feminine -а → -ы." } },
    { type: "fill", q: "Где ___? (ребёнок)", answer: ["де́ти", "дети"],
      tr: { he: "איפה הילדים?", en: "Where are the children?" },
      why: { he: "ребёнок → де́ти, צורה יוצאת דופן.", en: "ребёнок → де́ти is irregular." } },
    { type: "order", answer: "Там ма́льчики и де́вочки.",
      tr: { he: "שם יש בנים ובנות.", en: "There are boys and girls over there." } },
    { type: "order", answer: "Где мои́ ключи́?",
      tr: { he: "איפה המפתחות שלי?", en: "Where are my keys?" } },
    { type: "fix", q: "Э́то мои́ кни́гы.", answer: ["Э́то мои́ кни́ги."],
      tr: { he: "אלה הספרים שלי.", en: "These are my books." },
      why: { he: "אחרי г תמיד и: кни́ги.", en: "After г always и: кни́ги." } },
    { type: "fix", q: "Там челове́ки.", answer: ["Там лю́ди."],
      tr: { he: "שם יש אנשים.", en: "There are people there." },
      why: { he: "הרבים של челове́к הוא лю́ди.", en: "The plural of челове́к is лю́ди." } }
  ]
});

LS_DATA.grammar.push({
  id: "ru_pronouns_possessives", target: "ru", level: 1, order: 4,
  title: { he: "כינויי גוף וכינויי שייכות", en: "Pronouns & possessives", ru: "Местоиме́ния: я, ты, мой, твой" },
  explain: {
    he: "<p>כינויי הגוף: <b>я</b> (אני), <b>ты</b> (אתה/את), <b>он</b> (הוא), <b>она́</b> (היא), <b>оно́</b> (זה, סתמי), <b>мы</b> (אנחנו), <b>вы</b> (אתם/אתן, וגם פנייה מנומסת לאדם אחד), <b>они́</b> (הם/הן).</p><p>בעברית 'שלי' לא משתנה, אבל ברוסית 'שלי' מתאים למין ולמספר של <b>החפץ</b> (לא של הבעלים!):</p><table><tr><th></th><th>זכר</th><th>נקבה</th><th>סתמי</th><th>רבים</th></tr><tr><td>שלי</td><td>мой</td><td>моя́</td><td>моё</td><td>мои́</td></tr><tr><td>שלך</td><td>твой</td><td>твоя́</td><td>твоё</td><td>твои́</td></tr><tr><td>שלנו</td><td>наш</td><td>на́ша</td><td>на́ше</td><td>на́ши</td></tr><tr><td>שלכם</td><td>ваш</td><td>ва́ша</td><td>ва́ше</td><td>ва́ши</td></tr></table><p><b>его́</b> (שלו), <b>её</b> (שלה), <b>их</b> (שלהם) — <b>אף פעם לא משתנים</b>: его́ дом, его́ ма́ма, его́ кни́ги.</p><p>הכינוי בא <b>לפני</b> שם העצם: мой брат = 'אח שלי'.</p>",
    en: "<p>Personal pronouns: <b>я</b> (I), <b>ты</b> (you, one friend), <b>он</b> (he), <b>она́</b> (she), <b>оно́</b> (it, neuter), <b>мы</b> (we), <b>вы</b> (you plural, and polite 'you' to one person), <b>они́</b> (they).</p><p>In English 'my' never changes, but in Russian it agrees with the gender and number of the <b>thing owned</b> (not the owner!):</p><table><tr><th></th><th>masc.</th><th>fem.</th><th>neut.</th><th>plural</th></tr><tr><td>my</td><td>мой</td><td>моя́</td><td>моё</td><td>мои́</td></tr><tr><td>your</td><td>твой</td><td>твоя́</td><td>твоё</td><td>твои́</td></tr><tr><td>our</td><td>наш</td><td>на́ша</td><td>на́ше</td><td>на́ши</td></tr><tr><td>your (pl.)</td><td>ваш</td><td>ва́ша</td><td>ва́ше</td><td>ва́ши</td></tr></table><p><b>его́</b> (his), <b>её</b> (her), <b>их</b> (their) <b>never change</b>: его́ дом, его́ ма́ма, его́ кни́ги.</p><p>Like in English, the possessive goes <b>before</b> the noun: мой брат = my brother.</p>"
  },
  examples: [
    { t: "Э́то мой брат и моя́ сестра́.", he: "זה אח שלי ואחותי.", en: "This is my brother and my sister." },
    { t: "Где твоё письмо́?", he: "איפה המכתב שלך?", en: "Where is your letter?" },
    { t: "Э́то на́ши друзья́.", he: "אלה החברים שלנו.", en: "These are our friends." },
    { t: "Его́ ма́ма — врач.", he: "אמא שלו רופאה.", en: "His mom is a doctor." },
    { t: "Вы мой но́вый учи́тель?", he: "אתה המורה החדש שלי?", en: "Are you my new teacher?" }
  ],
  exercises: [
    { type: "choice", q: "Э́то ___ дом.", options: ["мой", "моя́", "моё"], answer: 0,
      tr: { he: "זה הבית שלי.", en: "This is my house." },
      why: { he: "дом — זכר, לכן мой.", en: "дом is masculine, so мой." } },
    { type: "choice", q: "Где ___ ма́ма?", options: ["твой", "твоя́", "твоё"], answer: 1,
      tr: { he: "איפה אמא שלך?", en: "Where is your mom?" },
      why: { he: "ма́ма — נקבה, לכן твоя́.", en: "ма́ма is feminine, so твоя́." } },
    { type: "choice", q: "Э́то ___ окно́.", options: ["наш", "на́ша", "на́ше"], answer: 2,
      tr: { he: "זה החלון שלנו.", en: "This is our window." },
      why: { he: "окно́ — סתמי, לכן на́ше.", en: "окно́ is neuter, so на́ше." } },
    { type: "choice", q: "Где ___ кни́ги?", options: ["мой", "моя́", "мои́"], answer: 2,
      tr: { he: "איפה הספרים שלי?", en: "Where are my books?" },
      why: { he: "кни́ги — רבים, לכן мои́.", en: "кни́ги is plural, so мои́." } },
    { type: "fill", q: "Э́то ___ сестра́. (мой)", answer: ["моя́", "моя"],
      tr: { he: "זו אחותי.", en: "This is my sister." },
      why: { he: "сестра́ — נקבה: моя́.", en: "сестра́ is feminine: моя́." } },
    { type: "fill", q: "Где ___ письмо́? (ваш)", answer: ["ва́ше", "ваше"],
      tr: { he: "איפה המכתב שלכם?", en: "Where is your letter?" },
      why: { he: "письмо́ — סתמי: ва́ше.", en: "письмо́ is neuter: ва́ше." } },
    { type: "fill", q: "Э́то Ма́ша и ___ брат. (her)", answer: ["её"],
      tr: { he: "זאת מאשה ואח שלה.", en: "This is Masha and her brother." },
      why: { he: "'שלה' = её, והוא לא משתנה.", en: "'Her' = её, and it never changes." } },
    { type: "order", answer: "Где твой телефо́н?",
      tr: { he: "איפה הטלפון שלך?", en: "Where is your phone?" } },
    { type: "order", answer: "Э́то его́ ко́мната.",
      tr: { he: "זה החדר שלו.", en: "This is his room." } },
    { type: "fix", q: "Э́то моя́ письмо́.", answer: ["Э́то моё письмо́."],
      tr: { he: "זה המכתב שלי.", en: "This is my letter." },
      why: { he: "письмо́ סתמי (נגמר ב־‎-о), לכן моё.", en: "письмо́ is neuter (ends in -о), so моё." } }
  ]
});

LS_DATA.grammar.push({
  id: "ru_adjectives", target: "ru", level: 1, order: 5,
  title: { he: "התאמת שמות תואר", en: "Adjective agreement", ru: "Прилага́тельные" },
  explain: {
    he: "<p>כמו בעברית ('בית גדול', 'עיר גדולה'), שם התואר ברוסית מתאים למין ולמספר של שם העצם. ההבדל: ברוסית שם התואר בא <b>לפני</b> שם העצם — <b>большо́й дом</b>.</p><table><tr><th>זכר</th><th>נקבה</th><th>סתמי</th><th>רבים</th></tr><tr><td>но́вый</td><td>но́вая</td><td>но́вое</td><td>но́вые</td></tr><tr><td>большо́й</td><td>больша́я</td><td>большо́е</td><td>больши́е</td></tr><tr><td>си́ний</td><td>си́няя</td><td>си́нее</td><td>си́ние</td></tr></table><p>בזכר יש שלוש אפשרויות: <b>‎-ый</b> (רגיל), <b>‎-о́й</b> (כשההטעמה על הסוף), <b>‎-ий</b> (אחרי г, к, х, ж, ш, ч, щ או בשמות תואר 'רכים').</p><p>אותו כלל כתיב מהרבים: אחרי г, к, х, ж, ш, ч, щ כותבים <b>и</b> ולא ы: ру́сский → ру́сские, хоро́ший → хоро́шие.</p><p>טיפ: הסוף של שם התואר לרוב 'מתחרז' עם השאלה: како́й? кака́я? како́е? каки́е?</p>",
    en: "<p>Like in Hebrew ('בית גדול', 'עיר גדולה'), a Russian adjective agrees with its noun in gender and number. Unlike Hebrew, it comes <b>before</b> the noun, as in English: <b>большо́й дом</b> (a big house).</p><table><tr><th>masc.</th><th>fem.</th><th>neut.</th><th>plural</th></tr><tr><td>но́вый</td><td>но́вая</td><td>но́вое</td><td>но́вые</td></tr><tr><td>большо́й</td><td>больша́я</td><td>большо́е</td><td>больши́е</td></tr><tr><td>си́ний</td><td>си́няя</td><td>си́нее</td><td>си́ние</td></tr></table><p>Masculine has three possible endings: <b>-ый</b> (normal), <b>-о́й</b> (when the ending is stressed), <b>-ий</b> (after г, к, х, ж, ш, ч, щ, or in 'soft' adjectives).</p><p>The same spelling rule as in plurals: after г, к, х, ж, ш, ч, щ write <b>и</b>, not ы: ру́сский → ру́сские, хоро́ший → хоро́шие.</p><p>Tip: the ending usually 'rhymes' with the question word: како́й? кака́я? како́е? каки́е? (which/what kind?)</p>"
  },
  examples: [
    { t: "Э́то но́вый телефо́н.", he: "זה טלפון חדש.", en: "This is a new phone." },
    { t: "Москва́ — о́чень краси́вый го́род.", he: "מוסקבה היא עיר יפה מאוד.", en: "Moscow is a very beautiful city." },
    { t: "Моя́ сестра́ — у́мная де́вочка.", he: "אחותי ילדה חכמה.", en: "My sister is a smart girl." },
    { t: "Како́е большо́е окно́!", he: "איזה חלון גדול!", en: "What a big window!" },
    { t: "Э́то ру́сские пе́сни.", he: "אלה שירים רוסיים.", en: "These are Russian songs." },
    { t: "Си́нее мо́ре и бе́лый песо́к.", he: "ים כחול וחול לבן.", en: "A blue sea and white sand." }
  ],
  exercises: [
    { type: "choice", q: "Э́то ___ кни́га.", options: ["интере́сный", "интере́сная", "интере́сное"], answer: 1,
      tr: { he: "זה ספר מעניין.", en: "This is an interesting book." },
      why: { he: "кни́га — נקבה: ‎-ая.", en: "кни́га is feminine: -ая." } },
    { type: "choice", q: "Како́е ___ мо́ре!", options: ["краси́вый", "краси́вая", "краси́вое"], answer: 2,
      tr: { he: "איזה ים יפה!", en: "What a beautiful sea!" },
      why: { he: "мо́ре — סתמי: ‎-ое.", en: "мо́ре is neuter: -ое." } },
    { type: "choice", q: "Э́то ___ дом.", options: ["большо́й", "больша́я", "больши́е"], answer: 0,
      tr: { he: "זה בית גדול.", en: "This is a big house." },
      why: { he: "дом — זכר. ההטעמה על הסוף, לכן ‎-о́й.", en: "дом is masculine; the ending is stressed, so -о́й." } },
    { type: "choice", q: "Э́то ___ студе́нты.", options: ["ру́сские", "ру́сскые", "ру́сская"], answer: 0,
      tr: { he: "אלה סטודנטים רוסים.", en: "These are Russian students." },
      why: { he: "רבים, ואחרי к כותבים и: ру́сские.", en: "Plural, and after к write и: ру́сские." } },
    { type: "fill", q: "Э́то ___ маши́на. (но́вый)", answer: ["но́вая", "новая"],
      tr: { he: "זו מכונית חדשה.", en: "This is a new car." },
      why: { he: "маши́на — נקבה: но́вая.", en: "маши́на is feminine: но́вая." } },
    { type: "fill", q: "Э́то ___ окно́. (большо́й)", answer: ["большо́е", "большое"],
      tr: { he: "זה חלון גדול.", en: "This is a big window." },
      why: { he: "окно́ — סתמי: большо́е.", en: "окно́ is neuter: большо́е." } },
    { type: "fill", q: "Там ___ де́ти. (ма́ленький)", answer: ["ма́ленькие", "маленькие"],
      tr: { he: "שם יש ילדים קטנים.", en: "There are little children there." },
      why: { he: "רבים, ואחרי к — ‎-ие.", en: "Plural, and after к — -ие." } },
    { type: "order", answer: "Э́то о́чень интере́сная кни́га.",
      tr: { he: "זה ספר מעניין מאוד.", en: "This is a very interesting book." } },
    { type: "fix", q: "Э́то краси́вый ла́мпа.", answer: ["Э́то краси́вая ла́мпа."],
      tr: { he: "זו מנורה יפה.", en: "This is a beautiful lamp." },
      why: { he: "ла́мпа — נקבה, לכן краси́вая.", en: "ла́мпа is feminine, so краси́вая." } },
    { type: "fix", q: "Мой брат — хоро́шый челове́к.", answer: ["Мой брат — хоро́ший челове́к."],
      tr: { he: "אחי בן אדם טוב.", en: "My brother is a good person." },
      why: { he: "אחרי ш כותבים и, לא ы: хоро́ший.", en: "After ш write и, not ы: хоро́ший." } }
  ]
});

LS_DATA.grammar.push({
  id: "ru_conj1", target: "ru", level: 2, order: 6,
  title: { he: "נטיית פעלים 1 (‎-ешь)", en: "Verb conjugation 1 (-ешь)", ru: "Пе́рвое спряже́ние" },
  explain: {
    he: "<p>בעברית הפועל בהווה משתנה לפי מין ומספר (יודע, יודעת, יודעים). ברוסית הוא משתנה לפי <b>גוף</b> — אבל <b>לא לפי מין</b>: 'он зна́ет' ו־'она́ зна́ет' זהים.</p><p>בקבוצה הראשונה מורידים ‎-ть מהמקור (знать → зна-) ומוסיפים:</p><table><tr><th>גוף</th><th>סיומת</th><th>знать (לדעת)</th><th>рабо́тать (לעבוד)</th></tr><tr><td>я</td><td>‎-ю</td><td>зна́ю</td><td>рабо́таю</td></tr><tr><td>ты</td><td>‎-ешь</td><td>зна́ешь</td><td>рабо́таешь</td></tr><tr><td>он / она́</td><td>‎-ет</td><td>зна́ет</td><td>рабо́тает</td></tr><tr><td>мы</td><td>‎-ем</td><td>зна́ем</td><td>рабо́таем</td></tr><tr><td>вы</td><td>‎-ете</td><td>зна́ете</td><td>рабо́таете</td></tr><tr><td>они́</td><td>‎-ют</td><td>зна́ют</td><td>рабо́тают</td></tr></table><p>כך גם: <b>де́лать</b> (לעשות), <b>чита́ть</b> (לקרוא), <b>понима́ть</b> (להבין), <b>слу́шать</b> (להקשיב), <b>игра́ть</b> (לשחק).</p><p>הסימן של הקבוצה: <b>е</b> בסיומות (‎-ешь, ‎-ет...).</p>",
    en: "<p>In Hebrew the present tense changes by gender and number (יודע, יודעת, יודעים). In Russian it changes by <b>person</b> — but <b>not by gender</b>: 'он зна́ет' and 'она́ зна́ет' are the same.</p><p>For the first group, drop -ть from the infinitive (знать → зна-) and add:</p><table><tr><th>Person</th><th>Ending</th><th>знать (to know)</th><th>рабо́тать (to work)</th></tr><tr><td>я</td><td>-ю</td><td>зна́ю</td><td>рабо́таю</td></tr><tr><td>ты</td><td>-ешь</td><td>зна́ешь</td><td>рабо́таешь</td></tr><tr><td>он / она́</td><td>-ет</td><td>зна́ет</td><td>рабо́тает</td></tr><tr><td>мы</td><td>-ем</td><td>зна́ем</td><td>рабо́таем</td></tr><tr><td>вы</td><td>-ете</td><td>зна́ете</td><td>рабо́таете</td></tr><tr><td>они́</td><td>-ют</td><td>зна́ют</td><td>рабо́тают</td></tr></table><p>Same pattern: <b>де́лать</b> (to do), <b>чита́ть</b> (to read), <b>понима́ть</b> (to understand), <b>слу́шать</b> (to listen), <b>игра́ть</b> (to play).</p><p>The sign of this group: the letter <b>е</b> in the endings (-ешь, -ет...). Russian present also covers English 'I read' and 'I am reading'.</p>"
  },
  examples: [
    { t: "Я зна́ю э́то сло́во.", he: "אני מכיר את המילה הזאת.", en: "I know this word." },
    { t: "Что ты де́лаешь? — Я чита́ю.", he: "מה אתה עושה? — אני קורא.", en: "What are you doing? — I'm reading." },
    { t: "Мой па́па рабо́тает в ба́нке.", he: "אבא שלי עובד בבנק.", en: "My dad works at a bank." },
    { t: "Мы понима́ем по-ру́сски.", he: "אנחנו מבינים רוסית.", en: "We understand Russian." },
    { t: "Вы слу́шаете му́зыку?", he: "אתם מקשיבים למוזיקה?", en: "Are you listening to music?" },
    { t: "Они́ мно́го рабо́тают.", he: "הם עובדים הרבה.", en: "They work a lot." }
  ],
  exercises: [
    { type: "choice", q: "Что ты ___?", options: ["де́лаю", "де́лаешь", "де́лает"], answer: 1,
      tr: { he: "מה אתה עושה?", en: "What are you doing?" },
      why: { he: "ты → ‎-ешь.", en: "ты → -ешь." } },
    { type: "choice", q: "Мы ___ по-ру́сски.", options: ["понима́ем", "понима́ете", "понима́ют"], answer: 0,
      tr: { he: "אנחנו מבינים רוסית.", en: "We understand Russian." },
      why: { he: "мы → ‎-ем.", en: "мы → -ем." } },
    { type: "choice", q: "Они́ ___ до́ма.", options: ["рабо́тает", "рабо́таем", "рабо́тают"], answer: 2,
      tr: { he: "הם עובדים מהבית.", en: "They work from home." },
      why: { he: "они́ → ‎-ют.", en: "они́ → -ют." } },
    { type: "fill", q: "Я ___ кни́гу. (чита́ть)", answer: ["чита́ю", "читаю"],
      tr: { he: "אני קורא ספר.", en: "I am reading a book." },
      why: { he: "я → ‎-ю.", en: "я → -ю." } },
    { type: "fill", q: "Вы ___ ру́сский язы́к? (знать)", answer: ["зна́ете", "знаете"],
      tr: { he: "אתם יודעים רוסית?", en: "Do you know Russian?" },
      why: { he: "вы → ‎-ете.", en: "вы → -ете." } },
    { type: "fill", q: "Она́ ___ му́зыку. (слу́шать)", answer: ["слу́шает", "слушает"],
      tr: { he: "היא מקשיבה למוזיקה.", en: "She is listening to music." },
      why: { he: "она́ → ‎-ет. אותה צורה כמו он.", en: "она́ → -ет, the same form as for он." } },
    { type: "fill", q: "Ты ___ сего́дня? (рабо́тать)", answer: ["рабо́таешь", "работаешь"],
      tr: { he: "אתה עובד היום?", en: "Are you working today?" },
      why: { he: "ты → ‎-ешь.", en: "ты → -ешь." } },
    { type: "order", answer: "Что вы де́лаете сего́дня?",
      tr: { he: "מה אתם עושים היום?", en: "What are you doing today?" } },
    { type: "fix", q: "Он зна́ешь э́то сло́во.", answer: ["Он зна́ет э́то сло́во."],
      tr: { he: "הוא מכיר את המילה הזאת.", en: "He knows this word." },
      why: { he: "он → ‎-ет, לא ‎-ешь (‎-ешь זה ל־ты).", en: "он takes -ет; -ешь is for ты." } },
    { type: "fix", q: "Мы чита́ют кни́гу.", answer: ["Мы чита́ем кни́гу."],
      tr: { he: "אנחנו קוראים ספר.", en: "We are reading a book." },
      why: { he: "мы → ‎-ем.", en: "мы → -ем." } }
  ]
});

LS_DATA.grammar.push({
  id: "ru_conj2", target: "ru", level: 2, order: 7,
  title: { he: "נטיית פעלים 2 (‎-ишь)", en: "Verb conjugation 2 (-ишь)", ru: "Второ́е спряже́ние" },
  explain: {
    he: "<p>הקבוצה השנייה — רוב הפעלים שנגמרים ב־<b>‎-ить</b> (וגם כמה ב־‎-еть). מורידים את ‎-ить/-еть ומוסיפים סיומות עם <b>и</b>:</p><table><tr><th>גוף</th><th>סיומת</th><th>говори́ть (לדבר)</th><th>смотре́ть (לצפות)</th></tr><tr><td>я</td><td>‎-ю/-у</td><td>говорю́</td><td>смотрю́</td></tr><tr><td>ты</td><td>‎-ишь</td><td>говори́шь</td><td>смо́тришь</td></tr><tr><td>он / она́</td><td>‎-ит</td><td>говори́т</td><td>смо́трит</td></tr><tr><td>мы</td><td>‎-им</td><td>говори́м</td><td>смо́трим</td></tr><tr><td>вы</td><td>‎-ите</td><td>говори́те</td><td>смо́трите</td></tr><tr><td>они́</td><td>‎-ят/-ат</td><td>говоря́т</td><td>смо́трят</td></tr></table><p><b>שימו לב ל־люби́ть</b> (לאהוב): ב־я מופיעה <b>л</b> נוספת: я <b>люблю́</b>, אבל ты лю́бишь, он лю́бит, они́ лю́бят. כך גם <b>ви́деть</b> → я <b>ви́жу</b>, ты ви́дишь.</p><p>ההטעמה יכולה לזוז: смотрю́, אבל смо́тришь. כדאי ללמוד את צורות я ו־ты בעל פה.</p>",
    en: "<p>The second group — most verbs ending in <b>-ить</b> (and some in -еть). Drop -ить/-еть and add endings with <b>и</b>:</p><table><tr><th>Person</th><th>Ending</th><th>говори́ть (to speak)</th><th>смотре́ть (to watch)</th></tr><tr><td>я</td><td>-ю/-у</td><td>говорю́</td><td>смотрю́</td></tr><tr><td>ты</td><td>-ишь</td><td>говори́шь</td><td>смо́тришь</td></tr><tr><td>он / она́</td><td>-ит</td><td>говори́т</td><td>смо́трит</td></tr><tr><td>мы</td><td>-им</td><td>говори́м</td><td>смо́трим</td></tr><tr><td>вы</td><td>-ите</td><td>говори́те</td><td>смо́трите</td></tr><tr><td>они́</td><td>-ят/-ат</td><td>говоря́т</td><td>смо́трят</td></tr></table><p><b>Watch out for люби́ть</b> (to love/like): the я form gets an extra <b>л</b>: я <b>люблю́</b>, but ты лю́бишь, он лю́бит, они́ лю́бят. Similarly <b>ви́деть</b> → я <b>ви́жу</b>, ты ви́дишь.</p><p>Stress can move: смотрю́, but смо́тришь. Learn the я and ты forms by heart; the rest follow the ты form.</p>"
  },
  examples: [
    { t: "Я говорю́ по-ру́сски и на иври́те.", he: "אני מדבר רוסית ועברית.", en: "I speak Russian and Hebrew." },
    { t: "Ты лю́бишь шокола́д?", he: "אתה אוהב שוקולד?", en: "Do you like chocolate?" },
    { t: "Мы смо́трим фильм.", he: "אנחנו צופים בסרט.", en: "We are watching a movie." },
    { t: "Они́ говоря́т о́чень бы́стро.", he: "הם מדברים מהר מאוד.", en: "They speak very fast." },
    { t: "Я люблю́ футбо́л.", he: "אני אוהב כדורגל.", en: "I love soccer." }
  ],
  exercises: [
    { type: "choice", q: "Я ___ по-англи́йски.", options: ["говорю́", "говори́шь", "говоря́т"], answer: 0,
      tr: { he: "אני מדבר אנגלית.", en: "I speak English." },
      why: { he: "я → ‎-ю.", en: "я → -ю." } },
    { type: "choice", q: "Ты ___ футбо́л?", options: ["люблю́", "лю́бишь", "лю́бит"], answer: 1,
      tr: { he: "אתה אוהב כדורגל?", en: "Do you like soccer?" },
      why: { he: "ты → ‎-ишь. ה־л הנוספת רק ב־я.", en: "ты → -ишь. The extra л is only in the я form." } },
    { type: "choice", q: "Они́ ___ телеви́зор.", options: ["смо́трит", "смо́трим", "смо́трят"], answer: 2,
      tr: { he: "הם צופים בטלוויזיה.", en: "They are watching TV." },
      why: { he: "они́ → ‎-ят.", en: "они́ → -ят." } },
    { type: "fill", q: "Я ___ мо́ре. (люби́ть)", answer: ["люблю́", "люблю"],
      tr: { he: "אני אוהב את הים.", en: "I love the sea." },
      why: { he: "ב־я יש л נוספת: люблю́.", en: "The я form adds л: люблю́." } },
    { type: "fill", q: "Что вы ___? (смотре́ть)", answer: ["смо́трите", "смотрите"],
      tr: { he: "במה אתם צופים?", en: "What are you watching?" },
      why: { he: "вы → ‎-ите.", en: "вы → -ите." } },
    { type: "fill", q: "Ма́ма ___ по телефо́ну. (говори́ть)", answer: ["говори́т", "говорит"],
      tr: { he: "אמא מדברת בטלפון.", en: "Mom is talking on the phone." },
      why: { he: "она́ → ‎-ит.", en: "она́ → -ит." } },
    { type: "fill", q: "Мы ___ фильм. (смотре́ть)", answer: ["смо́трим", "смотрим"],
      tr: { he: "אנחנו צופים בסרט.", en: "We are watching a movie." },
      why: { he: "мы → ‎-им.", en: "мы → -им." } },
    { type: "order", answer: "Я о́чень люблю́ шокола́д.",
      tr: { he: "אני מאוד אוהב שוקולד.", en: "I really love chocolate." } },
    { type: "fix", q: "Я любю́ пи́ццу.", answer: ["Я люблю́ пи́ццу."],
      tr: { he: "אני אוהב פיצה.", en: "I love pizza." },
      why: { he: "צריך л נוספת: люблю́.", en: "You need the extra л: люблю́." } },
    { type: "fix", q: "Они́ говоря́ют по-ру́сски.", answer: ["Они́ говоря́т по-ру́сски."],
      tr: { he: "הם מדברים רוסית.", en: "They speak Russian." },
      why: { he: "בקבוצה 2 они́ → ‎-ят, לא ‎-ют.", en: "In group 2, они́ takes -ят, not -ют." } }
  ]
});
