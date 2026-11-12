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
