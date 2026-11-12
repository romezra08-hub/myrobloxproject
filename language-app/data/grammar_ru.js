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
