// English grammar lessons for Hebrew/Russian speakers (beginner).
window.LS_DATA = window.LS_DATA || {};
LS_DATA.grammar = LS_DATA.grammar || [];

LS_DATA.grammar.push({
  id: "en_to_be", target: "en", level: 1, order: 1,
  title: { he: "הפועל to be: am / is / are", ru: "Глагол to be: am / is / are", en: "To be: am / is / are" },
  explain: {
    he: "<p>בעברית אומרים «אני שמחה» – בלי פועל באמצע. באנגלית זה <b>לא עובד</b>: חייבים פועל. הפועל הוא <b>to be</b> (להיות), ובהווה יש לו שלוש צורות:</p><table><tr><td>I</td><td><b>am</b></td></tr><tr><td>he / she / it</td><td><b>is</b></td></tr><tr><td>you / we / they</td><td><b>are</b></td></tr></table><ul><li>I <b>am</b> happy. – אני שמחה.</li><li>She <b>is</b> a doctor. – היא רופאה.</li><li>We <b>are</b> at home. – אנחנו בבית.</li></ul><p><b>שלילה:</b> שמים <b>not</b> אחרי הפועל: She is <b>not</b> here.</p><p><b>שאלה:</b> מעבירים את הפועל להתחלה: <b>Are</b> you ready?</p><p>בדיבור מקצרים: I'm, you're, he's, she's, it's, we're, they're, isn't, aren't.</p><p>טיפ: כשבעברית אין פועל במשפט – באנגלית כמעט תמיד צריך am / is / are.</p>",
    ru: "<p>По-русски мы говорим «Я счастлива» или «Она врач» – без глагола. В английском так <b>нельзя</b>: глагол обязателен. Это глагол <b>to be</b> (быть), и в настоящем времени у него три формы:</p><table><tr><td>I</td><td><b>am</b></td></tr><tr><td>he / she / it</td><td><b>is</b></td></tr><tr><td>you / we / they</td><td><b>are</b></td></tr></table><ul><li>I <b>am</b> happy. – Я счастлива.</li><li>She <b>is</b> a doctor. – Она врач.</li><li>We <b>are</b> at home. – Мы дома.</li></ul><p><b>Отрицание:</b> ставим <b>not</b> после глагола: She is <b>not</b> here.</p><p><b>Вопрос:</b> переносим глагол в начало: <b>Are</b> you ready?</p><p>В разговоре сокращаем: I'm, you're, he's, she's, it's, we're, they're, isn't, aren't.</p><p>Совет: если в русской фразе нет глагола – в английской почти всегда нужен am / is / are.</p>"
  },
  examples: [
    { t: "I am happy.", he: "אני שמחה.", ru: "Я сча́стлива." },
    { t: "She is a doctor.", he: "היא רופאה.", ru: "Она́ врач." },
    { t: "We are at home.", he: "אנחנו בבית.", ru: "Мы до́ма." },
    { t: "It is cold today.", he: "היום קר.", ru: "Сего́дня хо́лодно." },
    { t: "They are not here.", he: "הם לא כאן.", ru: "Их здесь нет." },
    { t: "Are you tired?", he: "את עייפה?", ru: "Ты уста́ла?" }
  ],
  exercises: [
    { type: "choice", q: "She ___ a doctor.", options: ["am", "is", "are"], answer: 1, tr: { he: "היא רופאה.", ru: "Она́ врач." }, why: { he: "עם she משתמשים ב-is.", ru: "С she всегда is." } },
    { type: "choice", q: "I ___ a student.", options: ["am", "is", "are"], answer: 0, tr: { he: "אני סטודנטית.", ru: "Я студе́нтка." }, why: { he: "עם I תמיד am.", ru: "С I всегда am." } },
    { type: "fill", q: "They ___ at home.", answer: ["are"], tr: { he: "הם בבית.", ru: "Они́ до́ма." }, why: { he: "עם they משתמשים ב-are.", ru: "С they нужно are." } },
    { type: "fill", q: "My mother ___ very kind.", answer: ["is"], tr: { he: "אמא שלי מאוד נחמדה.", ru: "Моя́ ма́ма о́чень до́брая." }, why: { he: "my mother = she, ולכן is.", ru: "My mother = she, поэтому is." } },
    { type: "fill", q: "We ___ not tired.", answer: ["are"], tr: { he: "אנחנו לא עייפים.", ru: "Мы не уста́ли." }, why: { he: "we → are, ו-not בא אחרי הפועל.", ru: "we → are, а not стоит после глагола." } },
    { type: "order", answer: "Are you a teacher?", tr: { he: "את מורה?", ru: "Вы учи́тель?" } },
    { type: "order", answer: "I am not hungry.", tr: { he: "אני לא רעבה.", ru: "Я не голодна́." } },
    { type: "fix", q: "He happy today.", answer: ["He is happy today.", "He's happy today."], tr: { he: "הוא שמח היום.", ru: "Он сего́дня сча́стлив." }, why: { he: "באנגלית חייבים פועל: He is happy.", ru: "В английском нужен глагол: He is happy." } },
    { type: "fix", q: "You is my friend.", answer: ["You are my friend.", "You're my friend."], tr: { he: "אתה החבר שלי.", ru: "Ты мой друг." }, why: { he: "עם you תמיד are.", ru: "С you всегда are." } },
    { type: "choice", q: "___ they from Israel?", options: ["Is", "Are", "Am"], answer: 1, tr: { he: "הם מישראל?", ru: "Они́ из Изра́иля?" }, why: { he: "they → are, ובשאלה הפועל בא ראשון.", ru: "they → are, а в вопросе глагол идёт первым." } }
  ]
});

LS_DATA.grammar.push({
  id: "en_articles", target: "en", level: 1, order: 2,
  title: { he: "a / an / the", ru: "Артикли a / an / the", en: "Articles: a / an / the" },
  explain: {
    he: "<p>בעברית יש רק ה- (ה«ידיעה»), ובשם עצם רגיל לא שמים כלום: «יש לי חתול». באנגלית לפני שם עצם ביחיד <b>כמעט תמיד</b> צריך מילה קטנה:</p><ul><li><b>a</b> = «סתם אחד», משהו לא מסוים, או כשמזכירים אותו בפעם הראשונה: I have <b>a</b> cat.</li><li><b>an</b> = אותו דבר, אבל לפני צליל של תנועה (a, e, i, o, u): <b>an</b> apple, <b>an</b> hour.</li><li><b>the</b> = כמו ה- בעברית: משהו מסוים שכבר ידוע: <b>The</b> cat is black.</li></ul><p><b>שימו לב:</b> עם מקצוע באנגלית שמים a: She is <b>a</b> teacher (בעברית פשוט «היא מורה»).</p><p>ברבים אין a: I have cats. אבל the אפשר: The cats are black.</p><p>דברים שיש רק אחד מהם – the sun, the sea.</p>",
    ru: "<p>В русском языке артиклей <b>нет совсем</b>: «У меня есть кошка. Кошка чёрная». В английском перед существительным в единственном числе <b>почти всегда</b> нужно маленькое слово:</p><ul><li><b>a</b> = «какой-то, один», когда говорим о чём-то впервые или не конкретно: I have <b>a</b> cat.</li><li><b>an</b> = то же самое, но перед гласным звуком (a, e, i, o, u): <b>an</b> apple, <b>an</b> hour.</li><li><b>the</b> = «тот самый», конкретный, уже известный: <b>The</b> cat is black.</li></ul><p><b>Внимание:</b> с профессией нужен a: She is <b>a</b> teacher (по-русски просто «Она учительница»).</p><p>Во множественном числе a не ставим: I have cats. А the можно: The cats are black.</p><p>То, что существует в одном экземпляре, – с the: the sun, the sea.</p><p>Подсказка: где по-русски можно сказать «какой-то» – там a; где «этот самый» – там the.</p>"
  },
  examples: [
    { t: "I have a cat.", he: "יש לי חתול.", ru: "У меня́ есть ко́шка." },
    { t: "The cat is black.", he: "החתול שחור.", ru: "Ко́шка чёрная." },
    { t: "She is a nurse.", he: "היא אחות.", ru: "Она́ медсестра́." },
    { t: "I eat an apple every day.", he: "אני אוכלת תפוח כל יום.", ru: "Я ем я́блоко ка́ждый день." },
    { t: "Close the door, please.", he: "תסגור את הדלת, בבקשה.", ru: "Закро́й дверь, пожа́луйста." },
    { t: "It is an old house.", he: "זה בית ישן.", ru: "Э́то ста́рый дом." }
  ],
  exercises: [
    { type: "choice", q: "I have ___ apple.", options: ["a", "an", "the"], answer: 1, tr: { he: "יש לי תפוח.", ru: "У меня́ есть я́блоко." }, why: { he: "apple מתחיל בתנועה, ולכן an.", ru: "apple начинается с гласной, поэтому an." } },
    { type: "choice", q: "He is ___ doctor.", options: ["a", "an", "—"], answer: 0, tr: { he: "הוא רופא.", ru: "Он врач." }, why: { he: "עם מקצוע באנגלית שמים a.", ru: "С профессией в английском нужен a." } },
    { type: "choice", q: "Please open ___ window.", options: ["a", "the", "an"], answer: 1, tr: { he: "בבקשה תפתח את החלון.", ru: "Откро́й, пожа́луйста, окно́." }, why: { he: "חלון מסוים שכולנו רואים – the.", ru: "Конкретное окно, которое мы видим, – the." } },
    { type: "fill", q: "I see ___ dog. The dog is big.", answer: ["a"], tr: { he: "אני רואה כלב. הכלב גדול.", ru: "Я ви́жу соба́ку. Соба́ка больша́я." }, why: { he: "בפעם הראשונה a, אחר כך the.", ru: "Первый раз – a, потом – the." } },
    { type: "fill", q: "She has ___ umbrella.", answer: ["an"], tr: { he: "יש לה מטרייה.", ru: "У неё есть зо́нтик." }, why: { he: "umbrella מתחיל בתנועה, ולכן an.", ru: "umbrella начинается с гласной, поэтому an." } },
    { type: "fill", q: "___ sun is hot.", answer: ["The", "the"], tr: { he: "השמש חמה.", ru: "Со́лнце горя́чее." }, why: { he: "יש רק שמש אחת, ולכן the.", ru: "Солнце одно, поэтому the." } },
    { type: "order", answer: "This is an old car.", tr: { he: "זאת מכונית ישנה.", ru: "Э́то ста́рая маши́на." } },
    { type: "order", answer: "The book is on the table.", tr: { he: "הספר על השולחן.", ru: "Кни́га на столе́." } },
    { type: "fix", q: "My sister is teacher.", answer: ["My sister is a teacher.", "My sister's a teacher."], tr: { he: "אחותי מורה.", ru: "Моя́ сестра́ – учи́тельница." }, why: { he: "לפני מקצוע צריך a.", ru: "Перед профессией нужен a." } },
    { type: "fix", q: "I want a orange.", answer: ["I want an orange."], tr: { he: "אני רוצה תפוז.", ru: "Я хочу́ апельси́н." }, why: { he: "orange מתחיל בתנועה, ולכן an.", ru: "orange начинается с гласной, поэтому an." } }
  ]
});

