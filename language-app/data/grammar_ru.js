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

LS_DATA.grammar.push({
  id: "ru_past", target: "ru", level: 2, order: 8,
  title: { he: "זמן עבר", en: "Past tense", ru: "Проше́дшее вре́мя" },
  explain: {
    he: "<p>זמן עבר ברוסית קל מאוד! מורידים ‎-ть מהמקור ומוסיפים סיומת לפי <b>מין ומספר</b> — בדיוק כמו בעברית (הוא כתב / היא כתבה / הם כתבו):</p><table><tr><th></th><th>סיומת</th><th>чита́ть</th></tr><tr><td>זכר (он, я-בן, ты-בן)</td><td>‎-л</td><td>чита́л</td></tr><tr><td>נקבה (она́, я-בת, ты-בת)</td><td>‎-ла</td><td>чита́ла</td></tr><tr><td>סתמי (оно́)</td><td>‎-ло</td><td>чита́ло</td></tr><tr><td>רבים (мы, вы, они́)</td><td>‎-ли</td><td>чита́ли</td></tr></table><p>אין שינוי לפי גוף: я чита́л, ты чита́л, он чита́л. רק המין קובע. בן אומר <b>я чита́л</b>, בת אומרת <b>я чита́ла</b>.</p><p><b>вы</b> תמיד ‎-ли, גם בפנייה מנומסת לאדם אחד.</p><p>'היה' = <b>был, была́, бы́ло, бы́ли</b>. ככה אומרים 'הייתי בבית': Я был до́ма. משפטים כמו 'היה קר' משתמשים בסתמי: <b>Бы́ло хо́лодно.</b></p><p>יוצא דופן נפוץ: идти́ → <b>шёл, шла, шли</b>.</p>",
    en: "<p>The Russian past tense is easy! Drop -ть from the infinitive and add an ending for <b>gender and number</b> — just like Hebrew (הוא כתב / היא כתבה / הם כתבו):</p><table><tr><th></th><th>Ending</th><th>чита́ть</th></tr><tr><td>masc. (он, я/ты as a boy)</td><td>-л</td><td>чита́л</td></tr><tr><td>fem. (она́, я/ты as a girl)</td><td>-ла</td><td>чита́ла</td></tr><tr><td>neuter (оно́)</td><td>-ло</td><td>чита́ло</td></tr><tr><td>plural (мы, вы, они́)</td><td>-ли</td><td>чита́ли</td></tr></table><p>There is no change by person: я чита́л, ты чита́л, он чита́л. Only gender matters. A boy says <b>я чита́л</b>, a girl says <b>я чита́ла</b>.</p><p><b>вы</b> is always -ли, even when politely addressing one person.</p><p>'Was/were' = <b>был, была́, бы́ло, бы́ли</b>: Я был до́ма (I was at home). Sentences like 'it was cold' use the neuter: <b>Бы́ло хо́лодно.</b></p><p>A common irregular: идти́ → <b>шёл, шла, шли</b>.</p>"
  },
  examples: [
    { t: "Вчера́ я чита́л кни́гу.", he: "אתמול קראתי ספר. (בן מדבר)", en: "Yesterday I read a book. (a boy speaking)" },
    { t: "Вчера́ я чита́ла кни́гу.", he: "אתמול קראתי ספר. (בת מדברת)", en: "Yesterday I read a book. (a girl speaking)" },
    { t: "Ма́ма рабо́тала весь день.", he: "אמא עבדה כל היום.", en: "Mom worked all day." },
    { t: "Мы смотре́ли фильм.", he: "צפינו בסרט.", en: "We watched a movie." },
    { t: "Где ты был?", he: "איפה היית?", en: "Where were you?" },
    { t: "Э́то бы́ло интере́сно.", he: "זה היה מעניין.", en: "It was interesting." }
  ],
  exercises: [
    { type: "choice", q: "Вчера́ А́нна ___ письмо́.", options: ["писа́л", "писа́ла", "писа́ли"], answer: 1,
      tr: { he: "אתמול אנה כתבה מכתב.", en: "Yesterday Anna wrote a letter." },
      why: { he: "А́нна — נקבה: ‎-ла.", en: "А́нна is feminine: -ла." } },
    { type: "choice", q: "Мы ___ до́ма.", options: ["был", "была́", "бы́ли"], answer: 2,
      tr: { he: "היינו בבית.", en: "We were at home." },
      why: { he: "мы — רבים: бы́ли.", en: "мы is plural: бы́ли." } },
    { type: "choice", q: "Па́па ___ телеви́зор.", options: ["смотре́л", "смотре́ла", "смотре́ли"], answer: 0,
      tr: { he: "אבא צפה בטלוויזיה.", en: "Dad watched TV." },
      why: { he: "па́па — זכר: ‎-л.", en: "па́па is masculine: -л." } },
    { type: "fill", q: "Ты ___ э́тот фильм? (смотре́ть)", answer: ["смотре́л", "смотре́ла", "смотрел", "смотрела"],
      tr: { he: "ראית את הסרט הזה?", en: "Did you watch this movie?" },
      why: { he: "ל־ты: ‎-л לבן, ‎-ла לבת.", en: "For ты: -л for a boy, -ла for a girl." } },
    { type: "fill", q: "Она́ ___ по-ру́сски. (говори́ть)", answer: ["говори́ла", "говорила"],
      tr: { he: "היא דיברה רוסית.", en: "She spoke Russian." },
      why: { he: "она́ → ‎-ла.", en: "она́ → -ла." } },
    { type: "fill", q: "Де́ти ___ в па́рке. (игра́ть)", answer: ["игра́ли", "играли"],
      tr: { he: "הילדים שיחקו בפארק.", en: "The children played in the park." },
      why: { he: "де́ти — רבים: ‎-ли.", en: "де́ти is plural: -ли." } },
    { type: "fill", q: "Вчера́ ___ хо́лодно. (быть)", answer: ["бы́ло", "было"],
      tr: { he: "אתמול היה קר.", en: "It was cold yesterday." },
      why: { he: "במשפט בלי נושא ('היה קר') משתמשים בסתמי: бы́ло.", en: "With no subject ('it was cold'), use the neuter: бы́ло." } },
    { type: "order", answer: "Где ты был вчера́?",
      tr: { he: "איפה היית אתמול?", en: "Where were you yesterday?" } },
    { type: "fix", q: "Она́ чита́л кни́гу.", answer: ["Она́ чита́ла кни́гу."],
      tr: { he: "היא קראה ספר.", en: "She read a book." },
      why: { he: "она́ — נקבה, צריך ‎-ла.", en: "она́ is feminine and needs -ла." } },
    { type: "fix", q: "Они́ рабо́тал вчера́.", answer: ["Они́ рабо́тали вчера́."],
      tr: { he: "הם עבדו אתמול.", en: "They worked yesterday." },
      why: { he: "они́ — רבים, צריך ‎-ли.", en: "они́ is plural and needs -ли." } }
  ]
});