LS_DATA.grammar.push({
  id: "en_plurals", target: "en", level: 1, order: 3,
  title: { he: "רבים: book → books", ru: "Множественное число: book → books", en: "Plurals: book → books" },
  explain: {
    he: "<p>בעברית יש -ים ו-ות. באנגלית ברוב המקרים פשוט מוסיפים <b>-s</b>:</p><ul><li>book → book<b>s</b>, car → car<b>s</b></li><li>אחרי s, sh, ch, x מוסיפים <b>-es</b>: bus → bus<b>es</b>, box → box<b>es</b></li><li>עיצור + y → <b>-ies</b>: baby → bab<b>ies</b>, city → cit<b>ies</b></li></ul><p><b>מילים חריגות</b> שכדאי לזכור:</p><table><tr><td>man → men</td><td>woman → women</td></tr><tr><td>child → children</td><td>person → people</td></tr><tr><td>foot → feet</td><td>tooth → teeth</td></tr></table><p><b>שימו לב:</b> בעברית גם שם התואר משתנה (בתים גדול<b>ים</b>). באנגלית שם התואר <b>לא משתנה</b>: big houses (לא bigs).</p><p>אחרי כל מספר מ-2 ומעלה – תמיד רבים: two books, ten books.</p>",
    ru: "<p>В английском множественное число образуется проще, чем в русском. Обычно просто добавляем <b>-s</b>:</p><ul><li>book → book<b>s</b>, car → car<b>s</b></li><li>после s, sh, ch, x добавляем <b>-es</b>: bus → bus<b>es</b>, box → box<b>es</b></li><li>согласная + y → <b>-ies</b>: baby → bab<b>ies</b>, city → cit<b>ies</b></li></ul><p><b>Исключения</b>, которые надо запомнить:</p><table><tr><td>man → men</td><td>woman → women</td></tr><tr><td>child → children</td><td>person → people</td></tr><tr><td>foot → feet</td><td>tooth → teeth</td></tr></table><p><b>Внимание:</b> по-русски мы говорим «две книги», но «пять книг». В английском после любого числа от 2 и больше – просто множественное: two books, five books, twenty books.</p><p>Прилагательное в английском <b>не меняется</b>: big house – big houses (не bigs).</p>"
  },
  examples: [
    { t: "one book – two books", he: "ספר אחד – שני ספרים", ru: "одна́ кни́га – две кни́ги" },
    { t: "I have three children.", he: "יש לי שלושה ילדים.", ru: "У меня́ тро́е дете́й." },
    { t: "The boxes are heavy.", he: "הקופסאות כבדות.", ru: "Коро́бки тяжёлые." },
    { t: "Two women and five men.", he: "שתי נשים וחמישה גברים.", ru: "Две же́нщины и пять мужчи́н." },
    { t: "I like red apples.", he: "אני אוהבת תפוחים אדומים.", ru: "Я люблю́ кра́сные я́блоки." },
    { t: "Many people live here.", he: "הרבה אנשים גרים כאן.", ru: "Здесь живёт мно́го люде́й." }
  ],
  exercises: [
    { type: "choice", q: "I have two ___.", options: ["cat", "cats", "cates"], answer: 1, tr: { he: "יש לי שני חתולים.", ru: "У меня́ две ко́шки." }, why: { he: "אחרי two – רבים: cats.", ru: "После two – множественное: cats." } },
    { type: "choice", q: "She has two ___.", options: ["childs", "children", "childrens"], answer: 1, tr: { he: "יש לה שני ילדים.", ru: "У неё дво́е дете́й." }, why: { he: "child → children, זו מילה חריגה.", ru: "child → children, это исключение." } },
    { type: "choice", q: "The ___ are on the table.", options: ["boxs", "boxes", "box"], answer: 1, tr: { he: "הקופסאות על השולחן.", ru: "Коро́бки на столе́." }, why: { he: "אחרי x מוסיפים -es.", ru: "После x добавляем -es." } },
    { type: "fill", q: "one baby – two ___", answer: ["babies"], tr: { he: "תינוק אחד – שני תינוקות", ru: "оди́н малы́ш – два малыша́" }, why: { he: "עיצור + y הופך ל-ies.", ru: "Согласная + y превращается в -ies." } },
    { type: "fill", q: "one man – five ___", answer: ["men"], tr: { he: "גבר אחד – חמישה גברים", ru: "оди́н мужчи́на – пять мужчи́н" }, why: { he: "man → men, זו מילה חריגה.", ru: "man → men, это исключение." } },
    { type: "fill", q: "I brush my ___ every morning. (tooth)", answer: ["teeth"], tr: { he: "אני מצחצחת שיניים כל בוקר.", ru: "Я чи́щу зу́бы ка́ждое у́тро." }, why: { he: "tooth → teeth, זו מילה חריגה.", ru: "tooth → teeth, это исключение." } },
    { type: "order", answer: "I have two big dogs.", tr: { he: "יש לי שני כלבים גדולים.", ru: "У меня́ две больши́е соба́ки." } },
    { type: "order", answer: "The children are at school.", tr: { he: "הילדים בבית הספר.", ru: "Де́ти в шко́ле." } },
    { type: "fix", q: "I have three book.", answer: ["I have three books."], tr: { he: "יש לי שלושה ספרים.", ru: "У меня́ три кни́ги." }, why: { he: "אחרי three צריך רבים: books.", ru: "После three нужно множественное: books." } },
    { type: "fix", q: "They are bigs houses.", answer: ["They are big houses.", "They're big houses."], tr: { he: "אלה בתים גדולים.", ru: "Э́то больши́е дома́." }, why: { he: "שם התואר באנגלית לא מקבל -s.", ru: "Прилагательное в английском не получает -s." } }
  ]
});

LS_DATA.grammar.push({
  id: "en_this_that", target: "en", level: 1, order: 4,
  title: { he: "this / that / these / those", ru: "this / that / these / those", en: "This / that / these / those" },
  explain: {
    he: "<p>המילים האלה מראות <b>על מה</b> מדברים – קרוב או רחוק, אחד או הרבה:</p><table><tr><td></td><td><b>קרוב</b></td><td><b>רחוק</b></td></tr><tr><td>אחד</td><td><b>this</b> – זה / זאת</td><td><b>that</b> – ההוא / ההיא</td></tr><tr><td>הרבה</td><td><b>these</b> – אלה</td><td><b>those</b> – ההם</td></tr></table><ul><li><b>This</b> is my bag. – זה התיק שלי.</li><li><b>These</b> are my keys. – אלה המפתחות שלי.</li><li><b>That</b> house is old. – הבית ההוא ישן.</li></ul><p><b>שימו לב:</b> בעברית יש «זה» ו«זאת» לפי מין. באנגלית אין זכר ונקבה: this מתאים לשניהם.</p><p>אבל ברבים חייבים להחליף: this → these, that → those, וגם is → are: <b>These are</b> my children.</p><p>אפשר לשים את המילה לפני שם עצם: this book, those people.</p>",
    ru: "<p>Эти слова показывают, <b>о чём</b> мы говорим – близко или далеко, один предмет или много:</p><table><tr><td></td><td><b>близко</b></td><td><b>далеко</b></td></tr><tr><td>один</td><td><b>this</b> – этот, эта, это</td><td><b>that</b> – тот, та, то</td></tr><tr><td>много</td><td><b>these</b> – эти</td><td><b>those</b> – те</td></tr></table><ul><li><b>This</b> is my bag. – Это моя сумка.</li><li><b>These</b> are my keys. – Это мои ключи.</li><li><b>That</b> house is old. – Тот дом старый.</li></ul><p><b>Внимание:</b> по-русски мы говорим «Это моя сумка» и «Это мои ключи» – слово «это» не меняется. В английском оно <b>меняется</b>: для одного – this is, для многих – <b>these are</b>.</p><p>Рода в английском нет: this подходит и для «этот», и для «эта».</p><p>Слово можно поставить перед существительным: this book, those people.</p>"
  },
  examples: [
    { t: "This is my bag.", he: "זה התיק שלי.", ru: "Э́то моя́ су́мка." },
    { t: "That house is very old.", he: "הבית ההוא מאוד ישן.", ru: "Тот дом о́чень ста́рый." },
    { t: "These are my keys.", he: "אלה המפתחות שלי.", ru: "Э́то мои́ ключи́." },
    { t: "Those people are my neighbors.", he: "האנשים ההם הם השכנים שלי.", ru: "Те лю́ди – мои́ сосе́ди." },
    { t: "Is this your phone?", he: "זה הטלפון שלך?", ru: "Э́то твой телефо́н?" }
  ],
  exercises: [
    { type: "choice", q: "___ are my children.", options: ["This", "These", "That"], answer: 1, tr: { he: "אלה הילדים שלי.", ru: "Э́то мои́ де́ти." }, why: { he: "הרבה וקרוב – these.", ru: "Много и близко – these." } },
    { type: "choice", q: "Look at ___ bird in the sky!", options: ["this", "these", "that"], answer: 2, tr: { he: "תראה את הציפור ההיא בשמיים!", ru: "Посмотри́ на ту пти́цу в не́бе!" }, why: { he: "אחת ורחוקה – that.", ru: "Одна и далеко – that." } },
    { type: "choice", q: "___ shoes are too small for me.", options: ["This", "These", "That"], answer: 1, tr: { he: "הנעליים האלה קטנות לי מדי.", ru: "Э́ти ту́фли мне малы́." }, why: { he: "shoes זה רבים, ולכן these.", ru: "shoes – множественное число, поэтому these." } },
    { type: "fill", q: "___ is my husband, David.", answer: ["This"], tr: { he: "זה בעלי, דוד.", ru: "Э́то мой муж, Дави́д." }, why: { he: "מציגים אדם אחד שעומד לידנו – this.", ru: "Представляем одного человека рядом – this." } },
    { type: "fill", q: "Who are ___ men over there?", answer: ["those"], tr: { he: "מי האנשים ההם שם?", ru: "Кто те мужчи́ны вон там?" }, why: { he: "הרבה ורחוק – those.", ru: "Много и далеко – those." } },
    { type: "fill", q: "I like ___ dress. It is very nice.", answer: ["this", "that"], tr: { he: "אני אוהבת את השמלה הזאת. היא מאוד יפה.", ru: "Мне нра́вится э́то пла́тье. Оно́ о́чень краси́вое." }, why: { he: "שמלה אחת – this (קרוב) או that (רחוק).", ru: "Одно платье – this (близко) или that (далеко)." } },
    { type: "order", answer: "These apples are very sweet.", tr: { he: "התפוחים האלה מאוד מתוקים.", ru: "Э́ти я́блоки о́чень сла́дкие." } },
    { type: "order", answer: "Is that your car?", tr: { he: "זאת המכונית שלך?", ru: "Э́то твоя́ маши́на?" } },
    { type: "fix", q: "This are my friends.", answer: ["These are my friends."], tr: { he: "אלה החברים שלי.", ru: "Э́то мои́ друзья́." }, why: { he: "friends זה רבים: These are.", ru: "friends – это много: These are." } },
    { type: "fix", q: "Those book is interesting.", answer: ["That book is interesting."], tr: { he: "הספר ההוא מעניין.", ru: "Та кни́га интере́сная." }, why: { he: "ספר אחד – that, לא those.", ru: "Одна книга – that, а не those." } }
  ]
});