LS_DATA.grammar.push({
  id: "ru_questions_negation", target: "ru", level: 2, order: 9,
  title: { he: "שאלות ושלילה", en: "Questions & negation", ru: "Вопро́сы и отрица́ние" },
  explain: {
    he: "<p><b>שאלות כן/לא</b> — בדיוק כמו בעברית: לא משנים את סדר המילים, רק מרימים את הטון: Ты студе́нт. → Ты студе́нт? (אין do/does כמו באנגלית.)</p><p><b>מילות שאלה:</b></p><ul><li><b>кто?</b> מי? · <b>что?</b> מה?</li><li><b>где?</b> איפה? · <b>куда́?</b> לאן?</li><li><b>когда́?</b> מתי? · <b>почему́?</b> למה?</li><li><b>как?</b> איך? · <b>ско́лько?</b> כמה? · <b>како́й?</b> איזה?</li></ul><p><b>שלילה:</b> שמים <b>не</b> לפני המילה ששוללים, בדרך כלל לפני הפועל: Я <b>не</b> зна́ю. (אני לא יודע.)</p><p><b>нет</b> = 'לא' כתשובה: Ты голо́дный? — <b>Нет</b>, я не голо́дный.</p><p><b>שלילה כפולה</b> היא נכונה ברוסית (כמו בעברית: 'אני לא יודע כלום'): Я <b>ничего́ не</b> зна́ю. <b>Никто́ не</b> зна́ет. Я <b>никогда́ не</b> был там.</p>",
    en: "<p><b>Yes/no questions</b> work like Hebrew: keep the same word order and just raise your voice: Ты студе́нт. → Ты студе́нт? (No 'do/does' like in English.)</p><p><b>Question words:</b></p><ul><li><b>кто?</b> who? · <b>что?</b> what?</li><li><b>где?</b> where? · <b>куда́?</b> where to?</li><li><b>когда́?</b> when? · <b>почему́?</b> why?</li><li><b>как?</b> how? · <b>ско́лько?</b> how many/much? · <b>како́й?</b> which / what kind?</li></ul><p><b>Negation:</b> put <b>не</b> right before the word you negate, usually the verb: Я <b>не</b> зна́ю. (I don't know.)</p><p><b>нет</b> = 'no' as an answer: Ты голо́дный? — <b>Нет</b>, я не голо́дный. (Are you hungry? — No, I'm not hungry.)</p><p><b>Double negatives</b> are correct in Russian (like Hebrew 'אני לא יודע כלום'): Я <b>ничего́ не</b> зна́ю (I don't know anything). <b>Никто́ не</b> зна́ет (Nobody knows). Я <b>никогда́ не</b> был там (I've never been there).</p>"
  },
  examples: [
    { t: "Ты студе́нт? — Нет, я не студе́нт.", he: "אתה סטודנט? — לא, אני לא סטודנט.", en: "Are you a student? — No, I'm not a student." },
    { t: "Где ты живёшь?", he: "איפה אתה גר?", en: "Where do you live?" },
    { t: "Почему́ ты не спишь?", he: "למה אתה לא ישן?", en: "Why aren't you sleeping?" },
    { t: "Как тебя́ зову́т?", he: "איך קוראים לך?", en: "What's your name?" },
    { t: "Я ничего́ не понима́ю.", he: "אני לא מבין כלום.", en: "I don't understand anything." },
    { t: "Когда́ ты рабо́таешь?", he: "מתי אתה עובד?", en: "When do you work?" }
  ],
  exercises: [
    { type: "choice", q: "___ ты живёшь? — В Ха́йфе.", options: ["Где", "Кто", "Когда́"], answer: 0,
      tr: { he: "איפה אתה גר? — בחיפה.", en: "Where do you live? — In Haifa." },
      why: { he: "שואלים על מקום: где?", en: "Asking about a place: где?" } },
    { type: "choice", q: "___ э́то? — Э́то мой брат.", options: ["Что", "Кто", "Как"], answer: 1,
      tr: { he: "מי זה? — זה אח שלי.", en: "Who is this? — This is my brother." },
      why: { he: "על אדם שואלים кто.", en: "For a person, ask кто." } },
    { type: "choice", q: "___ э́то? — Э́то стол.", options: ["Что", "Кто", "Где"], answer: 0,
      tr: { he: "מה זה? — זה שולחן.", en: "What is this? — It's a table." },
      why: { he: "על חפץ שואלים что.", en: "For a thing, ask что." } },
    { type: "choice", q: "Ты говори́шь по-англи́йски? — ___, не говорю́.", options: ["Да", "Нет", "Не"], answer: 1,
      tr: { he: "אתה מדבר אנגלית? — לא, אני לא מדבר.", en: "Do you speak English? — No, I don't." },
      why: { he: "'לא' כתשובה = нет. не בא לפני פועל.", en: "'No' as an answer is нет; не goes before a verb." } },
    { type: "fill", q: "Я ___ зна́ю. (not)", answer: ["не"],
      tr: { he: "אני לא יודע.", en: "I don't know." },
      why: { he: "не לפני הפועל.", en: "не goes before the verb." } },
    { type: "fill", q: "___ ты не спишь? — Я не уста́л.", answer: ["Почему́", "Почему"],
      tr: { he: "למה אתה לא ישן? — אני לא עייף.", en: "Why aren't you sleeping? — I'm not tired." },
      why: { he: "למה = почему́.", en: "Why = почему́." } },
    { type: "fill", q: "___ тебя́ зову́т? — Ма́ша.", answer: ["Как"],
      tr: { he: "איך קוראים לך? — מאשה.", en: "What's your name? — Masha." },
      why: { he: "ברוסית שואלים 'איך קוראים לך' — בדיוק כמו בעברית.", en: "Russian asks 'how do they call you' — like Hebrew 'איך קוראים לך'." } },
    { type: "order", answer: "Почему́ ты не рабо́таешь?",
      tr: { he: "למה אתה לא עובד?", en: "Why aren't you working?" } },
    { type: "order", answer: "Я ничего́ не понима́ю.",
      tr: { he: "אני לא מבין כלום.", en: "I don't understand anything." } },
    { type: "fix", q: "Я не ничего́ зна́ю.", answer: ["Я ничего́ не зна́ю."],
      tr: { he: "אני לא יודע כלום.", en: "I don't know anything." },
      why: { he: "не בא ישר לפני הפועל: ничего́ не зна́ю.", en: "не goes right before the verb: ничего́ не зна́ю." } }
  ]
});

LS_DATA.grammar.push({
  id: "ru_prepositional", target: "ru", level: 2, order: 10,
  title: { he: "יחסת המקום: в / на, где?", en: "Prepositional case: в / на, где?", ru: "Предло́жный паде́ж" },
  explain: {
    he: "<p>ברוסית לשמות עצם יש <b>יחסות</b> (паде́жи) — הסוף של המילה משתנה לפי התפקיד שלה במשפט. היחסה הראשונה: <b>יחסת המקום</b>, שעונה על השאלה <b>где?</b> (איפה?).</p><p>אחרי <b>в</b> (ב־, בתוך) ו־<b>на</b> (על, ב־) מוסיפים בדרך כלל <b>‎-е</b>:</p><table><tr><th>מילה</th><th>где?</th></tr><tr><td>стол</td><td>на столе́</td></tr><tr><td>шко́ла</td><td>в шко́ле</td></tr><tr><td>мо́ре</td><td>на мо́ре</td></tr><tr><td>Изра́иль</td><td>в Изра́иле</td></tr><tr><td>Росси́я (‎-ия)</td><td>в Росси́и</td></tr><tr><td>крова́ть (נקבה ‎-ь)</td><td>на крова́ти</td></tr></table><p>מילים ב־<b>‎-ия/-ие</b> ונקבה ב־<b>‎-ь</b> מקבלות <b>‎-и</b>.</p><p><b>на</b> משמש גם לכמה מקומות קבועים: на рабо́те (בעבודה), на у́лице (ברחוב), на ку́хне (במטבח), на мо́ре (בים), на конце́рте (בהופעה).</p><p>אותה יחסה באה גם אחרי <b>о</b> (על, בנושא): Мы говори́м о фи́льме.</p><p>'בבית' זה מילה מיוחדת: <b>до́ма</b>.</p>",
    en: "<p>Russian nouns have <b>cases</b> (паде́жи): the ending changes according to the word's job in the sentence. Our first case is the <b>prepositional</b>, which answers <b>где?</b> (where?).</p><p>After <b>в</b> (in) and <b>на</b> (on, at), most nouns take <b>-е</b>:</p><table><tr><th>Word</th><th>где?</th></tr><tr><td>стол</td><td>на столе́</td></tr><tr><td>шко́ла</td><td>в шко́ле</td></tr><tr><td>мо́ре</td><td>на мо́ре</td></tr><tr><td>Изра́иль</td><td>в Изра́иле</td></tr><tr><td>Росси́я (-ия)</td><td>в Росси́и</td></tr><tr><td>крова́ть (fem. -ь)</td><td>на крова́ти</td></tr></table><p>Nouns in <b>-ия/-ие</b> and feminine nouns in <b>-ь</b> take <b>-и</b>.</p><p><b>на</b> is also used with some fixed places: на рабо́те (at work), на у́лице (outside), на ку́хне (in the kitchen), на мо́ре (at the seaside), на конце́рте (at a concert).</p><p>The same case follows <b>о</b> (about): Мы говори́м о фи́льме (We're talking about the movie).</p><p>'At home' is a special word: <b>до́ма</b>.</p>"
  },
  examples: [
    { t: "Я живу́ в Изра́иле.", he: "אני גר בישראל.", en: "I live in Israel." },
    { t: "Кни́га на столе́.", he: "הספר על השולחן.", en: "The book is on the table." },
    { t: "Ма́ма на рабо́те.", he: "אמא בעבודה.", en: "Mom is at work." },
    { t: "Мы бы́ли в Москве́.", he: "היינו במוסקבה.", en: "We were in Moscow." },
    { t: "Ко́шка спит на крова́ти.", he: "החתולה ישנה על המיטה.", en: "The cat is sleeping on the bed." },
    { t: "Мы говори́м о фи́льме.", he: "אנחנו מדברים על הסרט.", en: "We are talking about the movie." }
  ],
  exercises: [
    { type: "choice", q: "Я живу́ в ___.", options: ["Изра́иль", "Изра́иле", "Изра́иля"], answer: 1,
      tr: { he: "אני גר בישראל.", en: "I live in Israel." },
      why: { he: "где? → יחסת המקום: ‎-е.", en: "где? → prepositional: -е." } },
    { type: "choice", q: "Ключи́ ___ столе́.", options: ["в", "на", "о"], answer: 1,
      tr: { he: "המפתחות על השולחן.", en: "The keys are on the table." },
      why: { he: "על משטח = на.", en: "On a surface = на." } },
    { type: "choice", q: "Па́па сейча́с ___ рабо́те.", options: ["в", "на", "о"], answer: 1,
      tr: { he: "אבא עכשיו בעבודה.", en: "Dad is at work now." },
      why: { he: "אומרים תמיד на рабо́те.", en: "It's always на рабо́те." } },
    { type: "fill", q: "Де́ти в ___. (шко́ла)", answer: ["шко́ле", "школе"],
      tr: { he: "הילדים בבית הספר.", en: "The children are at school." },
      why: { he: "‎-а → ‎-е.", en: "-а → -е." } },
    { type: "fill", q: "Ба́бушка живёт в ___. (Росси́я)", answer: ["Росси́и", "России"],
      tr: { he: "סבתא גרה ברוסיה.", en: "Grandma lives in Russia." },
      why: { he: "מילים ב־‎-ия → ‎-ии.", en: "Words in -ия → -ии." } },
    { type: "fill", q: "Мы гуля́ли в ___. (парк)", answer: ["па́рке", "парке"],
      tr: { he: "טיילנו בפארק.", en: "We walked in the park." },
      why: { he: "זכר: מוסיפים ‎-е.", en: "Masculine: add -е." } },
    { type: "fill", q: "Ко́шка спит на ___. (крова́ть)", answer: ["крова́ти", "кровати"],
      tr: { he: "החתולה ישנה על המיטה.", en: "The cat is sleeping on the bed." },
      why: { he: "נקבה ב־‎-ь → ‎-и.", en: "Feminine in -ь → -и." } },
    { type: "order", answer: "Мой брат живёт в Москве́.",
      tr: { he: "אחי גר במוסקבה.", en: "My brother lives in Moscow." } },
    { type: "fix", q: "Я живу́ в Тель-Ави́в.", answer: ["Я живу́ в Тель-Ави́ве."],
      tr: { he: "אני גר בתל אביב.", en: "I live in Tel Aviv." },
      why: { he: "где? → צריך ‎-е: в Тель-Ави́ве.", en: "где? needs -е: в Тель-Ави́ве." } },
    { type: "fix", q: "Кни́га на стол.", answer: ["Кни́га на столе́."],
      tr: { he: "הספר על השולחן.", en: "The book is on the table." },
      why: { he: "на + מקום → ‎-е: на столе́.", en: "на + location → -е: на столе́." } }
  ]
});