LS_DATA.grammar.push({
  id: "en_possessives", target: "en", level: 1, order: 5,
  title: { he: "שלי, שלך, של דוד: my / your / 's", ru: "Мой, твой, Давида: my / your / 's", en: "Possessives: my / your / 's" },
  explain: {
    he: "<p>בעברית אומרים «הספר שלי» – «שלי» בא <b>אחרי</b>. באנגלית המילה באה <b>לפני</b>, ובלי the: <b>my</b> book.</p><table><tr><td>I → <b>my</b> (שלי)</td><td>we → <b>our</b> (שלנו)</td></tr><tr><td>you → <b>your</b> (שלך / שלכם)</td><td>they → <b>their</b> (שלהם)</td></tr><tr><td>he → <b>his</b> (שלו)</td><td>she → <b>her</b> (שלה)</td></tr><tr><td>it → <b>its</b> (שלו / שלה, לחפץ או חיה)</td><td></td></tr></table><p><b>של + שם:</b> בעברית «המכונית של דוד». באנגלית הסדר הפוך: שם + <b>'s</b> + הדבר: <b>David's</b> car, my <b>mother's</b> house.</p><ul><li>Not: the car of David ✗</li><li>Not: the my book ✗</li></ul><p>טיפ: his ו-her תלויים <b>במי שהדבר שלו</b>: He loves <b>his</b> wife. She loves <b>her</b> husband.</p>",
    ru: "<p>Притяжательные слова в английском стоят перед существительным, как в русском: <b>my</b> book – моя книга. Но есть важные отличия.</p><table><tr><td>I → <b>my</b></td><td>we → <b>our</b></td></tr><tr><td>you → <b>your</b></td><td>they → <b>their</b></td></tr><tr><td>he → <b>his</b> (его)</td><td>she → <b>her</b> (её)</td></tr><tr><td>it → <b>its</b></td><td></td></tr></table><ul><li><b>Не меняются</b> по роду и числу: my book, my books, my son, my daughter (мой, моя, мои – всегда my).</li><li><b>Нет слова «свой»</b>! «Он любит свою жену» → He loves <b>his</b> wife. «Она любит своего мужа» → She loves <b>her</b> husband.</li></ul><p><b>Чей?</b> «Машина Давида» → <b>David's</b> car: сначала владелец + <b>'s</b>, потом вещь. Так же: my <b>mother's</b> house – дом моей мамы.</p><p>Не говорим: the car of David ✗.</p>"
  },
  examples: [
    { t: "My name is Anna.", he: "קוראים לי אנה.", ru: "Меня́ зову́т А́нна." },
    { t: "This is David's car.", he: "זאת המכונית של דוד.", ru: "Э́то маши́на Дави́да." },
    { t: "Her son lives in Haifa.", he: "הבן שלה גר בחיפה.", ru: "Её сын живёт в Ха́йфе." },
    { t: "Our house is small.", he: "הבית שלנו קטן.", ru: "Наш дом ма́ленький." },
    { t: "What is your phone number?", he: "מה מספר הטלפון שלך?", ru: "Како́й у тебя́ но́мер телефо́на?" },
    { t: "He loves his wife.", he: "הוא אוהב את אשתו.", ru: "Он лю́бит свою́ жену́." }
  ],
  exercises: [
    { type: "choice", q: "She loves ___ husband.", options: ["she", "her", "he"], answer: 1, tr: { he: "היא אוהבת את בעלה.", ru: "Она́ лю́бит своего́ му́жа." }, why: { he: "«שלה» באנגלית – her.", ru: "«Её / свой» для she – her." } },
    { type: "choice", q: "This is ___ bag.", options: ["Maria", "Marias", "Maria's"], answer: 2, tr: { he: "זה התיק של מריה.", ru: "Э́то су́мка Мари́и." }, why: { he: "«של מריה» – Maria's.", ru: "«Марии» – Maria's." } },
    { type: "choice", q: "We love ___ new apartment.", options: ["our", "us", "we"], answer: 0, tr: { he: "אנחנו אוהבים את הדירה החדשה שלנו.", ru: "Мы лю́бим на́шу но́вую кварти́ру." }, why: { he: "«שלנו» – our.", ru: "«Наш» – our." } },
    { type: "fill", q: "Tom has a sister. ___ sister is a cook.", answer: ["His"], tr: { he: "לטום יש אחות. אחותו טבחית.", ru: "У То́ма есть сестра́. Его́ сестра́ – по́вар." }, why: { he: "של טום (he) – his.", ru: "Тома (he) – his." } },
    { type: "fill", q: "The children are in ___ room.", answer: ["their"], tr: { he: "הילדים בחדר שלהם.", ru: "Де́ти в свое́й ко́мнате." }, why: { he: "של הילדים (they) – their.", ru: "Детей (they) – their." } },
    { type: "fill", q: "This is my ___ car. (husband)", answer: ["husband's"], tr: { he: "זאת המכונית של בעלי.", ru: "Э́то маши́на моего́ му́жа." }, why: { he: "«של בעלי» – my husband's.", ru: "«Моего мужа» – my husband's." } },
    { type: "order", answer: "My daughter's name is Dana.", tr: { he: "לבת שלי קוראים דנה.", ru: "Мою́ дочь зову́т Да́на." } },
    { type: "order", answer: "Is this your coat?", tr: { he: "זה המעיל שלך?", ru: "Э́то твоё пальто́?" } },
    { type: "fix", q: "This is the car of my brother.", answer: ["This is my brother's car."], tr: { he: "זאת המכונית של אחי.", ru: "Э́то маши́на моего́ бра́та." }, why: { he: "באנגלית אומרים my brother's car.", ru: "По-английски говорят my brother's car." } },
    { type: "fix", q: "He loves her wife.", answer: ["He loves his wife."], tr: { he: "הוא אוהב את אשתו.", ru: "Он лю́бит свою́ жену́." }, why: { he: "האישה שלו (he) – his wife.", ru: "Жена его (he) – his wife." } }
  ]
});

LS_DATA.grammar.push({
  id: "en_there_is", target: "en", level: 1, order: 6,
  title: { he: "יש / אין: there is / there are", ru: "Есть / нет: there is / there are", en: "There is / there are" },
  explain: {
    he: "<p>בעברית «יש» מתאים להכול. באנגלית יש <b>שני</b> מקרים שונים:</p><ul><li><b>יש לי</b> (בעלות) → <b>I have</b>: I have a dog. – יש לי כלב.</li><li><b>יש</b> (משהו נמצא במקום) → <b>There is / There are</b>: There is a dog in the garden. – יש כלב בגינה.</li></ul><p><b>There is</b> – לדבר אחד (או לדבר שלא סופרים, כמו milk). <b>There are</b> – להרבה דברים.</p><p>הסדר: There is + <b>מה</b> + <b>איפה</b>: There is a bank near my house.</p><p><b>אין:</b> There isn't any milk. There aren't any chairs.</p><p><b>שאלה:</b> מחליפים מקום: <b>Is there</b> a pharmacy here? <b>Are there</b> any eggs?</p><p>בדיבור: There's = There is.</p><p>טעות נפוצה: «Have a bank here» ✗ – נכון: There is a bank here.</p>",
    ru: "<p>Когда мы говорим, что что-то <b>находится</b> где-то, по-русски мы начинаем с места: «В комнате (есть) стол». В английском начинаем с <b>There is / There are</b>, а место – в конце:</p><ul><li><b>There is</b> a table in the room. – В комнате стол.</li><li><b>There are</b> two chairs in the kitchen. – На кухне два стула.</li></ul><p><b>There is</b> – для одного предмета (или того, что не считают: milk, water). <b>There are</b> – для многих.</p><p><b>Отрицание:</b> There isn't any milk. – Молока нет. There aren't any chairs.</p><p><b>Вопрос:</b> меняем местами: <b>Is there</b> a pharmacy here? <b>Are there</b> any eggs?</p><p><b>Не путайте</b> с «У меня есть» – это <b>I have</b>: I have a car.</p><p>Ошибка: «In the room is a table» ✗ – правильно: There is a table in the room.</p>"
  },
  examples: [
    { t: "There is a bank near my house.", he: "יש בנק ליד הבית שלי.", ru: "Ря́дом с мои́м до́мом есть банк." },
    { t: "There are two chairs in the kitchen.", he: "יש שני כיסאות במטבח.", ru: "На ку́хне два сту́ла." },
    { t: "There isn't any milk.", he: "אין חלב.", ru: "Молока́ нет." },
    { t: "Is there a pharmacy here?", he: "יש פה בית מרקחת?", ru: "Здесь есть апте́ка?" },
    { t: "There are many people in the park.", he: "יש הרבה אנשים בפארק.", ru: "В па́рке мно́го люде́й." }
  ],
  exercises: [
    { type: "choice", q: "There ___ a cat on the sofa.", options: ["is", "are", "have"], answer: 0, tr: { he: "יש חתול על הספה.", ru: "На дива́не ко́шка." }, why: { he: "חתול אחד – there is.", ru: "Одна кошка – there is." } },
    { type: "choice", q: "There ___ three banks on this street.", options: ["is", "are", "has"], answer: 1, tr: { he: "יש שלושה בנקים ברחוב הזה.", ru: "На э́той у́лице три ба́нка." }, why: { he: "הרבה – there are.", ru: "Много – there are." } },
    { type: "choice", q: "___ a supermarket near here?", options: ["Is there", "There is", "Have"], answer: 0, tr: { he: "יש סופרמרקט קרוב לכאן?", ru: "Здесь ря́дом есть суперма́ркет?" }, why: { he: "בשאלה – Is there.", ru: "В вопросе – Is there." } },
    { type: "fill", q: "There ___ two beds in the room.", answer: ["are"], tr: { he: "יש שתי מיטות בחדר.", ru: "В ко́мнате две крова́ти." }, why: { he: "שתי מיטות – are.", ru: "Две кровати – are." } },
    { type: "fill", q: "There ___ not any bread.", answer: ["is"], tr: { he: "אין לחם.", ru: "Хле́ба нет." }, why: { he: "לחם לא סופרים, ולכן is.", ru: "Хлеб не считают, поэтому is." } },
    { type: "fill", q: "___ there any eggs in the fridge?", answer: ["Are", "are"], tr: { he: "יש ביצים במקרר?", ru: "В холоди́льнике есть я́йца?" }, why: { he: "eggs זה רבים, ובשאלה – Are there.", ru: "eggs – много, в вопросе – Are there." } },
    { type: "order", answer: "There is a big park here.", tr: { he: "יש כאן פארק גדול.", ru: "Здесь есть большо́й парк." } },
    { type: "order", answer: "Are there any good restaurants here?", tr: { he: "יש כאן מסעדות טובות?", ru: "Здесь есть хоро́шие рестора́ны?" } },
    { type: "fix", q: "Have a bus stop near my house.", answer: ["There is a bus stop near my house.", "There's a bus stop near my house."], tr: { he: "יש תחנת אוטובוס ליד הבית שלי.", ru: "Ря́дом с мои́м до́мом есть автобу́сная остано́вка." }, why: { he: "«יש» במקום (לא «יש לי») – There is.", ru: "«Есть» в месте (не «у меня есть») – There is." } },
    { type: "fix", q: "In the room is two windows.", answer: ["There are two windows in the room."], tr: { he: "בחדר יש שני חלונות.", ru: "В ко́мнате два окна́." }, why: { he: "מתחילים ב-There are, והמקום בסוף.", ru: "Начинаем с There are, а место – в конце." } }
  ]
});