LS_DATA.grammar.push({
  id: "ru_accusative", target: "ru", level: 2, order: 11,
  title: { he: "יחסת המושא (את)", en: "Accusative case (direct object)", ru: "Вини́тельный паде́ж" },
  explain: {
    he: "<p>בעברית מסמנים מושא ישיר עם <b>את</b> ('אני קורא את הספר'). ברוסית אין 'את' — במקום זה <b>הסוף של המילה משתנה</b>. זה גם מה שמאפשר סדר מילים חופשי.</p><table><tr><th>סוג</th><th>שינוי</th><th>דוגמה</th></tr><tr><td>נקבה ‎-а / -я</td><td>‎-у / -ю</td><td>кни́га → кни́гу</td></tr><tr><td>זכר דומם, סתמי</td><td>לא משתנה</td><td>стол, окно́, фильм</td></tr><tr><td>נקבה ב־‎-ь</td><td>לא משתנה</td><td>дверь</td></tr><tr><td>זכר חי (אנשים, חיות)</td><td>‎-а / -я</td><td>брат → бра́та, учи́тель → учи́теля</td></tr></table><p>כינויים: меня́ (אותי), тебя́ (אותך), его́ (אותו), её (אותה), нас, вас, их. <b>Я люблю́ тебя́</b> = אני אוהב אותך.</p><p>גם 'שלי' משתנה בנקבה: моя́ → <b>мою́</b>: Я люблю́ мою́ ма́му.</p><p>אותה יחסה באה אחרי <b>в/на</b> כשעונים על <b>куда́?</b> (לאן?): <b>в шко́лу</b> (לבית הספר), <b>на рабо́ту</b> (לעבודה). השוו: где? в шко́ле (איפה?) / куда́? в шко́лу (לאן?).</p>",
    en: "<p>In Hebrew a definite direct object is marked with <b>את</b>. Russian has no such word — instead, <b>the ending of the noun changes</b>. That's also what lets Russian word order be so free.</p><table><tr><th>Type</th><th>Change</th><th>Example</th></tr><tr><td>feminine -а / -я</td><td>-у / -ю</td><td>кни́га → кни́гу</td></tr><tr><td>masc. things, neuter</td><td>no change</td><td>стол, окно́, фильм</td></tr><tr><td>feminine in -ь</td><td>no change</td><td>дверь</td></tr><tr><td>masc. living (people, animals)</td><td>-а / -я</td><td>брат → бра́та, учи́тель → учи́теля</td></tr></table><p>Pronouns: меня́ (me), тебя́ (you), его́ (him), её (her), нас (us), вас (you), их (them). <b>Я люблю́ тебя́</b> = I love you.</p><p>Feminine 'my' changes too: моя́ → <b>мою́</b>: Я люблю́ мою́ ма́му.</p><p>The same case follows <b>в/на</b> when answering <b>куда́?</b> (where to?): <b>в шко́лу</b> (to school), <b>на рабо́ту</b> (to work). Compare: где? в шко́ле (at school) / куда́? в шко́лу (to school).</p>"
  },
  examples: [
    { t: "Я чита́ю кни́гу.", he: "אני קורא ספר.", en: "I am reading a book." },
    { t: "Ты лю́бишь шокола́д?", he: "אתה אוהב שוקולד?", en: "Do you like chocolate?" },
    { t: "Я жду дру́га.", he: "אני מחכה לחבר.", en: "I'm waiting for a friend." },
    { t: "Ма́ма идёт на рабо́ту.", he: "אמא הולכת לעבודה.", en: "Mom is going to work." },
    { t: "Я люблю́ тебя́.", he: "אני אוהב אותך.", en: "I love you." },
    { t: "Она́ пьёт во́ду.", he: "היא שותה מים.", en: "She is drinking water." }
  ],
  exercises: [
    { type: "choice", q: "Я чита́ю ___.", options: ["кни́га", "кни́гу", "кни́ге"], answer: 1,
      tr: { he: "אני קורא ספר.", en: "I am reading a book." },
      why: { he: "מושא ישיר, נקבה: ‎-а → ‎-у.", en: "Direct object, feminine: -а → -у." } },
    { type: "choice", q: "Мы смо́трим ___.", options: ["фильм", "фи́льма", "фи́льму"], answer: 0,
      tr: { he: "אנחנו צופים בסרט.", en: "We are watching a movie." },
      why: { he: "זכר דומם לא משתנה.", en: "A masculine thing doesn't change." } },
    { type: "choice", q: "Я жду ___.", options: ["брат", "бра́та", "бра́ту"], answer: 1,
      tr: { he: "אני מחכה לאח שלי.", en: "I'm waiting for my brother." },
      why: { he: "זכר חי (אדם) מקבל ‎-а.", en: "A living masculine noun takes -а." } },
    { type: "choice", q: "Ты лю́бишь ___?", options: ["я", "меня́", "мне"], answer: 1,
      tr: { he: "אתה אוהב אותי?", en: "Do you love me?" },
      why: { he: "'אותי' = меня́.", en: "'Me' as an object = меня́." } },
    { type: "fill", q: "Она́ пьёт ___. (вода́)", answer: ["во́ду", "воду"],
      tr: { he: "היא שותה מים.", en: "She is drinking water." },
      why: { he: "‎-а → ‎-у, וההטעמה זזה: во́ду.", en: "-а → -у, and the stress moves: во́ду." } },
    { type: "fill", q: "Мы идём в ___. (шко́ла)", answer: ["шко́лу", "школу"],
      tr: { he: "אנחנו הולכים לבית הספר.", en: "We are going to school." },
      why: { he: "куда́? (לאן) → יחסת המושא: шко́лу.", en: "куда́? (where to) → accusative: шко́лу." } },
    { type: "fill", q: "Я слу́шаю ___. (му́зыка)", answer: ["му́зыку", "музыку"],
      tr: { he: "אני מקשיב למוזיקה.", en: "I'm listening to music." },
      why: { he: "ברוסית 'слу́шать' לוקח מושא ישיר: му́зыку.", en: "слу́шать takes a direct object: му́зыку." } },
    { type: "order", answer: "Ма́ма покупа́ет хлеб и молоко́.",
      tr: { he: "אמא קונה לחם וחלב.", en: "Mom is buying bread and milk." } },
    { type: "fix", q: "Я ви́жу ма́ма.", answer: ["Я ви́жу ма́му."],
      tr: { he: "אני רואה את אמא.", en: "I see Mom." },
      why: { he: "מושא ישיר: ма́ма → ма́му.", en: "Direct object: ма́ма → ма́му." } },
    { type: "fix", q: "Па́па идёт на рабо́та.", answer: ["Па́па идёт на рабо́ту."],
      tr: { he: "אבא הולך לעבודה.", en: "Dad is going to work." },
      why: { he: "לאן? → на рабо́ту.", en: "Where to? → на рабо́ту." } }
  ]
});

LS_DATA.grammar.push({
  id: "ru_u_menya_est", target: "ru", level: 2, order: 12,
  title: { he: "יש לי — у меня́ есть", en: "I have — у меня́ есть", ru: "У меня́ есть" },
  explain: {
    he: "<p>חדשות טובות: ברוסית אומרים 'יש לי' כמעט כמו בעברית! במקום פועל 'to have' כמו באנגלית, אומרים <b>у меня́ есть</b> — מילולית 'אצלי יש'.</p><table><tr><th>יש ל...</th><th>רוסית</th></tr><tr><td>יש לי</td><td>у меня́ есть</td></tr><tr><td>יש לך</td><td>у тебя́ есть</td></tr><tr><td>יש לו / לה</td><td>у него́ / у неё есть</td></tr><tr><td>יש לנו</td><td>у нас есть</td></tr><tr><td>יש לכם</td><td>у вас есть</td></tr><tr><td>יש להם</td><td>у них есть</td></tr></table><p>שימו לב: אחרי <b>у</b> כינויי הגוף של 'הוא/היא/הם' מקבלים <b>н</b>: у <b>н</b>его́, у <b>н</b>её, у <b>н</b>их.</p><p>עם שמות: у ма́мы, у бра́та, у А́нны (סוף של יחסת הקניין — נלמד בשיעור הבא).</p><p>הדבר שיש לך נשאר בצורה הרגילה: У меня́ есть <b>соба́ка</b>.</p><p>בעבר: 'היה לי' — הפועל מתאים לדבר שהיה, כמו בעברית: У меня́ <b>был</b> кот. У меня́ <b>была́</b> соба́ка.</p><p>כשמתארים משהו, אפשר להשמיט есть: У него́ краси́вые глаза́.</p>",
    en: "<p>Good news: Russian says 'I have' almost like Hebrew 'יש לי'! Instead of a verb 'to have', you say <b>у меня́ есть</b> — literally 'by me there is'.</p><table><tr><th>English</th><th>Russian</th></tr><tr><td>I have</td><td>у меня́ есть</td></tr><tr><td>you have</td><td>у тебя́ есть</td></tr><tr><td>he / she has</td><td>у него́ / у неё есть</td></tr><tr><td>we have</td><td>у нас есть</td></tr><tr><td>you (pl.) have</td><td>у вас есть</td></tr><tr><td>they have</td><td>у них есть</td></tr></table><p>Note: after <b>у</b>, the pronouns for he/she/they get an <b>н</b>: у <b>н</b>его́, у <b>н</b>её, у <b>н</b>их.</p><p>With names and nouns: у ма́мы, у бра́та, у А́нны (genitive endings — next lesson).</p><p>The thing you have stays in its normal form: У меня́ есть <b>соба́ка</b> (I have a dog).</p><p>In the past, the verb agrees with the thing owned, like Hebrew 'היה לי / הייתה לי': У меня́ <b>был</b> кот. У меня́ <b>была́</b> соба́ка.</p><p>When describing, есть is often dropped: У него́ краси́вые глаза́ (He has beautiful eyes).</p>"
  },
  examples: [
    { t: "У меня́ есть брат.", he: "יש לי אח.", en: "I have a brother." },
    { t: "У тебя́ есть ру́чка?", he: "יש לך עט?", en: "Do you have a pen?" },
    { t: "У нас есть соба́ка.", he: "יש לנו כלב.", en: "We have a dog." },
    { t: "У Ма́ши есть но́вый телефо́н.", he: "למאשה יש טלפון חדש.", en: "Masha has a new phone." },
    { t: "У меня́ была́ ко́шка.", he: "הייתה לי חתולה.", en: "I had a cat." },
    { t: "У него́ краси́вые глаза́.", he: "יש לו עיניים יפות.", en: "He has beautiful eyes." }
  ],
  exercises: [
    { type: "choice", q: "___ есть сестра́.", options: ["Я", "У меня́", "Мне"], answer: 1,
      tr: { he: "יש לי אחות.", en: "I have a sister." },
      why: { he: "'יש לי' = у меня́ есть.", en: "'I have' = у меня́ есть." } },
    { type: "choice", q: "У ___ есть маши́на?", options: ["ты", "тебя́", "тебе́"], answer: 1,
      tr: { he: "יש לך מכונית?", en: "Do you have a car?" },
      why: { he: "אחרי у: тебя́.", en: "After у: тебя́." } },
    { type: "choice", q: "У неё ___ соба́ка.", options: ["был", "была́", "бы́ло"], answer: 1,
      tr: { he: "היה לה כלב.", en: "She had a dog." },
      why: { he: "הפועל מתאים ל־соба́ка (נקבה): была́.", en: "The verb agrees with соба́ка (feminine): была́." } },
    { type: "choice", q: "У ___ есть дом.", options: ["они́", "их", "них"], answer: 2,
      tr: { he: "יש להם בית.", en: "They have a house." },
      why: { he: "אחרי у מוסיפים н: у них.", en: "After у add н: у них." } },
    { type: "fill", q: "У ___ есть кот. (он)", answer: ["него́", "него"],
      tr: { he: "יש לו חתול.", en: "He has a cat." },
      why: { he: "у + он → у него́.", en: "у + он → у него́." } },
    { type: "fill", q: "У ___ есть кни́га? (вы)", answer: ["вас"],
      tr: { he: "יש לכם ספר?", en: "Do you have a book?" },
      why: { he: "у + вы → у вас.", en: "у + вы → у вас." } },
    { type: "fill", q: "У меня́ ___ велосипе́д. (быть)", answer: ["был"],
      tr: { he: "היו לי אופניים.", en: "I had a bike." },
      why: { he: "велосипе́д זכר: был.", en: "велосипе́д is masculine: был." } },
    { type: "order", answer: "У тебя́ есть брат?",
      tr: { he: "יש לך אח?", en: "Do you have a brother?" } },
    { type: "order", answer: "У нас есть большо́й дом.",
      tr: { he: "יש לנו בית גדול.", en: "We have a big house." } },
    { type: "fix", q: "У я есть брат.", answer: ["У меня́ есть брат."],
      tr: { he: "יש לי אח.", en: "I have a brother." },
      why: { he: "אחרי у צריך меня́.", en: "After у you need меня́." } }
  ]
});