LS_DATA.grammar.push({
  id: "en_present_simple", target: "en", level: 2, order: 7,
  title: { he: "הווה פשוט: I work / she works", ru: "Present Simple: I work / she works", en: "Present simple: I work / she works" },
  explain: {
    he: "<p><b>Present simple</b> מתאר הרגלים, עובדות ודברים שקורים באופן קבוע: I work every day. – אני עובדת כל יום.</p><p>בעברית הפועל משתנה הרבה (עובד, עובדת, עובדים). באנגלית הפועל <b>כמעט לא משתנה</b> – יש רק כלל אחד חשוב:</p><table><tr><td>I / you / we / they</td><td>work</td></tr><tr><td><b>he / she / it</b></td><td>work<b>s</b></td></tr></table><ul><li>אחרי s, sh, ch, x, o מוסיפים <b>-es</b>: watch → watch<b>es</b>, go → go<b>es</b>.</li><li>עיצור + y → <b>-ies</b>: study → stud<b>ies</b>.</li><li>have → <b>has</b>.</li></ul><p>זה ה-s שהכי קל לשכוח! כל פעם שהנושא הוא he, she, it, או שם של אדם אחד (my son, Anna) – לבדוק שיש s.</p><p>מילים שבאות עם present simple: always, usually, often, sometimes, never, every day.</p>",
    ru: "<p><b>Present Simple</b> – это привычки, факты и то, что происходит регулярно: I work every day. – Я работаю каждый день.</p><p>В русском глагол меняется по лицам: я работаю, ты работаешь, они работают. В английском глагол <b>почти не меняется</b> – есть только одно важное правило:</p><table><tr><td>I / you / we / they</td><td>work</td></tr><tr><td><b>he / she / it</b></td><td>work<b>s</b></td></tr></table><ul><li>После s, sh, ch, x, o добавляем <b>-es</b>: watch → watch<b>es</b>, go → go<b>es</b>.</li><li>Согласная + y → <b>-ies</b>: study → stud<b>ies</b>.</li><li>have → <b>has</b>.</li></ul><p>Это окончание -s забывают чаще всего! Если подлежащее – he, she, it или один человек (my son, Anna), проверьте, есть ли -s.</p><p>Слова-подсказки: always, usually, often, sometimes, never, every day.</p>"
  },
  examples: [
    { t: "I work in a hospital.", he: "אני עובדת בבית חולים.", ru: "Я рабо́таю в больни́це." },
    { t: "She works in a bank.", he: "היא עובדת בבנק.", ru: "Она́ рабо́тает в ба́нке." },
    { t: "My husband drinks coffee every morning.", he: "בעלי שותה קפה כל בוקר.", ru: "Мой муж пьёт ко́фе ка́ждое у́тро." },
    { t: "We live in Tel Aviv.", he: "אנחנו גרים בתל אביב.", ru: "Мы живём в Тель-Ави́ве." },
    { t: "He watches TV in the evening.", he: "הוא רואה טלוויזיה בערב.", ru: "Он смо́трит телеви́зор ве́чером." },
    { t: "The shop opens at nine.", he: "החנות נפתחת בתשע.", ru: "Магази́н открыва́ется в де́вять." }
  ],
  exercises: [
    { type: "choice", q: "She ___ English every day.", options: ["study", "studies", "studys"], answer: 1, tr: { he: "היא לומדת אנגלית כל יום.", ru: "Она́ у́чит англи́йский ка́ждый день." }, why: { he: "she + study → studies (y הופך ל-ies).", ru: "she + study → studies (y меняется на ies)." } },
    { type: "choice", q: "My parents ___ in Haifa.", options: ["live", "lives", "living"], answer: 0, tr: { he: "ההורים שלי גרים בחיפה.", ru: "Мои́ роди́тели живу́т в Ха́йфе." }, why: { he: "parents = they, ולכן בלי s.", ru: "parents = they, поэтому без -s." } },
    { type: "choice", q: "He ___ a big dog.", options: ["have", "has", "haves"], answer: 1, tr: { he: "יש לו כלב גדול.", ru: "У него́ больша́я соба́ка." }, why: { he: "he + have → has.", ru: "he + have → has." } },
    { type: "fill", q: "My son ___ to school by bus. (go)", answer: ["goes"], tr: { he: "הבן שלי נוסע לבית הספר באוטובוס.", ru: "Мой сын е́здит в шко́лу на авто́бусе." }, why: { he: "he + go → goes.", ru: "he + go → goes." } },
    { type: "fill", q: "I ___ tea in the morning. (drink)", answer: ["drink"], tr: { he: "אני שותה תה בבוקר.", ru: "Я пью чай у́тром." }, why: { he: "עם I – בלי s.", ru: "С I – без -s." } },
    { type: "fill", q: "The bus ___ here. (stop)", answer: ["stops"], tr: { he: "האוטובוס עוצר כאן.", ru: "Авто́бус остана́вливается здесь." }, why: { he: "the bus = it, ולכן stops.", ru: "the bus = it, поэтому stops." } },
    { type: "order", answer: "She always drinks green tea.", tr: { he: "היא תמיד שותה תה ירוק.", ru: "Она́ всегда́ пьёт зелёный чай." } },
    { type: "order", answer: "We usually eat dinner at seven.", tr: { he: "אנחנו בדרך כלל אוכלים ארוחת ערב בשבע.", ru: "Мы обы́чно у́жинаем в семь." } },
    { type: "fix", q: "He work in an office.", answer: ["He works in an office."], tr: { he: "הוא עובד במשרד.", ru: "Он рабо́тает в о́фисе." }, why: { he: "עם he מוסיפים s: works.", ru: "С he добавляем -s: works." } },
    { type: "fix", q: "My daughter watch TV every evening.", answer: ["My daughter watches TV every evening."], tr: { he: "הבת שלי רואה טלוויזיה כל ערב.", ru: "Моя́ дочь смо́трит телеви́зор ка́ждый ве́чер." }, why: { he: "she + watch → watches.", ru: "she + watch → watches." } }
  ]
});

LS_DATA.grammar.push({
  id: "en_do_does", target: "en", level: 2, order: 8,
  title: { he: "שאלה ושלילה: do / does", ru: "Вопрос и отрицание: do / does", en: "Questions and negatives: do / does" },
  explain: {
    he: "<p>בעברית שאלה היא רק עניין של טון: «את גרה פה?». באנגלית ב-present simple צריך <b>פועל עזר</b> בתחילת השאלה:</p><ul><li><b>Do</b> you live here? – את גרה פה?</li><li><b>Does</b> she work? – היא עובדת?</li></ul><p><b>שלילה:</b> בעברית פשוט «לא». באנגלית:</p><ul><li>I <b>don't</b> (do not) like coffee.</li><li>She <b>doesn't</b> (does not) like coffee.</li></ul><table><tr><td>I / you / we / they</td><td><b>do / don't</b></td></tr><tr><td>he / she / it</td><td><b>does / doesn't</b></td></tr></table><p><b>חשוב:</b> אחרי does / doesn't הפועל חוזר לצורה הרגילה, <b>בלי s</b>: Does she <b>work</b>? She doesn't <b>work</b>. (ה-s כבר «נמצא» ב-does.)</p><p>עם am / is / are לא משתמשים ב-do: <b>Are</b> you tired? (לא Do you are tired).</p><p>תשובה קצרה: Yes, I do. / No, he doesn't.</p>",
    ru: "<p>По-русски вопрос задаём только интонацией: «Ты живёшь здесь?». В английском в Present Simple нужен <b>вспомогательный глагол</b> в начале:</p><ul><li><b>Do</b> you live here? – Ты живёшь здесь?</li><li><b>Does</b> she work? – Она работает?</li></ul><p><b>Отрицание:</b> по-русски просто «не». В английском:</p><ul><li>I <b>don't</b> (do not) like coffee.</li><li>She <b>doesn't</b> (does not) like coffee.</li></ul><table><tr><td>I / you / we / they</td><td><b>do / don't</b></td></tr><tr><td>he / she / it</td><td><b>does / doesn't</b></td></tr></table><p><b>Важно:</b> после does / doesn't глагол <b>без -s</b>: Does she <b>work</b>? She doesn't <b>work</b>. (-s уже «ушло» в does.)</p><p>С am / is / are do не нужен: <b>Are</b> you tired? (не Do you are tired).</p><p>Короткий ответ: Yes, I do. / No, he doesn't.</p>"
  },
  examples: [
    { t: "Do you speak English?", he: "את מדברת אנגלית?", ru: "Вы говори́те по-англи́йски?" },
    { t: "Does your husband work?", he: "בעלך עובד?", ru: "Ваш муж рабо́тает?" },
    { t: "I don't eat meat.", he: "אני לא אוכלת בשר.", ru: "Я не ем мя́со." },
    { t: "She doesn't like coffee.", he: "היא לא אוהבת קפה.", ru: "Она́ не лю́бит ко́фе." },
    { t: "Do they live near you?", he: "הם גרים לידך?", ru: "Они́ живу́т ря́дом с ва́ми?" }
  ],
  exercises: [
    { type: "choice", q: "___ you like tea?", options: ["Do", "Does", "Are"], answer: 0, tr: { he: "את אוהבת תה?", ru: "Ты лю́бишь чай?" }, why: { he: "עם you – Do.", ru: "С you – Do." } },
    { type: "choice", q: "___ your son speak Russian?", options: ["Do", "Does", "Is"], answer: 1, tr: { he: "הבן שלך מדבר רוסית?", ru: "Твой сын говори́т по-ру́сски?" }, why: { he: "your son = he, ולכן Does.", ru: "your son = he, поэтому Does." } },
    { type: "choice", q: "She doesn't ___ in Jerusalem.", options: ["live", "lives", "living"], answer: 0, tr: { he: "היא לא גרה בירושלים.", ru: "Она́ не живёт в Иерусали́ме." }, why: { he: "אחרי doesn't הפועל בלי s.", ru: "После doesn't глагол без -s." } },
    { type: "fill", q: "I ___ not understand.", answer: ["do"], tr: { he: "אני לא מבינה.", ru: "Я не понима́ю." }, why: { he: "עם I – do not.", ru: "С I – do not." } },
    { type: "fill", q: "He ___ like fish.", answer: ["doesn't", "does not"], tr: { he: "הוא לא אוהב דגים.", ru: "Он не лю́бит ры́бу." }, why: { he: "שלילה עם he – doesn't.", ru: "Отрицание с he – doesn't." } },
    { type: "fill", q: "___ she work on Fridays?", answer: ["Does", "does"], tr: { he: "היא עובדת בימי שישי?", ru: "Она́ рабо́тает по пя́тницам?" }, why: { he: "שאלה עם she – Does.", ru: "Вопрос с she – Does." } },
    { type: "order", answer: "Do you have children?", tr: { he: "יש לך ילדים?", ru: "У вас есть де́ти?" } },
    { type: "order", answer: "My mother doesn't drive a car.", tr: { he: "אמא שלי לא נוהגת.", ru: "Моя́ ма́ма не во́дит маши́ну." } },
    { type: "fix", q: "You speak Hebrew?", answer: ["Do you speak Hebrew?"], tr: { he: "אתה מדבר עברית?", ru: "Ты говори́шь на иври́те?" }, why: { he: "שאלה באנגלית מתחילה ב-Do.", ru: "Вопрос в английском начинается с Do." } },
    { type: "fix", q: "She don't eat sugar.", answer: ["She doesn't eat sugar.", "She does not eat sugar."], tr: { he: "היא לא אוכלת סוכר.", ru: "Она́ не ест са́хар." }, why: { he: "עם she – doesn't.", ru: "С she – doesn't." } }
  ]
});