LS_DATA.grammar.push({
  id: "ru_genitive", target: "ru", level: 3, order: 13,
  title: { he: "יחסת הקניין: нет, 'של', ומספרים", en: "Genitive basics: нет, 'of', numbers", ru: "Роди́тельный паде́ж" },
  explain: {
    he: "<p>יחסת הקניין (роди́тельный) משמשת להרבה דברים. שלושה שימושים בסיסיים:</p><ul><li><b>אין</b>: нет + יחסת קניין. У меня́ нет <b>бра́та</b>. (אין לי אח.)</li><li><b>של</b>: кни́га <b>бра́та</b> (הספר של האח). כמו סמיכות בעברית!</li><li><b>אחרי מספרים</b>.</li></ul><table><tr><th>סוג</th><th>סיומת</th><th>דוגמה</th></tr><tr><td>זכר, סתמי</td><td>‎-а / -я</td><td>брат → бра́та, мо́ре → мо́ря</td></tr><tr><td>נקבה</td><td>‎-ы / -и</td><td>ма́ма → ма́мы, кни́га → кни́ги</td></tr></table><p><b>מספרים:</b></p><ul><li>1 + צורה רגילה: оди́н стол, одна́ кни́га</li><li>2, 3, 4 + יחסת קניין יחיד: два <b>стола́</b>, три <b>кни́ги</b> (בנקבה 'שתיים' = <b>две</b>)</li><li>5 ומעלה + יחסת קניין רבים: пять <b>столо́в</b>, пять <b>книг</b></li></ul><p>שנים: оди́н год, два <b>го́да</b>, пять <b>лет</b>. ביטוי שימושי: У меня́ нет вре́мени (אין לי זמן).</p>",
    en: "<p>The genitive case (роди́тельный) has many jobs. Three basic ones:</p><ul><li><b>Absence</b>: нет + genitive. У меня́ нет <b>бра́та</b>. (I don't have a brother.)</li><li><b>'Of' / possession</b>: кни́га <b>бра́та</b> (my brother's book, lit. 'book of brother'). Like Hebrew סמיכות!</li><li><b>After numbers</b>.</li></ul><table><tr><th>Type</th><th>Ending</th><th>Example</th></tr><tr><td>masc., neuter</td><td>-а / -я</td><td>брат → бра́та, мо́ре → мо́ря</td></tr><tr><td>feminine</td><td>-ы / -и</td><td>ма́ма → ма́мы, кни́га → кни́ги</td></tr></table><p><b>Numbers:</b></p><ul><li>1 + normal form: оди́н стол, одна́ кни́га</li><li>2, 3, 4 + genitive singular: два <b>стола́</b>, три <b>кни́ги</b> (feminine 'two' = <b>две</b>)</li><li>5 and up + genitive plural: пять <b>столо́в</b>, пять <b>книг</b></li></ul><p>Years: оди́н год, два <b>го́да</b>, пять <b>лет</b>. Useful phrase: У меня́ нет вре́мени (I have no time).</p>"
  },
  examples: [
    { t: "У меня́ нет бра́та.", he: "אין לי אח.", en: "I don't have a brother." },
    { t: "Сего́дня нет уро́ка.", he: "היום אין שיעור.", en: "There's no class today." },
    { t: "Э́то маши́на па́пы.", he: "זאת המכונית של אבא.", en: "This is Dad's car." },
    { t: "У меня́ два бра́та и три сестры́.", he: "יש לי שני אחים ושלוש אחיות.", en: "I have two brothers and three sisters." },
    { t: "Я жил там два го́да.", he: "גרתי שם שנתיים.", en: "I lived there for two years." },
    { t: "В кла́ссе пять ма́льчиков.", he: "בכיתה יש חמישה בנים.", en: "There are five boys in the class." }
  ],
  exercises: [
    { type: "choice", q: "У меня́ нет ___.", options: ["брат", "бра́та", "бра́ту"], answer: 1,
      tr: { he: "אין לי אח.", en: "I don't have a brother." },
      why: { he: "нет + יחסת קניין: бра́та.", en: "нет + genitive: бра́та." } },
    { type: "choice", q: "Здесь нет ___.", options: ["вода́", "во́ду", "воды́"], answer: 2,
      tr: { he: "אין כאן מים.", en: "There's no water here." },
      why: { he: "נקבה ‎-а → ‎-ы: воды́.", en: "Feminine -а → -ы: воды́." } },
    { type: "choice", q: "два ___", options: ["стол", "стола́", "столо́в"], answer: 1,
      tr: { he: "שני שולחנות", en: "two tables" },
      why: { he: "2-4 + יחסת קניין יחיד.", en: "2-4 + genitive singular." } },
    { type: "choice", q: "пять ___", options: ["год", "го́да", "лет"], answer: 2,
      tr: { he: "חמש שנים", en: "five years" },
      why: { he: "5 ומעלה + лет (צורה מיוחדת).", en: "5 and up + лет (a special form)." } },
    { type: "fill", q: "У нас нет ___. (маши́на)", answer: ["маши́ны", "машины"],
      tr: { he: "אין לנו מכונית.", en: "We don't have a car." },
      why: { he: "нет + נקבה: ‎-ы.", en: "нет + feminine: -ы." } },
    { type: "fill", q: "Э́то кни́га ___. (учи́тель)", answer: ["учи́теля", "учителя"],
      tr: { he: "זה הספר של המורה.", en: "This is the teacher's book." },
      why: { he: "'של' = יחסת קניין. ‎-ь → ‎-я.", en: "'Of' = genitive. -ь → -я." } },
    { type: "fill", q: "У меня́ три ___. (сестра́)", answer: ["сестры́", "сестры"],
      tr: { he: "יש לי שלוש אחיות.", en: "I have three sisters." },
      why: { he: "3 + יחסת קניין יחיד: сестры́.", en: "3 + genitive singular: сестры́." } },
    { type: "order", answer: "У меня́ нет вре́мени.",
      tr: { he: "אין לי זמן.", en: "I have no time." } },
    { type: "fix", q: "У меня́ нет соба́ка.", answer: ["У меня́ нет соба́ки."],
      tr: { he: "אין לי כלב.", en: "I don't have a dog." },
      why: { he: "אחרי нет צריך יחסת קניין: соба́ки.", en: "After нет use the genitive: соба́ки." } },
    { type: "fix", q: "У него́ два брат.", answer: ["У него́ два бра́та."],
      tr: { he: "יש לו שני אחים.", en: "He has two brothers." },
      why: { he: "אחרי 2 צריך יחסת קניין: бра́та.", en: "After 2 use the genitive: бра́та." } }
  ]
});

LS_DATA.grammar.push({
  id: "ru_dative", target: "ru", level: 3, order: 14,
  title: { he: "יחסת הנמען: мне нра́вится, мне хо́лодно", en: "Dative basics: мне нра́вится, мне хо́лодно", ru: "Да́тельный паде́ж" },
  explain: {
    he: "<p>יחסת הנמען (да́тельный) עונה על 'ל...' — <b>למי?</b> והיא מאוד דומה לעברית!</p><table><tr><th>לי</th><th>לך</th><th>לו</th><th>לה</th><th>לנו</th><th>לכם</th><th>להם</th></tr><tr><td>мне</td><td>тебе́</td><td>ему́</td><td>ей</td><td>нам</td><td>вам</td><td>им</td></tr></table><p><b>קר לי / חם לי / משעמם לי</b> — בדיוק כמו בעברית: <b>Мне хо́лодно. Мне жа́рко. Мне ску́чно.</b> (באנגלית אומרים I am cold, אבל ברוסית — 'לי קר'.)</p><p><b>אני אוהב (משהו)</b> — <b>Мне нра́вится</b> му́зыка, מילולית 'המוזיקה מוצאת חן בעיני'. הדבר שאוהבים הוא הנושא, לכן ברבים: Мне <b>нра́вятся</b> ко́шки.</p><p><b>גיל</b>: Мне пятна́дцать лет (אני בן 15). <b>צריך</b>: Мне на́до идти́ (אני צריך ללכת).</p><p>שמות עצם: זכר/סתמי <b>‎-у/-ю</b> (бра́ту), נקבה <b>‎-е</b> (ма́ме). לתת/להתקשר ל...: Я звоню́ <b>ма́ме</b>.</p>",
    en: "<p>The dative case (да́тельный) answers <b>to whom? / for whom?</b> — and it works a lot like Hebrew 'ל...'!</p><table><tr><th>me</th><th>you</th><th>him</th><th>her</th><th>us</th><th>you (pl.)</th><th>them</th></tr><tr><td>мне</td><td>тебе́</td><td>ему́</td><td>ей</td><td>нам</td><td>вам</td><td>им</td></tr></table><p><b>Feelings and states</b> — exactly like Hebrew 'קר לי': <b>Мне хо́лодно</b> (I'm cold), <b>Мне жа́рко</b> (I'm hot), <b>Мне ску́чно</b> (I'm bored). Literally 'to me it's cold'.</p><p><b>Liking</b> — <b>Мне нра́вится</b> му́зыка, literally 'music is pleasing to me'. The thing you like is the subject, so in the plural: Мне <b>нра́вятся</b> ко́шки (I like cats).</p><p><b>Age</b>: Мне пятна́дцать лет (I'm 15). <b>Need to</b>: Мне на́до идти́ (I need to go).</p><p>Noun endings: masc./neuter <b>-у/-ю</b> (бра́ту), feminine <b>-е</b> (ма́ме). Giving/calling someone: Я звоню́ <b>ма́ме</b> (I'm calling Mom).</p>"
  },
  examples: [
    { t: "Мне нра́вится э́тот фильм.", he: "הסרט הזה מוצא חן בעיני.", en: "I like this movie." },
    { t: "Тебе́ хо́лодно? — Нет, мне жа́рко.", he: "קר לך? — לא, חם לי.", en: "Are you cold? — No, I'm hot." },
    { t: "Ей нра́вятся ко́шки.", he: "היא אוהבת חתולים.", en: "She likes cats." },
    { t: "Мне пятна́дцать лет.", he: "אני בן חמש עשרה.", en: "I am fifteen years old." },
    { t: "Я звоню́ ма́ме.", he: "אני מתקשר לאמא.", en: "I'm calling Mom." },
    { t: "Нам на́до идти́.", he: "אנחנו צריכים ללכת.", en: "We need to go." }
  ],
  exercises: [
    { type: "choice", q: "___ нра́вится му́зыка.", options: ["Я", "Меня́", "Мне"], answer: 2,
      tr: { he: "אני אוהב מוזיקה.", en: "I like music." },
      why: { he: "нра́вится + יחסת הנמען: мне.", en: "нра́вится takes the dative: мне." } },
    { type: "choice", q: "Ему́ ___ э́ти пе́сни.", options: ["нра́вится", "нра́вятся", "нра́вишься"], answer: 1,
      tr: { he: "השירים האלה מוצאים חן בעיניו.", en: "He likes these songs." },
      why: { he: "пе́сни ברבים, לכן нра́вятся.", en: "пе́сни is plural, so нра́вятся." } },
    { type: "choice", q: "___ хо́лодно?", options: ["Ты", "Тебя́", "Тебе́"], answer: 2,
      tr: { he: "קר לך?", en: "Are you cold?" },
      why: { he: "'קר לך' = тебе́ хо́лодно.", en: "'To you it's cold' = тебе́ хо́лодно." } },
    { type: "choice", q: "Я звоню́ ___.", options: ["ма́ма", "ма́му", "ма́ме"], answer: 2,
      tr: { he: "אני מתקשר לאמא.", en: "I'm calling Mom." },
      why: { he: "звони́ть + למי? → יחסת הנמען: ма́ме.", en: "звони́ть + to whom? → dative: ма́ме." } },
    { type: "fill", q: "___ ску́чно. (мы)", answer: ["Нам"],
      tr: { he: "משעמם לנו.", en: "We're bored." },
      why: { he: "мы → нам.", en: "мы → нам." } },
    { type: "fill", q: "Ско́лько ___ лет? (ты)", answer: ["тебе́", "тебе"],
      tr: { he: "בן כמה אתה?", en: "How old are you?" },
      why: { he: "גיל ביחסת הנמען: тебе́.", en: "Age uses the dative: тебе́." } },
    { type: "fill", q: "Я даю́ кни́гу ___. (брат)", answer: ["бра́ту", "брату"],
      tr: { he: "אני נותן את הספר לאח שלי.", en: "I'm giving the book to my brother." },
      why: { he: "למי? זכר → ‎-у.", en: "To whom? masculine → -у." } },
    { type: "order", answer: "Мне о́чень нра́вится Москва́.",
      tr: { he: "מוסקבה מאוד מוצאת חן בעיני.", en: "I really like Moscow." } },
    { type: "fix", q: "Я хо́лодно.", answer: ["Мне хо́лодно."],
      tr: { he: "קר לי.", en: "I'm cold." },
      why: { he: "כמו בעברית — 'לי קר': мне.", en: "Like Hebrew 'קר לי' — use мне." } },
    { type: "fix", q: "Мне нра́вится э́ти кни́ги.", answer: ["Мне нра́вятся э́ти кни́ги."],
      tr: { he: "הספרים האלה מוצאים חן בעיני.", en: "I like these books." },
      why: { he: "кни́ги רבים → нра́вятся.", en: "кни́ги is plural → нра́вятся." } }
  ]
});