LS_DATA.grammar.push({
  id: "en_word_order", target: "en", level: 2, order: 9,
  title: { he: "סדר מילים ו-me / him / her", ru: "Порядок слов и me / him / her", en: "Word order and object pronouns" },
  explain: {
    he: "<p>בעברית ובמיוחד ברוסית אפשר להזיז מילים במשפט. באנגלית הסדר <b>קבוע</b>:</p><p><b>מי</b> (נושא) → <b>עושה</b> (פועל) → <b>את מה / את מי</b> (מושא) → איפה / מתי</p><ul><li>I love him. – אני אוהבת אותו.</li><li>My son drinks milk every morning.</li></ul><p>כשהאדם מקבל את הפעולה, משתמשים בצורה אחרת של הכינוי:</p><table><tr><td>I → <b>me</b> (אותי / לי)</td><td>we → <b>us</b> (אותנו / לנו)</td></tr><tr><td>you → <b>you</b></td><td>they → <b>them</b> (אותם / להם)</td></tr><tr><td>he → <b>him</b> (אותו / לו)</td><td>she → <b>her</b> (אותה / לה)</td></tr><tr><td>it → <b>it</b></td><td></td></tr></table><p>«אותו», «לו», «אליו» – כולם <b>him</b>: I see him, I give him a book, I call him.</p><p>לא אומרים «He helps I» ✗ – נכון: He helps <b>me</b>.</p>",
    ru: "<p>В русском порядок слов свободный: «Я его люблю», «Его я люблю», «Люблю я его». В английском порядок <b>строгий</b>:</p><p><b>Кто</b> (подлежащее) → <b>делает</b> (глагол) → <b>кого / что</b> (дополнение) → где / когда</p><ul><li>I love him. – Я его люблю.</li><li>My son drinks milk every morning.</li></ul><p>Местоимение после глагола меняет форму:</p><table><tr><td>I → <b>me</b> (меня, мне)</td><td>we → <b>us</b> (нас, нам)</td></tr><tr><td>you → <b>you</b></td><td>they → <b>them</b> (их, им)</td></tr><tr><td>he → <b>him</b> (его, ему)</td><td>she → <b>her</b> (её, ей)</td></tr><tr><td>it → <b>it</b></td><td></td></tr></table><p><b>Внимание:</b> «Мне нравится» – по-английски I like: здесь «я» – подлежащее, и оно стоит первым. «Ему нравится» – He likes.</p><p>Не говорим «He helps I» ✗ – правильно: He helps <b>me</b>.</p>"
  },
  examples: [
    { t: "I love him.", he: "אני אוהבת אותו.", ru: "Я его́ люблю́." },
    { t: "She calls me every day.", he: "היא מתקשרת אליי כל יום.", ru: "Она́ звони́т мне ка́ждый день." },
    { t: "I like this song.", he: "אני אוהבת את השיר הזה.", ru: "Мне нра́вится э́та пе́сня." },
    { t: "Please help us.", he: "בבקשה עזרו לנו.", ru: "Помоги́те нам, пожа́луйста." },
    { t: "We see them on Saturdays.", he: "אנחנו רואים אותם בשבתות.", ru: "Мы ви́дим их по суббо́там." },
    { t: "My son gives her flowers.", he: "הבן שלי נותן לה פרחים.", ru: "Мой сын да́рит ей цветы́." }
  ],
  exercises: [
    { type: "choice", q: "Please call ___ tomorrow.", options: ["I", "me", "my"], answer: 1, tr: { he: "בבקשה תתקשר אליי מחר.", ru: "Позвони́ мне за́втра, пожа́луйста." }, why: { he: "אחרי הפועל – me.", ru: "После глагола – me." } },
    { type: "choice", q: "I know ___. He is my neighbor.", options: ["he", "him", "his"], answer: 1, tr: { he: "אני מכירה אותו. הוא השכן שלי.", ru: "Я его́ зна́ю. Он мой сосе́д." }, why: { he: "«אותו» – him.", ru: "«Его» после глагола – him." } },
    { type: "choice", q: "Which sentence is correct?", options: ["I him love.", "I love him.", "Him I love."], answer: 1, tr: { he: "אני אוהבת אותו.", ru: "Я его́ люблю́." }, why: { he: "סדר קבוע: I + love + him.", ru: "Строгий порядок: I + love + him." } },
    { type: "fill", q: "Where are my keys? I don't see ___.", answer: ["them"], tr: { he: "איפה המפתחות שלי? אני לא רואה אותם.", ru: "Где мои́ ключи́? Я их не ви́жу." }, why: { he: "keys = they, ולכן them.", ru: "keys = they, поэтому them." } },
    { type: "fill", q: "Maria is nice. I like ___ very much.", answer: ["her"], tr: { he: "מריה נחמדה. אני מאוד אוהבת אותה.", ru: "Мари́я ми́лая. Она́ мне о́чень нра́вится." }, why: { he: "«אותה» – her.", ru: "«Её» после глагола – her." } },
    { type: "fill", q: "Our grandchildren visit ___ every week.", answer: ["us"], tr: { he: "הנכדים שלנו מבקרים אותנו כל שבוע.", ru: "Вну́ки навеща́ют нас ка́ждую неде́лю." }, why: { he: "«אותנו» – us.", ru: "«Нас» – us." } },
    { type: "order", answer: "I like this city very much.", tr: { he: "אני מאוד אוהבת את העיר הזאת.", ru: "Мне о́чень нра́вится э́тот го́род." } },
    { type: "order", answer: "She often helps her mother.", tr: { he: "היא עוזרת לאמא שלה לעיתים קרובות.", ru: "Она́ ча́сто помога́ет свое́й ма́ме." } },
    { type: "fix", q: "Him I see every day.", answer: ["I see him every day."], tr: { he: "אני רואה אותו כל יום.", ru: "Я ви́жу его́ ка́ждый день." }, why: { he: "קודם מי שעושה: I see him.", ru: "Сначала тот, кто делает: I see him." } },
    { type: "fix", q: "He gives I a book.", answer: ["He gives me a book."], tr: { he: "הוא נותן לי ספר.", ru: "Он даёт мне кни́гу." }, why: { he: "אחרי הפועל – me, לא I.", ru: "После глагола – me, а не I." } }
  ]
});

LS_DATA.grammar.push({
  id: "en_in_on_at", target: "en", level: 2, order: 10,
  title: { he: "מילות יחס: in / on / at", ru: "Предлоги: in / on / at", en: "Prepositions: in / on / at" },
  explain: {
    he: "<p>בעברית אומרים «ב-» כמעט לכל דבר: בשעה חמש, ביום שני, ביולי, בבית. באנגלית יש <b>שלוש</b> מילים שונות.</p><p><b>זמן:</b></p><table><tr><td><b>at</b></td><td>שעה מדויקת</td><td>at 5 o'clock, at night</td></tr><tr><td><b>on</b></td><td>יום ותאריך</td><td>on Monday, on May 5</td></tr><tr><td><b>in</b></td><td>חודש, שנה, עונה, חלק מהיום</td><td>in July, in 2024, in summer, in the morning</td></tr></table><p><b>מקום:</b></p><ul><li><b>in</b> = בתוך: in the box, in the kitchen, in Israel</li><li><b>on</b> = על משטח: on the table, on the wall</li><li><b>at</b> = בנקודה / במקום שבו עושים משהו: at home, at work, at school, at the bus stop</li></ul><p>טיפ: מהקטן לגדול – <b>at</b> (שעה) → <b>on</b> (יום) → <b>in</b> (חודש, שנה).</p>",
    ru: "<p>По-русски мы говорим «в»: в пять часов, в понедельник, в июле. В английском здесь <b>три разных</b> предлога.</p><p><b>Время:</b></p><table><tr><td><b>at</b></td><td>точное время</td><td>at 5 o'clock, at night</td></tr><tr><td><b>on</b></td><td>день, дата</td><td>on Monday, on May 5</td></tr><tr><td><b>in</b></td><td>месяц, год, сезон, часть дня</td><td>in July, in 2024, in summer, in the morning</td></tr></table><p><b>Место:</b></p><ul><li><b>in</b> = внутри: in the box, in the kitchen, in Israel</li><li><b>on</b> = на поверхности: on the table, on the wall</li><li><b>at</b> = в точке, там, где чем-то занимаются: at home (дома), at work (на работе), at school, at the bus stop</li></ul><p><b>Внимание:</b> русское «на» не всегда on: «на работе» – at work, «на кухне» – in the kitchen.</p><p>Совет: от маленького к большому – <b>at</b> (час) → <b>on</b> (день) → <b>in</b> (месяц, год).</p>"
  },
  examples: [
    { t: "The meeting is at 10 o'clock.", he: "הפגישה בשעה עשר.", ru: "Встре́ча в де́сять часо́в." },
    { t: "I see my mother on Fridays.", he: "אני רואה את אמא שלי בימי שישי.", ru: "Я ви́жу ма́му по пя́тницам." },
    { t: "My birthday is in May.", he: "יום ההולדת שלי במאי.", ru: "Мой день рожде́ния в ма́е." },
    { t: "The keys are on the table.", he: "המפתחות על השולחן.", ru: "Ключи́ на столе́." },
    { t: "She is at work now.", he: "היא בעבודה עכשיו.", ru: "Она́ сейча́с на рабо́те." },
    { t: "We live in Israel.", he: "אנחנו גרים בישראל.", ru: "Мы живём в Изра́иле." }
  ],
  exercises: [
    { type: "choice", q: "The movie starts ___ 8 o'clock.", options: ["in", "on", "at"], answer: 2, tr: { he: "הסרט מתחיל בשמונה.", ru: "Фильм начина́ется в во́семь." }, why: { he: "שעה מדויקת – at.", ru: "Точное время – at." } },
    { type: "choice", q: "I have a doctor's appointment ___ Monday.", options: ["in", "on", "at"], answer: 1, tr: { he: "יש לי תור לרופא ביום שני.", ru: "У меня́ приём у врача́ в понеде́льник." }, why: { he: "יום בשבוע – on.", ru: "День недели – on." } },
    { type: "choice", q: "It is very hot here ___ August.", options: ["in", "on", "at"], answer: 0, tr: { he: "חם מאוד כאן באוגוסט.", ru: "Здесь о́чень жа́рко в а́вгусте." }, why: { he: "חודש – in.", ru: "Месяц – in." } },
    { type: "fill", q: "The milk is ___ the fridge.", answer: ["in"], tr: { he: "החלב במקרר.", ru: "Молоко́ в холоди́льнике." }, why: { he: "בתוך – in.", ru: "Внутри – in." } },
    { type: "fill", q: "There is a picture ___ the wall.", answer: ["on"], tr: { he: "יש תמונה על הקיר.", ru: "На стене́ виси́т карти́на." }, why: { he: "על משטח – on.", ru: "На поверхности – on." } },
    { type: "fill", q: "I am ___ home tonight.", answer: ["at"], tr: { he: "אני בבית הערב.", ru: "Сего́дня ве́чером я до́ма." }, why: { he: "«בבית» תמיד at home.", ru: "«Дома» – всегда at home." } },
    { type: "order", answer: "We go to the beach in summer.", tr: { he: "אנחנו הולכים לים בקיץ.", ru: "Ле́том мы хо́дим на пляж." } },
    { type: "order", answer: "The children are at school now.", tr: { he: "הילדים בבית הספר עכשיו.", ru: "Де́ти сейча́с в шко́ле." } },
    { type: "fix", q: "I wake up in 7 o'clock.", answer: ["I wake up at 7 o'clock.", "I wake up at seven o'clock."], tr: { he: "אני מתעוררת בשבע.", ru: "Я просыпа́юсь в семь часо́в." }, why: { he: "שעה – at.", ru: "Время по часам – at." } },
    { type: "fix", q: "See you in Sunday!", answer: ["See you on Sunday!", "See you on Sunday."], tr: { he: "נתראה ביום ראשון!", ru: "Уви́димся в воскресе́нье!" }, why: { he: "יום – on.", ru: "День – on." } }
  ]
});