LS_DATA.grammar.push({
  id: "ru_instrumental", target: "ru", level: 3, order: 15,
  title: { he: "יחסת הכלי: с кем?", en: "Instrumental basics: с кем?", ru: "Твори́тельный паде́ж" },
  explain: {
    he: "<p>יחסת הכלי (твори́тельный) עונה על <b>с кем?</b> (עם מי?) ו־<b>с чем?</b> (עם מה?).</p><table><tr><th>סוג</th><th>סיומת</th><th>דוגמה</th></tr><tr><td>זכר, סתמי</td><td>‎-ом / -ем</td><td>брат → с бра́том, учи́тель → с учи́телем</td></tr><tr><td>נקבה</td><td>‎-ой / -ей</td><td>ма́ма → с ма́мой, Та́ня → с Та́ней</td></tr></table><p><b>כינויים:</b> со мной (איתי), с тобо́й (איתך), с ним (איתו), с ней (איתה), с на́ми (איתנו), с ва́ми (איתכם), с ни́ми (איתם).</p><p>שימושים נפוצים:</p><ul><li><b>ביחד עם</b>: Я гуля́ю с дру́гом.</li><li><b>אוכל</b>: чай с молоко́м (תה עם חלב), бутербро́д с сы́ром.</li><li><b>בעזרת</b> (בלי с!): Я пишу́ <b>ру́чкой</b> — אני כותב בעט. כמו 'ב־' בעברית.</li><li><b>מקצוע בעתיד</b>: Я хочу́ быть <b>врачо́м</b>.</li></ul>",
    en: "<p>The instrumental case (твори́тельный) answers <b>с кем?</b> (with whom?) and <b>с чем?</b> (with what?).</p><table><tr><th>Type</th><th>Ending</th><th>Example</th></tr><tr><td>masc., neuter</td><td>-ом / -ем</td><td>брат → с бра́том, учи́тель → с учи́телем</td></tr><tr><td>feminine</td><td>-ой / -ей</td><td>ма́ма → с ма́мой, Та́ня → с Та́ней</td></tr></table><p><b>Pronouns:</b> со мной (with me), с тобо́й (with you), с ним (with him), с ней (with her), с на́ми (with us), с ва́ми (with you, pl.), с ни́ми (with them).</p><p>Common uses:</p><ul><li><b>Together with</b>: Я гуля́ю с дру́гом (I'm walking with a friend).</li><li><b>Food</b>: чай с молоко́м (tea with milk), бутербро́д с сы́ром (a cheese sandwich).</li><li><b>Using a tool</b> (no с!): Я пишу́ <b>ру́чкой</b> — I write with a pen. Like Hebrew 'כותב בעט'.</li><li><b>Future job</b>: Я хочу́ быть <b>врачо́м</b> (I want to be a doctor).</li></ul>"
  },
  examples: [
    { t: "Я гуля́ю с дру́гом.", he: "אני מטייל עם חבר.", en: "I'm walking with a friend." },
    { t: "Ты пойдёшь со мной?", he: "תלך איתי?", en: "Will you go with me?" },
    { t: "Чай с молоко́м, пожа́луйста.", he: "תה עם חלב, בבקשה.", en: "Tea with milk, please." },
    { t: "Она́ говори́т с ма́мой.", he: "היא מדברת עם אמא.", en: "She is talking with Mom." },
    { t: "Я пишу́ ру́чкой.", he: "אני כותב בעט.", en: "I write with a pen." },
    { t: "С кем ты был вчера́?", he: "עם מי היית אתמול?", en: "Who were you with yesterday?" }
  ],
  exercises: [
    { type: "choice", q: "Я игра́ю с ___.", options: ["брат", "бра́том", "бра́та"], answer: 1,
      tr: { he: "אני משחק עם אח שלי.", en: "I'm playing with my brother." },
      why: { he: "с + יחסת הכלי, זכר: ‎-ом.", en: "с + instrumental, masculine: -ом." } },
    { type: "choice", q: "Ты пойдёшь ___?", options: ["с я", "со мной", "с меня́"], answer: 1,
      tr: { he: "תלך איתי?", en: "Will you go with me?" },
      why: { he: "'איתי' = со мной.", en: "'With me' = со мной." } },
    { type: "choice", q: "Ко́фе с ___, пожа́луйста.", options: ["са́хар", "са́харом", "са́хара"], answer: 1,
      tr: { he: "קפה עם סוכר, בבקשה.", en: "Coffee with sugar, please." },
      why: { he: "с + זכר: ‎-ом.", en: "с + masculine: -ом." } },
    { type: "fill", q: "Он говори́т с ___. (сестра́)", answer: ["сестро́й", "сестрой"],
      tr: { he: "הוא מדבר עם אחותו.", en: "He is talking with his sister." },
      why: { he: "נקבה: ‎-а → ‎-ой.", en: "Feminine: -а → -ой." } },
    { type: "fill", q: "Я живу́ с ___. (ба́бушка)", answer: ["ба́бушкой", "бабушкой"],
      tr: { he: "אני גר עם סבתא.", en: "I live with my grandma." },
      why: { he: "נקבה: ‎-ой.", en: "Feminine: -ой." } },
    { type: "fill", q: "Мы бы́ли в кино́ с ___. (друг)", answer: ["дру́гом", "другом"],
      tr: { he: "היינו בקולנוע עם חבר.", en: "We were at the movies with a friend." },
      why: { he: "זכר: ‎-ом.", en: "Masculine: -ом." } },
    { type: "fill", q: "С ___ ты идёшь в кино́? (кто)", answer: ["кем"],
      tr: { he: "עם מי אתה הולך לקולנוע?", en: "Who are you going to the movies with?" },
      why: { he: "кто ביחסת הכלי = кем.", en: "кто in the instrumental is кем." } },
    { type: "order", answer: "Я гуля́ю с соба́кой.",
      tr: { he: "אני מטייל עם הכלב.", en: "I'm walking the dog." } },
    { type: "fix", q: "Я иду́ в парк с ма́ма.", answer: ["Я иду́ в парк с ма́мой."],
      tr: { he: "אני הולך לפארק עם אמא.", en: "I'm going to the park with Mom." },
      why: { he: "с + נקבה → ‎-ой: с ма́мой.", en: "с + feminine → -ой: с ма́мой." } },
    { type: "fix", q: "Он говори́т с она́.", answer: ["Он говори́т с ней."],
      tr: { he: "הוא מדבר איתה.", en: "He is talking with her." },
      why: { he: "'איתה' = с ней.", en: "'With her' = с ней." } }
  ]
});