LS_DATA.grammar.push({
  id: "en_present_continuous", target: "en", level: 2, order: 11,
  title: { he: "עכשיו או תמיד? I work / I am working", ru: "Сейчас или всегда? I work / I am working", en: "Present continuous vs. present simple" },
  explain: {
    he: "<p>בעברית יש רק הווה אחד: «אני מבשלת» – גם «עכשיו» וגם «בדרך כלל». באנגלית יש <b>שני</b> זמנים:</p><ul><li><b>Present simple</b> – הרגל, דבר קבוע: I cook every day. – אני מבשלת כל יום.</li><li><b>Present continuous</b> – קורה <b>עכשיו</b>, ממש ברגע זה: I <b>am cooking</b> now. – אני מבשלת עכשיו.</li></ul><p><b>איך בונים:</b> am / is / are + פועל עם <b>-ing</b></p><table><tr><td>I</td><td><b>am</b> working</td></tr><tr><td>he / she / it</td><td><b>is</b> working</td></tr><tr><td>you / we / they</td><td><b>are</b> working</td></tr></table><p>אל תשכחו את am / is / are! «I cooking» ✗</p><p>מילים של «עכשיו»: now, right now, at the moment, Look!, Listen!</p><p>יש פעלים שכמעט אף פעם לא באים עם -ing: like, love, want, know, understand. אומרים I <b>want</b> tea (לא I am wanting).</p>",
    ru: "<p>В русском одно настоящее время: «я готовлю» – и сейчас, и обычно. В английском их <b>два</b>:</p><ul><li><b>Present Simple</b> – привычка, регулярно: I cook every day. – Я готовлю каждый день.</li><li><b>Present Continuous</b> – происходит <b>прямо сейчас</b>: I <b>am cooking</b> now. – Я сейчас готовлю.</li></ul><p><b>Как строим:</b> am / is / are + глагол с <b>-ing</b></p><table><tr><td>I</td><td><b>am</b> working</td></tr><tr><td>he / she / it</td><td><b>is</b> working</td></tr><tr><td>you / we / they</td><td><b>are</b> working</td></tr></table><p>Не забывайте am / is / are! «I cooking» ✗</p><p>Слова-подсказки «сейчас»: now, right now, at the moment, Look!, Listen!</p><p>Некоторые глаголы почти никогда не бывают с -ing: like, love, want, know, understand. Говорим I <b>want</b> tea (не I am wanting).</p>"
  },
  examples: [
    { t: "I am cooking dinner now.", he: "אני מבשלת ארוחת ערב עכשיו.", ru: "Я сейча́с гото́влю у́жин." },
    { t: "She is talking on the phone.", he: "היא מדברת בטלפון.", ru: "Она́ говори́т по телефо́ну." },
    { t: "It is raining.", he: "יורד גשם.", ru: "Идёт дождь." },
    { t: "I usually walk, but today I am taking a taxi.", he: "בדרך כלל אני הולכת ברגל, אבל היום אני לוקחת מונית.", ru: "Обы́чно я хожу́ пешко́м, но сего́дня я е́ду на такси́." },
    { t: "What are you doing?", he: "מה את עושה?", ru: "Что ты де́лаешь?" },
    { t: "I know the answer.", he: "אני יודעת את התשובה.", ru: "Я зна́ю отве́т." }
  ],
  exercises: [
    { type: "choice", q: "Look! The baby ___.", options: ["sleeps", "is sleeping", "sleep"], answer: 1, tr: { he: "תראה! התינוק ישן.", ru: "Смотри́! Малы́ш спит." }, why: { he: "Look! – קורה עכשיו, ולכן is sleeping.", ru: "Look! – это сейчас, поэтому is sleeping." } },
    { type: "choice", q: "I ___ to work every day.", options: ["go", "am going", "goes"], answer: 0, tr: { he: "אני הולכת לעבודה כל יום.", ru: "Я хожу́ на рабо́ту ка́ждый день." }, why: { he: "every day = הרגל, ולכן present simple.", ru: "every day = привычка, поэтому Present Simple." } },
    { type: "choice", q: "I ___ a new car.", options: ["want", "am wanting", "wants"], answer: 0, tr: { he: "אני רוצה מכונית חדשה.", ru: "Я хочу́ но́вую маши́ну." }, why: { he: "want לא בא עם -ing.", ru: "want не используют с -ing." } },
    { type: "fill", q: "We ___ watching a movie right now.", answer: ["are"], tr: { he: "אנחנו רואים סרט עכשיו.", ru: "Мы сейча́с смо́трим фильм." }, why: { he: "עם we – are + ing.", ru: "С we – are + -ing." } },
    { type: "fill", q: "She is ___ a book at the moment. (read)", answer: ["reading"], tr: { he: "היא קוראת ספר כרגע.", ru: "Она́ сейча́с чита́ет кни́гу." }, why: { he: "is + פועל עם -ing.", ru: "is + глагол с -ing." } },
    { type: "fill", q: "My husband ___ every Saturday. (cook)", answer: ["cooks"], tr: { he: "בעלי מבשל כל שבת.", ru: "Мой муж гото́вит ка́ждую суббо́ту." }, why: { he: "כל שבת = הרגל; he → cooks.", ru: "Каждую субботу = привычка; he → cooks." } },
    { type: "order", answer: "What are you doing now?", tr: { he: "מה את עושה עכשיו?", ru: "Что ты сейча́с де́лаешь?" } },
    { type: "order", answer: "The children are playing outside.", tr: { he: "הילדים משחקים בחוץ.", ru: "Де́ти игра́ют на у́лице." } },
    { type: "fix", q: "I cooking now.", answer: ["I am cooking now.", "I'm cooking now."], tr: { he: "אני מבשלת עכשיו.", ru: "Я сейча́с гото́влю." }, why: { he: "חסר am: I am cooking.", ru: "Не хватает am: I am cooking." } },
    { type: "fix", q: "Listen! She sing.", answer: ["Listen! She is singing.", "Listen! She's singing."], tr: { he: "תקשיב! היא שרה.", ru: "Послу́шай! Она́ поёт." }, why: { he: "קורה עכשיו – is singing.", ru: "Это сейчас – is singing." } }
  ]
});

LS_DATA.grammar.push({
  id: "en_can_must", target: "en", level: 2, order: 12,
  title: { he: "יכול וחייב: can / must", ru: "Могу и должен: can / must", en: "Can and must" },
  explain: {
    he: "<ul><li><b>can</b> = יכול / יודע ל-: I <b>can</b> swim. – אני יודעת לשחות.</li><li><b>can't</b> (cannot) = לא יכול: I <b>can't</b> come. – אני לא יכולה לבוא.</li><li><b>must</b> = חייב: You <b>must</b> stop. – אתה חייב לעצור.</li><li><b>mustn't</b> = אסור: You <b>mustn't</b> smoke here. – אסור לעשן כאן.</li></ul><p><b>שלושה כללים פשוטים:</b></p><ul><li>can ו-must <b>לא משתנים</b>: I can, she can (לא cans), he must (לא musts).</li><li>אחריהם הפועל בצורה הבסיסית <b>בלי to</b>: I can <b>swim</b>. בעברית אומרים «יכולה <b>ל</b>שחות» – באנגלית אין «ל»: I can to swim ✗.</li><li>שאלה – בלי do: <b>Can</b> you help me? (לא Do you can).</li></ul><p>מילה שימושית: <b>Can I…?</b> = אפשר…? – Can I pay by card? – אפשר לשלם בכרטיס?</p>",
    ru: "<ul><li><b>can</b> = могу, умею: I <b>can</b> swim. – Я умею плавать.</li><li><b>can't</b> (cannot) = не могу: I <b>can't</b> come. – Я не могу прийти.</li><li><b>must</b> = должен, нужно: You <b>must</b> stop. – Ты должен остановиться.</li><li><b>mustn't</b> = нельзя: You <b>mustn't</b> smoke here. – Здесь нельзя курить.</li></ul><p><b>Три простых правила:</b></p><ul><li>can и must <b>не меняются</b>: I can, she can (не cans), he must (не musts). А в русском: могу, может, должен, должна…</li><li>После них глагол в простой форме <b>без to</b>: I can <b>swim</b>. Нельзя: I can to swim ✗.</li><li>Вопрос – без do: <b>Can</b> you help me? (не Do you can).</li></ul><p>Полезная фраза: <b>Can I…?</b> = Можно…? – Can I pay by card? – Можно оплатить картой?</p>"
  },
  examples: [
    { t: "I can swim.", he: "אני יודעת לשחות.", ru: "Я уме́ю пла́вать." },
    { t: "She can't come today.", he: "היא לא יכולה לבוא היום.", ru: "Она́ не мо́жет прийти́ сего́дня." },
    { t: "Can you help me, please?", he: "אתה יכול לעזור לי, בבקשה?", ru: "Вы мо́жете мне помо́чь, пожа́луйста?" },
    { t: "You must wear a seat belt.", he: "חייבים לחגור חגורת בטיחות.", ru: "Ну́жно пристегну́ть реме́нь безопа́сности." },
    { t: "We mustn't be late.", he: "אסור לנו לאחר.", ru: "Нам нельзя́ опа́здывать." }
  ],
  exercises: [
    { type: "choice", q: "She ___ speak three languages.", options: ["can", "cans", "can to"], answer: 0, tr: { he: "היא יודעת לדבר שלוש שפות.", ru: "Она́ уме́ет говори́ть на трёх языка́х." }, why: { he: "can לא משתנה, ובלי to.", ru: "can не меняется, и без to." } },
    { type: "choice", q: "You ___ smoke here. It is a hospital.", options: ["must", "mustn't", "can"], answer: 1, tr: { he: "אסור לעשן כאן. זה בית חולים.", ru: "Здесь нельзя́ кури́ть. Э́то больни́ца." }, why: { he: "«אסור» – mustn't.", ru: "«Нельзя» – mustn't." } },
    { type: "choice", q: "___ you drive?", options: ["Do can", "Can", "Are can"], answer: 1, tr: { he: "אתה יודע לנהוג?", ru: "Ты уме́ешь води́ть?" }, why: { he: "שאלה: Can + you, בלי do.", ru: "Вопрос: Can + you, без do." } },
    { type: "fill", q: "I ___ find my glasses. Help me, please!", answer: ["can't", "cannot", "can not"], tr: { he: "אני לא מוצאת את המשקפיים שלי. תעזור לי, בבקשה!", ru: "Я не могу́ найти́ очки́. Помоги́ мне, пожа́луйста!" }, why: { he: "«לא יכולה» – can't.", ru: "«Не могу» – can't." } },
    { type: "fill", q: "You ___ take this medicine every day.", answer: ["must"], tr: { he: "אתה חייב לקחת את התרופה הזאת כל יום.", ru: "Ты до́лжен принима́ть э́то лека́рство ка́ждый день." }, why: { he: "«חייב» – must.", ru: "«Должен» – must." } },
    { type: "fill", q: "My grandson can ___ now. (read)", answer: ["read"], tr: { he: "הנכד שלי יודע לקרוא עכשיו.", ru: "Мой внук тепе́рь уме́ет чита́ть." }, why: { he: "אחרי can – הפועל כמו שהוא.", ru: "После can – глагол как есть." } },
    { type: "order", answer: "Can I pay by card?", tr: { he: "אפשר לשלם בכרטיס?", ru: "Мо́жно оплати́ть ка́ртой?" } },
    { type: "order", answer: "We must go home now.", tr: { he: "אנחנו חייבים ללכת הביתה עכשיו.", ru: "Нам ну́жно сейча́с идти́ домо́й." } },
    { type: "fix", q: "I can to cook very well.", answer: ["I can cook very well."], tr: { he: "אני יודעת לבשל טוב מאוד.", ru: "Я о́чень хорошо́ гото́влю." }, why: { he: "אחרי can אין to.", ru: "После can нет to." } },
    { type: "fix", q: "He musts work today.", answer: ["He must work today."], tr: { he: "הוא חייב לעבוד היום.", ru: "Он до́лжен сего́дня рабо́тать." }, why: { he: "must אף פעם לא מקבל s.", ru: "must никогда не получает -s." } }
  ]
});

LS_DATA.grammar.push({
  id: "en_wh_questions", target: "en", level: 3, order: 13,
  title: { he: "מילות שאלה: what, where, when…", ru: "Вопросительные слова: what, where, when…", en: "Wh-questions: what, where, when…" },
  explain: {
    he: "<table><tr><td><b>what</b> – מה</td><td><b>where</b> – איפה / לאן</td></tr><tr><td><b>when</b> – מתי</td><td><b>who</b> – מי</td></tr><tr><td><b>why</b> – למה</td><td><b>how</b> – איך</td></tr><tr><td><b>how much / how many</b> – כמה</td><td><b>which</b> – איזה</td></tr></table><p>בעברית שואלים בלי לשנות כלום: «איפה את גרה?». באנגלית צריך <b>סדר מיוחד</b>:</p><p><b>מילת שאלה + do / does + מי + פועל</b></p><ul><li><b>Where do</b> you live?</li><li><b>When does</b> the bank open?</li></ul><p>עם am / is / are – הפועל בא אחרי מילת השאלה:</p><ul><li><b>Where is</b> the station?</li><li><b>Why are</b> you sad?</li></ul><p>כמה: <b>how many</b> – לדברים שסופרים (how many children), <b>how much</b> – לדברים שלא סופרים ולמחיר (how much water, How much is it?).</p><p>זהירות: «Where you live?» ✗ – חסר do!</p>",
    ru: "<table><tr><td><b>what</b> – что</td><td><b>where</b> – где / куда</td></tr><tr><td><b>when</b> – когда</td><td><b>who</b> – кто</td></tr><tr><td><b>why</b> – почему</td><td><b>how</b> – как</td></tr><tr><td><b>how much / how many</b> – сколько</td><td><b>which</b> – который, какой</td></tr></table><p>По-русски мы просто ставим вопросительное слово: «Где ты живёшь?». В английском нужен <b>особый порядок</b>:</p><p><b>Вопросительное слово + do / does + кто + глагол</b></p><ul><li><b>Where do</b> you live?</li><li><b>When does</b> the bank open?</li></ul><p>С am / is / are глагол идёт сразу после вопросительного слова:</p><ul><li><b>Where is</b> the station?</li><li><b>Why are</b> you sad?</li></ul><p>«Сколько»: <b>how many</b> – для того, что можно посчитать (how many children), <b>how much</b> – для того, что не считают, и для цены (how much water, How much is it?).</p><p>Осторожно: «Where you live?» ✗ – не хватает do!</p>"
  },
  examples: [
    { t: "Where do you live?", he: "איפה את גרה?", ru: "Где ты живёшь?" },
    { t: "What is your name?", he: "איך קוראים לך?", ru: "Как тебя́ зову́т?" },
    { t: "When does the bank open?", he: "מתי הבנק נפתח?", ru: "Когда́ открыва́ется банк?" },
    { t: "Why are you sad?", he: "למה את עצובה?", ru: "Почему́ ты гру́стная?" },
    { t: "How much is this?", he: "כמה זה עולה?", ru: "Ско́лько э́то сто́ит?" },
    { t: "Who is that woman?", he: "מי האישה ההיא?", ru: "Кто та же́нщина?" }
  ],
  exercises: [
    { type: "choice", q: "___ do you live? – In Haifa.", options: ["What", "Where", "When"], answer: 1, tr: { he: "איפה את גרה? – בחיפה.", ru: "Где ты живёшь? – В Ха́йфе." }, why: { he: "שואלים על מקום – where.", ru: "Спрашиваем о месте – where." } },
    { type: "choice", q: "___ is your birthday? – In June.", options: ["When", "Who", "How"], answer: 0, tr: { he: "מתי יום ההולדת שלך? – ביוני.", ru: "Когда́ у тебя́ день рожде́ния? – В ию́не." }, why: { he: "שואלים על זמן – when.", ru: "Спрашиваем о времени – when." } },
    { type: "choice", q: "___ apples do you need?", options: ["How much", "How many", "What many"], answer: 1, tr: { he: "כמה תפוחים את צריכה?", ru: "Ско́лько я́блок тебе́ ну́жно?" }, why: { he: "תפוחים אפשר לספור – how many.", ru: "Яблоки можно посчитать – how many." } },
    { type: "fill", q: "What ___ you want for dinner?", answer: ["do"], tr: { he: "מה את רוצה לארוחת ערב?", ru: "Что ты хо́чешь на у́жин?" }, why: { he: "you + פועל רגיל – do.", ru: "you + обычный глагол – do." } },
    { type: "fill", q: "Where ___ your husband work?", answer: ["does"], tr: { he: "איפה בעלך עובד?", ru: "Где рабо́тает твой муж?" }, why: { he: "your husband = he, ולכן does.", ru: "your husband = he, поэтому does." } },
    { type: "fill", q: "___ are you tired? – Because I work a lot.", answer: ["Why", "why"], tr: { he: "למה את עייפה? – כי אני עובדת הרבה.", ru: "Почему́ ты уста́ла? – Потому́ что я мно́го рабо́таю." }, why: { he: "שואלים על סיבה – why.", ru: "Спрашиваем о причине – why." } },
    { type: "order", answer: "How old are your children?", tr: { he: "בני כמה הילדים שלך?", ru: "Ско́лько лет твои́м де́тям?" } },
    { type: "order", answer: "What time does the shop close?", tr: { he: "באיזו שעה החנות נסגרת?", ru: "Во ско́лько закрыва́ется магази́н?" } },
    { type: "fix", q: "Where you live?", answer: ["Where do you live?"], tr: { he: "איפה אתה גר?", ru: "Где ты живёшь?" }, why: { he: "חסר do: Where do you live?", ru: "Не хватает do: Where do you live?" } },
    { type: "fix", q: "What she is doing?", answer: ["What is she doing?", "What's she doing?"], tr: { he: "מה היא עושה?", ru: "Что она́ де́лает?" }, why: { he: "בשאלה is בא לפני she.", ru: "В вопросе is стоит перед she." } }
  ]
});

LS_DATA.grammar.push({
  id: "en_past_simple", target: "en", level: 3, order: 14,
  title: { he: "עבר פשוט: worked, went", ru: "Прошедшее время: worked, went", en: "Past simple: worked, went" },
  explain: {
    he: "<p>יש בשורה טובה: בעבר האנגלי הפועל <b>זהה לכולם</b>. בעברית: עבדתי, עבדה, עבדנו. באנגלית: I worked, she worked, we worked.</p><p><b>פעלים רגילים</b> – מוסיפים <b>-ed</b>:</p><ul><li>work → work<b>ed</b>, visit → visit<b>ed</b></li><li>live → live<b>d</b>, stop → stop<b>ped</b>, study → stud<b>ied</b></li></ul><p><b>פעלים חריגים</b> – צריך לזכור בעל פה:</p><table><tr><td>go → went</td><td>have → had</td><td>see → saw</td></tr><tr><td>eat → ate</td><td>buy → bought</td><td>come → came</td></tr><tr><td>make → made</td><td>get → got</td><td>take → took</td></tr></table><p>to be: I / he / she / it → <b>was</b>; you / we / they → <b>were</b>.</p><p><b>שלילה ושאלה</b> – עם <b>did</b>, והפועל חוזר לצורה הבסיסית:</p><ul><li>I <b>didn't go</b>. (לא didn't went)</li><li><b>Did</b> you <b>see</b> him? (לא Did you saw)</li></ul>",
    ru: "<p>Хорошая новость: в английском прошедшем времени глагол <b>одинаковый для всех</b>. По-русски: работал, работала, работали. По-английски: I worked, she worked, we worked.</p><p><b>Правильные глаголы</b> – добавляем <b>-ed</b>:</p><ul><li>work → work<b>ed</b>, visit → visit<b>ed</b></li><li>live → live<b>d</b>, stop → stop<b>ped</b>, study → stud<b>ied</b></li></ul><p><b>Неправильные глаголы</b> – нужно запомнить:</p><table><tr><td>go → went</td><td>have → had</td><td>see → saw</td></tr><tr><td>eat → ate</td><td>buy → bought</td><td>come → came</td></tr><tr><td>make → made</td><td>get → got</td><td>take → took</td></tr></table><p>to be: I / he / she / it → <b>was</b>; you / we / they → <b>were</b>.</p><p><b>Отрицание и вопрос</b> – с <b>did</b>, а глагол возвращается в простую форму:</p><ul><li>I <b>didn't go</b>. (не didn't went)</li><li><b>Did</b> you <b>see</b> him? (не Did you saw)</li></ul><p>Слова-подсказки: yesterday, last week, ago, in 2010.</p>"
  },
  examples: [
    { t: "I worked in a bank.", he: "עבדתי בבנק.", ru: "Я рабо́тала в ба́нке." },
    { t: "We went to Paris last year.", he: "נסענו לפריז בשנה שעברה.", ru: "В про́шлом году́ мы е́здили в Пари́ж." },
    { t: "She bought a new dress yesterday.", he: "אתמול היא קנתה שמלה חדשה.", ru: "Вчера́ она́ купи́ла но́вое пла́тье." },
    { t: "Did you eat breakfast?", he: "אכלת ארוחת בוקר?", ru: "Ты за́втракала?" },
    { t: "I didn't see him.", he: "לא ראיתי אותו.", ru: "Я его́ не ви́дела." },
    { t: "The weather was beautiful.", he: "מזג האוויר היה יפה.", ru: "Пого́да была́ прекра́сная." }
  ],
  exercises: [
    { type: "choice", q: "Yesterday I ___ my friend.", options: ["visit", "visited", "visits"], answer: 1, tr: { he: "אתמול ביקרתי את החברה שלי.", ru: "Вчера́ я навести́ла подру́гу." }, why: { he: "yesterday = עבר, ולכן -ed.", ru: "yesterday = прошлое, поэтому -ed." } },
    { type: "choice", q: "We ___ to the beach last Saturday.", options: ["go", "goed", "went"], answer: 2, tr: { he: "בשבת שעברה הלכנו לים.", ru: "В про́шлую суббо́ту мы ходи́ли на пляж." }, why: { he: "go → went, פועל חריג.", ru: "go → went, неправильный глагол." } },
    { type: "choice", q: "Did you ___ the news?", options: ["see", "saw", "seen"], answer: 0, tr: { he: "ראית את החדשות?", ru: "Ты ви́дел но́вости?" }, why: { he: "אחרי did – הצורה הבסיסית.", ru: "После did – простая форма." } },
    { type: "fill", q: "She ___ bread this morning. (buy)", answer: ["bought"], tr: { he: "היא קנתה לחם הבוקר.", ru: "Она́ купи́ла хлеб сего́дня у́тром." }, why: { he: "buy → bought, פועל חריג.", ru: "buy → bought, неправильный глагол." } },
    { type: "fill", q: "I ___ very tired yesterday. (be)", answer: ["was"], tr: { he: "אתמול הייתי מאוד עייפה.", ru: "Вчера́ я о́чень уста́ла." }, why: { he: "I בעבר – was.", ru: "I в прошлом – was." } },
    { type: "fill", q: "They ___ not come to the party.", answer: ["did"], tr: { he: "הם לא באו למסיבה.", ru: "Они́ не пришли́ на вечери́нку." }, why: { he: "שלילה בעבר: did not + פועל.", ru: "Отрицание в прошлом: did not + глагол." } },
    { type: "order", answer: "We had dinner at home.", tr: { he: "אכלנו ארוחת ערב בבית.", ru: "Мы у́жинали до́ма." } },
    { type: "order", answer: "Did you call your mother?", tr: { he: "התקשרת לאמא שלך?", ru: "Ты позвони́л ма́ме?" } },
    { type: "fix", q: "I goed to the doctor yesterday.", answer: ["I went to the doctor yesterday."], tr: { he: "אתמול הלכתי לרופא.", ru: "Вчера́ я ходи́ла к врачу́." }, why: { he: "go → went.", ru: "go → went." } },
    { type: "fix", q: "He didn't called me.", answer: ["He didn't call me.", "He did not call me."], tr: { he: "הוא לא התקשר אליי.", ru: "Он мне не позвони́л." }, why: { he: "אחרי didn't – הצורה הבסיסית.", ru: "После didn't – простая форма." } }
  ]
});

LS_DATA.grammar.push({
  id: "en_future", target: "en", level: 3, order: 15,
  title: { he: "עתיד: will / going to", ru: "Будущее: will / going to", en: "Future: will / going to" },
  explain: {
    he: "<p>בעברית יש עתיד אחד: «אעזור». באנגלית יש שתי דרכים עיקריות:</p><p><b>1. will + פועל</b> – החלטה של הרגע, הבטחה, ניחוש:</p><ul><li>It's cold. I <b>will close</b> the window. – קר. אני אסגור את החלון.</li><li>I'<b>ll call</b> you tomorrow. – אתקשר אלייך מחר.</li></ul><p>will לא משתנה (she will, they will), ואחריו פועל בלי to ובלי s. שלילה: <b>won't</b> (= will not).</p><p><b>2. am / is / are + going to + פועל</b> – תוכנית שכבר החלטנו עליה:</p><ul><li>I <b>am going to visit</b> my sister on Sunday. – ביום ראשון אני הולכת לבקר את אחותי.</li><li>Look at the clouds! It'<b>s going to rain</b>.</li></ul><p>נוח לזכור: בעברית גם אומרים «אני <b>הולכת</b> ל…» – בדיוק כמו going to!</p><p>הרבה פעמים שתי הצורות נכונות – אל תדאגו יותר מדי.</p>",
    ru: "<p>В русском будущее строится просто: «помогу», «буду помогать». В английском есть два главных способа:</p><p><b>1. will + глагол</b> – решение в момент речи, обещание, предположение:</p><ul><li>It's cold. I <b>will close</b> the window. – Холодно. Я закрою окно.</li><li>I'<b>ll call</b> you tomorrow. – Я позвоню тебе завтра.</li></ul><p>will не меняется (she will, they will), после него глагол без to и без -s. Отрицание: <b>won't</b> (= will not).</p><p><b>2. am / is / are + going to + глагол</b> – план, который уже решён: «собираюсь»:</p><ul><li>I <b>am going to visit</b> my sister on Sunday. – В воскресенье я собираюсь к сестре.</li><li>Look at the clouds! It'<b>s going to rain</b>. – Сейчас пойдёт дождь.</li></ul><p>Запомните: going to = «собираюсь». Часто подходят оба варианта – не переживайте.</p>"
  },
  examples: [
    { t: "I will call you tomorrow.", he: "אתקשר אלייך מחר.", ru: "Я позвоню́ тебе́ за́втра." },
    { t: "It's cold. I'll close the window.", he: "קר. אני אסגור את החלון.", ru: "Хо́лодно. Я закро́ю окно́." },
    { t: "We are going to visit my sister on Sunday.", he: "ביום ראשון אנחנו הולכים לבקר את אחותי.", ru: "В воскресе́нье мы пое́дем к мое́й сестре́." },
    { t: "She won't be late.", he: "היא לא תאחר.", ru: "Она́ не опозда́ет." },
    { t: "Look at the clouds! It's going to rain.", he: "תראי את העננים! עומד לרדת גשם.", ru: "Посмотри́ на облака́! Сейча́с пойдёт дождь." },
    { t: "Will you help me?", he: "תעזור לי?", ru: "Ты мне помо́жешь?" }
  ],
  exercises: [
    { type: "choice", q: "Tomorrow I ___ you.", options: ["call", "will call", "will calls"], answer: 1, tr: { he: "מחר אתקשר אליך.", ru: "За́втра я тебе́ позвоню́." }, why: { he: "עתיד: will + פועל.", ru: "Будущее: will + глагол." } },
    { type: "choice", q: "We ___ going to buy a new sofa.", options: ["is", "are", "will"], answer: 1, tr: { he: "אנחנו הולכים לקנות ספה חדשה.", ru: "Мы собира́емся купи́ть но́вый дива́н." }, why: { he: "עם we – are going to.", ru: "С we – are going to." } },
    { type: "choice", q: "Don't worry, I ___ tell anyone.", options: ["won't", "don't will", "willn't"], answer: 0, tr: { he: "אל תדאגי, אני לא אספר לאף אחד.", ru: "Не волну́йся, я никому́ не скажу́." }, why: { he: "will not = won't.", ru: "will not = won't." } },
    { type: "fill", q: "She ___ visit us next week.", answer: ["will", "is going to"], tr: { he: "היא תבקר אותנו בשבוע הבא.", ru: "Она́ навести́т нас на сле́дующей неде́ле." }, why: { he: "עתיד – will (או is going to).", ru: "Будущее – will (или is going to)." } },
    { type: "fill", q: "I am ___ to learn English this year.", answer: ["going"], tr: { he: "אני הולכת ללמוד אנגלית השנה.", ru: "В э́том году́ я собира́юсь учи́ть англи́йский." }, why: { he: "תוכנית – am going to.", ru: "План – am going to." } },
    { type: "fill", q: "Will you ___ me tomorrow? (help)", answer: ["help"], tr: { he: "תעזור לי מחר?", ru: "Ты помо́жешь мне за́втра?" }, why: { he: "אחרי will – הפועל כמו שהוא.", ru: "После will – глагол как есть." } },
    { type: "order", answer: "I will see you tomorrow.", tr: { he: "אראה אותך מחר.", ru: "Уви́димся за́втра." } },
    { type: "order", answer: "They are going to move to Haifa.", tr: { he: "הם עומדים לעבור לחיפה.", ru: "Они́ собира́ются перее́хать в Ха́йфу." } },
    { type: "fix", q: "I will to call you later.", answer: ["I will call you later.", "I'll call you later."], tr: { he: "אתקשר אליך אחר כך.", ru: "Я позвоню́ тебе́ по́зже." }, why: { he: "אחרי will אין to.", ru: "После will нет to." } },
    { type: "fix", q: "He will comes tomorrow.", answer: ["He will come tomorrow.", "He'll come tomorrow."], tr: { he: "הוא יבוא מחר.", ru: "Он придёт за́втра." }, why: { he: "אחרי will – בלי s.", ru: "После will – без -s." } }
  ]
});
