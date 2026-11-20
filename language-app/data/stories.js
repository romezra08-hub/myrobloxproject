window.LS_DATA = window.LS_DATA || {};
LS_DATA.stories = LS_DATA.stories || [];

LS_DATA.stories.push({
  id: "s_coffee", level: 1, emoji: "☕",
  title: { en: "Morning Coffee", ru: "У́тренний ко́фе", he: "קפה של בוקר" },
  sentences: [
    { en: "Anna wakes up at seven.", ru: "А́нна просыпа́ется в семь.", he: "אנה מתעוררת בשבע.", emoji: "⏰" },
    { en: "She goes to the kitchen.", ru: "Она́ идёт на ку́хню.", he: "היא הולכת למטבח.", emoji: "🚶‍♀️" },
    { en: "She makes hot coffee.", ru: "Она́ ва́рит горя́чий ко́фе.", he: "היא מכינה קפה חם.", emoji: "☕" },
    { en: "The coffee smells very good.", ru: "Ко́фе о́чень вку́сно па́хнет.", he: "הקפה מריח טוב מאוד.", emoji: "👃" },
    { en: "The cat wants milk too.", ru: "Ко́шка то́же хо́чет молока́.", he: "גם החתולה רוצה חלב.", emoji: "🐱" },
    { en: "Anna gives the cat milk.", ru: "А́нна даёт ко́шке молоко́.", he: "אנה נותנת לחתולה חלב.", emoji: "🥛" },
    { en: "Now they are both happy.", ru: "Тепе́рь они́ о́бе счастли́вы.", he: "עכשיו שתיהן מאושרות.", emoji: "😊" }
  ],
  questions: [
    { q: { en: "When does Anna wake up?", ru: "Когда́ А́нна просыпа́ется?", he: "מתי אנה מתעוררת?" },
      options: [ { en: "At seven", ru: "В семь", he: "בשבע" }, { en: "At nine", ru: "В де́вять", he: "בתשע" }, { en: "At noon", ru: "В по́лдень", he: "בצהריים" } ],
      answer: 0 },
    { q: { en: "What does Anna make?", ru: "Что А́нна ва́рит?", he: "מה אנה מכינה?" },
      options: [ { en: "Tea", ru: "Чай", he: "תה" }, { en: "Coffee", ru: "Ко́фе", he: "קפה" }, { en: "Soup", ru: "Суп", he: "מרק" } ],
      answer: 1 },
    { q: { en: "Who wants milk too?", ru: "Кто то́же хо́чет молока́?", he: "מי גם רוצה חלב?" },
      options: [ { en: "The dog", ru: "Соба́ка", he: "הכלב" }, { en: "Her husband", ru: "Её муж", he: "בעלה" }, { en: "The cat", ru: "Ко́шка", he: "החתולה" } ],
      answer: 2 }
  ]
});

LS_DATA.stories.push({
  id: "s_lost_cat", level: 1, emoji: "🐈",
  title: { en: "The Lost Cat", ru: "Пропа́вшая ко́шка", he: "החתולה שאבדה" },
  sentences: [
    { en: "Our cat Murka is lost.", ru: "На́ша ко́шка Му́рка пропа́ла.", he: "החתולה שלנו מורקה אבדה.", emoji: "😿" },
    { en: "We look in the garden.", ru: "Мы и́щем в саду́.", he: "אנחנו מחפשים בגינה.", emoji: "🌳" },
    { en: "She is not there.", ru: "Её там нет.", he: "היא לא שם.", emoji: "❌" },
    { en: "We look under the bed.", ru: "Мы смо́трим под крова́тью.", he: "אנחנו מסתכלים מתחת למיטה.", emoji: "🛏️" },
    { en: "She is not there either.", ru: "Там её то́же нет.", he: "גם שם היא לא נמצאת.", emoji: "🤷" },
    { en: "Then we hear a quiet \"meow.\"", ru: "Пото́м мы слы́шим ти́хое «мя́у».", he: "ואז אנחנו שומעים \"מיאו\" שקט.", emoji: "👂" },
    { en: "Murka is sleeping in the closet!", ru: "Му́рка спит в шкафу́!", he: "מורקה ישנה בארון!", emoji: "😴" },
    { en: "She is warm and happy.", ru: "Ей тепло́, и она́ дово́льна.", he: "חם לה, והיא מרוצה.", emoji: "🥰" }
  ],
  questions: [
    { q: { en: "Who is lost?", ru: "Кто пропа́л?", he: "מי אבד?" },
      options: [ { en: "The dog", ru: "Соба́ка", he: "הכלב" }, { en: "A bird", ru: "Пти́ца", he: "ציפור" }, { en: "The cat Murka", ru: "Ко́шка Му́рка", he: "החתולה מורקה" } ],
      answer: 2 },
    { q: { en: "Where do they look first?", ru: "Где они́ снача́ла и́щут?", he: "איפה הם מחפשים קודם?" },
      options: [ { en: "In the garden", ru: "В саду́", he: "בגינה" }, { en: "In the car", ru: "В маши́не", he: "באוטו" }, { en: "In the kitchen", ru: "На ку́хне", he: "במטבח" } ],
      answer: 0 },
    { q: { en: "Where is Murka sleeping?", ru: "Где спит Му́рка?", he: "איפה מורקה ישנה?" },
      options: [ { en: "Under the bed", ru: "Под крова́тью", he: "מתחת למיטה" }, { en: "In the closet", ru: "В шкафу́", he: "בארון" }, { en: "On the roof", ru: "На кры́ше", he: "על הגג" } ],
      answer: 1 }
  ]
});

LS_DATA.stories.push({
  id: "s_market", level: 1, emoji: "🛒",
  title: { en: "Market Day", ru: "База́рный день", he: "יום שוק" },
  sentences: [
    { en: "Today is market day.", ru: "Сего́дня база́рный день.", he: "היום יום שוק.", emoji: "🛒" },
    { en: "Dad takes a big basket.", ru: "Па́па берёт большу́ю корзи́ну.", he: "אבא לוקח סל גדול.", emoji: "🧺" },
    { en: "He buys red tomatoes.", ru: "Он покупа́ет кра́сные помидо́ры.", he: "הוא קונה עגבניות אדומות.", emoji: "🍅" },
    { en: "He buys sweet apples.", ru: "Он покупа́ет сла́дкие я́блоки.", he: "הוא קונה תפוחים מתוקים.", emoji: "🍎" },
    { en: "A seller gives him a free banana.", ru: "Продаве́ц даёт ему́ беспла́тный бана́н.", he: "מוכר נותן לו בננה בחינם.", emoji: "🍌" },
    { en: "Dad is very happy.", ru: "Па́па о́чень рад.", he: "אבא שמח מאוד.", emoji: "😄" },
    { en: "At home he sees: no bread!", ru: "До́ма он ви́дит: хле́ба нет!", he: "בבית הוא רואה: אין לחם!", emoji: "🍞" },
    { en: "He goes back to the market.", ru: "Он идёт обра́тно на база́р.", he: "הוא חוזר לשוק.", emoji: "🔁" }
  ],
  questions: [
    { q: { en: "What does Dad buy?", ru: "Что покупа́ет па́па?", he: "מה אבא קונה?" },
      options: [ { en: "Fish and rice", ru: "Ры́бу и рис", he: "דג ואורז" }, { en: "Milk and eggs", ru: "Молоко́ и я́йца", he: "חלב וביצים" }, { en: "Tomatoes and apples", ru: "Помидо́ры и я́блоки", he: "עגבניות ותפוחים" } ],
      answer: 2 },
    { q: { en: "What does the seller give him for free?", ru: "Что продаве́ц даёт ему́ беспла́тно?", he: "מה המוכר נותן לו בחינם?" },
      options: [ { en: "A banana", ru: "Бана́н", he: "בננה" }, { en: "An apple", ru: "Я́блоко", he: "תפוח" }, { en: "A tomato", ru: "Помидо́р", he: "עגבנייה" } ],
      answer: 0 },
    { q: { en: "What is missing at home?", ru: "Чего́ нет до́ма?", he: "מה חסר בבית?" },
      options: [ { en: "Milk", ru: "Молока́", he: "חלב" }, { en: "Bread", ru: "Хле́ба", he: "לחם" }, { en: "Coffee", ru: "Ко́фе", he: "קפה" } ],
      answer: 1 }
  ]
});

LS_DATA.stories.push({
  id: "s_grandma", level: 1, emoji: "👵",
  title: { en: "A Call from Grandma", ru: "Звоно́к от ба́бушки", he: "שיחה מסבתא" },
  sentences: [
    { en: "Grandma calls every Sunday.", ru: "Ба́бушка звони́т ка́ждое воскресе́нье.", he: "סבתא מתקשרת כל יום ראשון.", emoji: "📞" },
    { en: "\"Hello, my sweetheart!\"", ru: "«Приве́т, мой ми́лый!»", he: "\"שלום, מתוק שלי!\"", emoji: "👵" },
    { en: "\"Are you eating well?\"", ru: "«Ты хорошо́ ешь?»", he: "\"אתה אוכל טוב?\"", emoji: "🍲" },
    { en: "\"Yes, Grandma, very well.\"", ru: "«Да, ба́бушка, о́чень хорошо́».", he: "\"כן, סבתא, טוב מאוד.\"", emoji: "👍" },
    { en: "\"Are you wearing a hat?\"", ru: "«Ты но́сишь ша́пку?»", he: "\"אתה חובש כובע?\"", emoji: "🧢" },
    { en: "\"Grandma, it is summer now!\"", ru: "«Ба́бушка, сейча́с ле́то!»", he: "\"סבתא, עכשיו קיץ!\"", emoji: "☀️" },
    { en: "Grandma laughs out loud.", ru: "Ба́бушка гро́мко смеётся.", he: "סבתא צוחקת בקול.", emoji: "😂" },
    { en: "\"I love you very much.\"", ru: "«Я тебя́ о́чень люблю́».", he: "\"אני אוהבת אותך מאוד.\"", emoji: "❤️" }
  ],
  questions: [
    { q: { en: "When does Grandma call?", ru: "Когда́ звони́т ба́бушка?", he: "מתי סבתא מתקשרת?" },
      options: [ { en: "Every Friday", ru: "Ка́ждую пя́тницу", he: "כל יום שישי" }, { en: "Every Sunday", ru: "Ка́ждое воскресе́нье", he: "כל יום ראשון" }, { en: "Every morning", ru: "Ка́ждое у́тро", he: "כל בוקר" } ],
      answer: 1 },
    { q: { en: "What does Grandma ask about?", ru: "О чём спра́шивает ба́бушка?", he: "על מה סבתא שואלת?" },
      options: [ { en: "A hat", ru: "О ша́пке", he: "על כובע" }, { en: "A car", ru: "О маши́не", he: "על מכונית" }, { en: "A dog", ru: "О соба́ке", he: "על כלב" } ],
      answer: 0 },
    { q: { en: "What season is it now?", ru: "Како́е сейча́с вре́мя го́да?", he: "איזו עונה עכשיו?" },
      options: [ { en: "Winter", ru: "Зима́", he: "חורף" }, { en: "Spring", ru: "Весна́", he: "אביב" }, { en: "Summer", ru: "Ле́то", he: "קיץ" } ],
      answer: 2 }
  ]
});

LS_DATA.stories.push({
  id: "s_rain", level: 1, emoji: "🌧️",
  title: { en: "A Rainy Day", ru: "Дождли́вый день", he: "יום גשום" },
  sentences: [
    { en: "It is raining today.", ru: "Сего́дня идёт дождь.", he: "היום יורד גשם.", emoji: "🌧️" },
    { en: "Dan does not want to go out.", ru: "Дан не хо́чет выходи́ть.", he: "דן לא רוצה לצאת.", emoji: "🏠" },
    { en: "He reads a good book.", ru: "Он чита́ет хоро́шую кни́гу.", he: "הוא קורא ספר טוב.", emoji: "📖" },
    { en: "He drinks hot tea.", ru: "Он пьёт горя́чий чай.", he: "הוא שותה תה חם.", emoji: "🍵" },
    { en: "His dog looks at the door.", ru: "Его́ соба́ка смо́трит на дверь.", he: "הכלב שלו מסתכל על הדלת.", emoji: "🐕" },
    { en: "The dog wants a walk.", ru: "Соба́ка хо́чет гуля́ть.", he: "הכלב רוצה לטייל.", emoji: "🦮" },
    { en: "Dan takes an umbrella.", ru: "Дан берёт зонт.", he: "דן לוקח מטרייה.", emoji: "☂️" },
    { en: "Now they are both wet and happy.", ru: "Тепе́рь они́ о́ба мо́крые и счастли́вые.", he: "עכשיו שניהם רטובים ומאושרים.", emoji: "😄" }
  ],
  questions: [
    { q: { en: "What is the weather like today?", ru: "Кака́я сего́дня пого́да?", he: "מה מזג האוויר היום?" },
      options: [ { en: "It is snowing", ru: "Идёт снег", he: "יורד שלג" }, { en: "It is raining", ru: "Идёт дождь", he: "יורד גשם" }, { en: "It is hot", ru: "Жа́рко", he: "חם" } ],
      answer: 1 },
    { q: { en: "What does Dan drink?", ru: "Что пьёт Дан?", he: "מה דן שותה?" },
      options: [ { en: "Hot tea", ru: "Горя́чий чай", he: "תה חם" }, { en: "Cold juice", ru: "Холо́дный сок", he: "מיץ קר" }, { en: "Coffee", ru: "Ко́фе", he: "קפה" } ],
      answer: 0 },
    { q: { en: "What does Dan take?", ru: "Что берёт Дан?", he: "מה דן לוקח?" },
      options: [ { en: "A hat", ru: "Ша́пку", he: "כובע" }, { en: "A bag", ru: "Су́мку", he: "תיק" }, { en: "An umbrella", ru: "Зонт", he: "מטרייה" } ],
      answer: 2 }
  ]
});

LS_DATA.stories.push({
  id: "s_birthday", level: 2, emoji: "🎂",
  title: { en: "The Birthday Surprise", ru: "Сюрпри́з на день рожде́ния", he: "הפתעה ליום ההולדת" },
  sentences: [
    { en: "Yesterday was Mom's birthday.", ru: "Вчера́ был день рожде́ния ма́мы.", he: "אתמול היה יום ההולדת של אמא.", emoji: "🎂" },
    { en: "In the morning, nobody said anything.", ru: "У́тром никто́ ничего́ не сказа́л.", he: "בבוקר אף אחד לא אמר כלום.", emoji: "🤐" },
    { en: "Mom was a little sad.", ru: "Ма́ма немно́го грусти́ла.", he: "אמא הייתה קצת עצובה.", emoji: "😔" },
    { en: "She went to work alone.", ru: "Она́ пошла́ на рабо́ту одна́.", he: "היא הלכה לעבודה לבד.", emoji: "🚶‍♀️" },
    { en: "Meanwhile, Dad and the kids baked a cake.", ru: "Тем вре́менем па́па и де́ти испекли́ торт.", he: "בינתיים אבא והילדים אפו עוגה.", emoji: "🍰" },
    { en: "The cake came out a little crooked.", ru: "Торт получи́лся немно́го кривы́м.", he: "העוגה יצאה קצת עקומה.", emoji: "😅" },
    { en: "In the evening, Mom opened the door.", ru: "Ве́чером ма́ма откры́ла дверь.", he: "בערב אמא פתחה את הדלת.", emoji: "🚪" },
    { en: "Everyone shouted: \"Surprise!\"", ru: "Все закрича́ли: «Сюрпри́з!»", he: "כולם צעקו: \"הפתעה!\"", emoji: "🎉" },
    { en: "Mom laughed and cried at the same time.", ru: "Ма́ма смея́лась и пла́кала одновреме́нно.", he: "אמא צחקה ובכתה באותו זמן.", emoji: "🥹" },
    { en: "She said it was the best cake in the world.", ru: "Она́ сказа́ла, что э́то лу́чший торт в ми́ре.", he: "היא אמרה שזו העוגה הכי טובה בעולם.", emoji: "❤️" }
  ],
  questions: [
    { q: { en: "Whose birthday was it?", ru: "Чей был день рожде́ния?", he: "של מי היה יום ההולדת?" },
      options: [ { en: "Dad's", ru: "Па́пы", he: "של אבא" }, { en: "Mom's", ru: "Ма́мы", he: "של אמא" }, { en: "Grandma's", ru: "Ба́бушки", he: "של סבתא" } ],
      answer: 1 },
    { q: { en: "What did Dad and the kids bake?", ru: "Что испекли́ па́па и де́ти?", he: "מה אפו אבא והילדים?" },
      options: [ { en: "A cake", ru: "Торт", he: "עוגה" }, { en: "Bread", ru: "Хлеб", he: "לחם" }, { en: "Cookies", ru: "Пече́нье", he: "עוגיות" } ],
      answer: 0 },
    { q: { en: "How did the cake turn out?", ru: "Како́й получи́лся торт?", he: "איך יצאה העוגה?" },
      options: [ { en: "Very big", ru: "О́чень большо́й", he: "גדולה מאוד" }, { en: "Very small", ru: "О́чень ма́ленький", he: "קטנה מאוד" }, { en: "A little crooked", ru: "Немно́го кривы́й", he: "קצת עקומה" } ],
      answer: 2 }
  ]
});

LS_DATA.stories.push({
  id: "s_bus", level: 2, emoji: "🚌",
  title: { en: "The Wrong Bus", ru: "Не тот авто́бус", he: "האוטובוס הלא נכון" },
  sentences: [
    { en: "On Monday, Leah took the bus to work.", ru: "В понеде́льник Ле́я пое́хала на рабо́ту на авто́бусе.", he: "ביום שני לאה נסעה לעבודה באוטובוס.", emoji: "🚌" },
    { en: "She was very tired and closed her eyes.", ru: "Она́ о́чень уста́ла и закры́ла глаза́.", he: "היא הייתה עייפה מאוד ועצמה עיניים.", emoji: "😴" },
    { en: "When she opened them, everything looked strange.", ru: "Когда́ она́ их откры́ла, всё вокру́г бы́ло стра́нным.", he: "כשהיא פתחה אותן, הכול נראה מוזר.", emoji: "👀" },
    { en: "Outside there were fields and cows.", ru: "За окно́м бы́ли поля́ и коро́вы.", he: "בחוץ היו שדות ופרות.", emoji: "🐄" },
    { en: "She took the wrong bus!", ru: "Она́ се́ла не на тот авто́бус!", he: "היא עלתה על האוטובוס הלא נכון!", emoji: "😱" },
    { en: "Leah asked the driver where they were.", ru: "Ле́я спроси́ла води́теля, где они́.", he: "לאה שאלה את הנהג איפה הם.", emoji: "❓" },
    { en: "\"We are in a village,\" he answered.", ru: "«Мы в дере́вне», — отве́тил он.", he: "\"אנחנו בכפר,\" הוא ענה.", emoji: "🏡" },
    { en: "Leah called her boss and laughed.", ru: "Ле́я позвони́ла нача́льнику и засмея́лась.", he: "לאה התקשרה לבוס שלה וצחקה.", emoji: "📱" },
    { en: "Her boss laughed too.", ru: "Нача́льник то́же засмея́лся.", he: "גם הבוס צחק.", emoji: "😂" },
    { en: "That day, she bought fresh milk from a farmer.", ru: "В тот день она́ купи́ла све́жее молоко́ у фе́рмера.", he: "באותו יום היא קנתה חלב טרי מחקלאי.", emoji: "🥛" }
  ],
  questions: [
    { q: { en: "Why did Leah close her eyes?", ru: "Почему́ Ле́я закры́ла глаза́?", he: "למה לאה עצמה עיניים?" },
      options: [ { en: "She was tired", ru: "Она́ уста́ла", he: "היא הייתה עייפה" }, { en: "She was sad", ru: "Ей бы́ло гру́стно", he: "היא הייתה עצובה" }, { en: "The sun was bright", ru: "Со́лнце бы́ло я́рким", he: "השמש הייתה חזקה" } ],
      answer: 0 },
    { q: { en: "What did she see outside?", ru: "Что она́ уви́дела за окно́м?", he: "מה היא ראתה בחוץ?" },
      options: [ { en: "The sea", ru: "Мо́ре", he: "ים" }, { en: "Tall buildings", ru: "Высо́кие дома́", he: "בניינים גבוהים" }, { en: "Fields and cows", ru: "Поля́ и коро́в", he: "שדות ופרות" } ],
      answer: 2 },
    { q: { en: "Who did she call?", ru: "Кому́ она́ позвони́ла?", he: "למי היא התקשרה?" },
      options: [ { en: "Her mom", ru: "Ма́ме", he: "לאמא שלה" }, { en: "Her boss", ru: "Нача́льнику", he: "לבוס שלה" }, { en: "A taxi", ru: "В такси́", he: "למונית" } ],
      answer: 1 }
  ]
});

LS_DATA.stories.push({
  id: "s_cooking", level: 2, emoji: "🍗",
  title: { en: "The Cooking Disaster", ru: "Кулина́рная катастро́фа", he: "אסון במטבח" },
  sentences: [
    { en: "Last Friday, Boris decided to cook dinner.", ru: "В про́шлую пя́тницу Бори́с реши́л пригото́вить у́жин.", he: "ביום שישי שעבר בוריס החליט לבשל ארוחת ערב.", emoji: "👨‍🍳" },
    { en: "He wanted to surprise his wife.", ru: "Он хоте́л удиви́ть жену́.", he: "הוא רצה להפתיע את אשתו.", emoji: "💝" },
    { en: "He found a recipe on the internet.", ru: "Он нашёл реце́пт в интерне́те.", he: "הוא מצא מתכון באינטרנט.", emoji: "💻" },
    { en: "He put the chicken in the oven.", ru: "Он положи́л ку́рицу в духо́вку.", he: "הוא שם את העוף בתנור.", emoji: "🍗" },
    { en: "Then he sat down to watch soccer.", ru: "Пото́м он сел смотре́ть футбо́л.", he: "אחר כך הוא התיישב לראות כדורגל.", emoji: "⚽" },
    { en: "An hour later, the kitchen was full of smoke.", ru: "Че́рез час ку́хня была́ полна́ ды́ма.", he: "אחרי שעה המטבח היה מלא עשן.", emoji: "💨" },
    { en: "The chicken was as black as coal.", ru: "Ку́рица была́ чёрной, как у́голь.", he: "העוף היה שחור כמו פחם.", emoji: "⚫" },
    { en: "His wife came home and opened the windows.", ru: "Жена́ пришла́ домо́й и откры́ла о́кна.", he: "אשתו הגיעה הביתה ופתחה את החלונות.", emoji: "🪟" },
    { en: "Then she smiled and ordered pizza.", ru: "Пото́м она́ улыбну́лась и заказа́ла пи́ццу.", he: "ואז היא חייכה והזמינה פיצה.", emoji: "🍕" },
    { en: "In the end, it was a very nice dinner.", ru: "В конце́ концо́в у́жин получи́лся о́чень хоро́шим.", he: "בסוף זאת הייתה ארוחת ערב נחמדה מאוד.", emoji: "😄" }
  ],
  questions: [
    { q: { en: "What did Boris cook?", ru: "Что гото́вил Бори́с?", he: "מה בוריס בישל?" },
      options: [ { en: "Fish", ru: "Ры́бу", he: "דג" }, { en: "Chicken", ru: "Ку́рицу", he: "עוף" }, { en: "Soup", ru: "Суп", he: "מרק" } ],
      answer: 1 },
    { q: { en: "What did Boris do while the chicken was in the oven?", ru: "Что де́лал Бори́с, пока́ ку́рица была́ в духо́вке?", he: "מה בוריס עשה בזמן שהעוף היה בתנור?" },
      options: [ { en: "He watched soccer", ru: "Смотре́л футбо́л", he: "ראה כדורגל" }, { en: "He read a book", ru: "Чита́л кни́гу", he: "קרא ספר" }, { en: "He slept", ru: "Спал", he: "ישן" } ],
      answer: 0 },
    { q: { en: "What did they eat in the end?", ru: "Что они́ е́ли в конце́?", he: "מה הם אכלו בסוף?" },
      options: [ { en: "Chicken", ru: "Ку́рицу", he: "עוף" }, { en: "Salad", ru: "Сала́т", he: "סלט" }, { en: "Pizza", ru: "Пи́ццу", he: "פיצה" } ],
      answer: 2 }
  ]
});

LS_DATA.stories.push({
  id: "s_doctor", level: 2, emoji: "🩺",
  title: { en: "At the Doctor", ru: "У врача́", he: "אצל הרופא" },
  sentences: [
    { en: "Yesterday, Sam had a bad cough.", ru: "Вчера́ у Сэ́ма был си́льный ка́шель.", he: "אתמול היה לסאם שיעול חזק.", emoji: "🤧" },
    { en: "He went to the doctor.", ru: "Он пошёл к врачу́.", he: "הוא הלך לרופא.", emoji: "🏥" },
    { en: "He waited in line for a long time.", ru: "Он до́лго ждал в о́череди.", he: "הוא חיכה הרבה זמן בתור.", emoji: "⏳" },
    { en: "Finally, the doctor called him in.", ru: "Наконе́ц врач позва́л его́.", he: "סוף סוף הרופא קרא לו להיכנס.", emoji: "📋" },
    { en: "The doctor listened to his lungs.", ru: "Врач послу́шал его́ лёгкие.", he: "הרופא הקשיב לריאות שלו.", emoji: "🩺" },
    { en: "\"It is just a cold,\" the doctor said.", ru: "«Э́то про́сто просту́да», — сказа́л врач.", he: "\"זאת רק הצטננות,\" אמר הרופא.", emoji: "🙂" },
    { en: "\"Drink tea with honey and rest.\"", ru: "«Пе́йте чай с мёдом и отдыха́йте».", he: "\"תשתה תה עם דבש ותנוח.\"", emoji: "🍯" },
    { en: "Sam asked: \"Can I eat ice cream?\"", ru: "Сэм спроси́л: «Мо́жно есть моро́женое?»", he: "סאם שאל: \"מותר לאכול גלידה?\"", emoji: "🍦" },
    { en: "The doctor smiled: \"Only a little.\"", ru: "Врач улыбну́лся: «То́лько немно́го».", he: "הרופא חייך: \"רק קצת.\"", emoji: "😉" },
    { en: "On the way home, Sam bought honey... and ice cream.", ru: "По доро́ге домо́й Сэм купи́л мёд... и моро́женое.", he: "בדרך הביתה סאם קנה דבש... וגלידה.", emoji: "🛍️" }
  ],
  questions: [
    { q: { en: "What was wrong with Sam?", ru: "Что бы́ло у Сэ́ма?", he: "מה היה לסאם?" },
      options: [ { en: "A toothache", ru: "Зубна́я боль", he: "כאב שיניים" }, { en: "A broken leg", ru: "Сло́манная нога́", he: "רגל שבורה" }, { en: "A bad cough", ru: "Си́льный ка́шель", he: "שיעול חזק" } ],
      answer: 2 },
    { q: { en: "What did the doctor tell him to drink?", ru: "Что врач сказа́л пить?", he: "מה הרופא אמר לו לשתות?" },
      options: [ { en: "Tea with honey", ru: "Чай с мёдом", he: "תה עם דבש" }, { en: "Cold water", ru: "Холо́дную во́ду", he: "מים קרים" }, { en: "Orange juice", ru: "Апельси́новый сок", he: "מיץ תפוזים" } ],
      answer: 0 },
    { q: { en: "What did Sam ask about?", ru: "О чём спроси́л Сэм?", he: "על מה סאם שאל?" },
      options: [ { en: "About soccer", ru: "О футбо́ле", he: "על כדורגל" }, { en: "About ice cream", ru: "О моро́женом", he: "על גלידה" }, { en: "About chocolate", ru: "О шокола́де", he: "על שוקולד" } ],
      answer: 1 }
  ]
});

LS_DATA.stories.push({
  id: "s_sea", level: 3, emoji: "🏖️",
  title: { en: "A Trip to the Sea", ru: "Пое́здка на мо́ре", he: "טיול לים" },
  sentences: [
    { en: "Last summer, our family went to the sea for a week.", ru: "Про́шлым ле́том на́ша семья́ пое́хала на мо́ре на неде́лю.", he: "בקיץ שעבר המשפחה שלנו נסעה לים לשבוע.", emoji: "🏖️" },
    { en: "We packed our bags the evening before.", ru: "Мы собра́ли ве́щи накану́не ве́чером.", he: "ארזנו את התיקים בערב שלפני כן.", emoji: "🧳" },
    { en: "Dad wanted to leave at six in the morning.", ru: "Па́па хоте́л вы́ехать в шесть утра́.", he: "אבא רצה לצאת בשש בבוקר.", emoji: "⏰" },
    { en: "Of course, we left at ten.", ru: "Коне́чно, мы вы́ехали в де́сять.", he: "כמובן, יצאנו בעשר.", emoji: "😅" },
    { en: "On the road, the kids asked every five minutes: \"Are we there yet?\"", ru: "В доро́ге де́ти ка́ждые пять мину́т спра́шивали: «Мы уже́ прие́хали?»", he: "בדרך הילדים שאלו כל חמש דקות: \"כבר הגענו?\"", emoji: "🚗" },
    { en: "When we finally saw the sea, everyone shouted with joy.", ru: "Когда́ мы наконе́ц уви́дели мо́ре, все закрича́ли от ра́дости.", he: "כשסוף סוף ראינו את הים, כולם צעקו משמחה.", emoji: "🌊" },
    { en: "The water was warm and very clear.", ru: "Вода́ была́ тёплой и о́чень прозра́чной.", he: "המים היו חמים וצלולים מאוד.", emoji: "💧" },
    { en: "Grandpa fell asleep on the beach under an umbrella.", ru: "Де́душка усну́л на пля́же под зонто́м.", he: "סבא נרדם על החוף מתחת לשמשייה.", emoji: "⛱️" },
    { en: "The sun moved, and he woke up as red as a tomato.", ru: "Со́лнце сдви́нулось, и он просну́лся кра́сный, как помидо́р.", he: "השמש זזה, והוא התעורר אדום כמו עגבנייה.", emoji: "🍅" },
    { en: "Mom found a beautiful shell and gave it to me.", ru: "Ма́ма нашла́ краси́вую раку́шку и подари́ла её мне.", he: "אמא מצאה צדף יפה ונתנה לי אותו.", emoji: "🐚" },
    { en: "Every evening we ate ice cream and watched the sunset.", ru: "Ка́ждый ве́чер мы е́ли моро́женое и смотре́ли на зака́т.", he: "כל ערב אכלנו גלידה והסתכלנו על השקיעה.", emoji: "🌅" },
    { en: "That shell is still on my desk.", ru: "Э́та раку́шка до сих пор лежи́т у меня́ на столе́.", he: "הצדף הזה עדיין נמצא על השולחן שלי.", emoji: "💛" }
  ],
  questions: [
    { q: { en: "What time did the family really leave?", ru: "Во ско́лько семья́ на са́мом де́ле вы́ехала?", he: "באיזו שעה המשפחה באמת יצאה?" },
      options: [ { en: "At six", ru: "В шесть", he: "בשש" }, { en: "At eight", ru: "В во́семь", he: "בשמונה" }, { en: "At ten", ru: "В де́сять", he: "בעשר" } ],
      answer: 2 },
    { q: { en: "Why did Grandpa wake up red?", ru: "Почему́ де́душка просну́лся кра́сным?", he: "למה סבא התעורר אדום?" },
      options: [ { en: "The sun moved", ru: "Со́лнце сдви́нулось", he: "השמש זזה" }, { en: "He was angry", ru: "Он рассерди́лся", he: "הוא כעס" }, { en: "He ate tomatoes", ru: "Он съел помидо́ры", he: "הוא אכל עגבניות" } ],
      answer: 0 },
    { q: { en: "What did Mom find on the beach?", ru: "Что ма́ма нашла́ на пля́же?", he: "מה אמא מצאה על החוף?" },
      options: [ { en: "A coin", ru: "Моне́ту", he: "מטבע" }, { en: "A shell", ru: "Раку́шку", he: "צדף" }, { en: "A hat", ru: "Ша́пку", he: "כובע" } ],
      answer: 1 }
  ]
});

LS_DATA.stories.push({
  id: "s_neighbor", level: 3, emoji: "🎻",
  title: { en: "The New Neighbor", ru: "Но́вый сосе́д", he: "השכן החדש" },
  sentences: [
    { en: "A new neighbor moved into the apartment next to ours.", ru: "В кварти́ру ря́дом с на́шей перее́хал но́вый сосе́д.", he: "שכן חדש עבר לדירה שליד הדירה שלנו.", emoji: "🏢" },
    { en: "For three days, we heard only loud music through the wall.", ru: "Три дня мы слы́шали то́лько гро́мкую му́зыку из-за стены́.", he: "שלושה ימים שמענו רק מוזיקה רועשת מבעד לקיר.", emoji: "🎵" },
    { en: "Mom was angry and wanted to complain.", ru: "Ма́ма серди́лась и хоте́ла пожа́ловаться.", he: "אמא כעסה ורצתה להתלונן.", emoji: "😠" },
    { en: "But then she decided to bake a cake and meet him first.", ru: "Но пото́м она́ реши́ла снача́ла испе́чь пиро́г и познако́миться с ним.", he: "אבל אז היא החליטה קודם לאפות עוגה ולהכיר אותו.", emoji: "🥧" },
    { en: "She knocked on his door with the warm cake.", ru: "Она́ постуча́ла в его́ дверь с тёплым пирого́м.", he: "היא דפקה על הדלת שלו עם העוגה החמה.", emoji: "🚪" },
    { en: "An old man with a violin opened the door.", ru: "Дверь откры́л пожило́й мужчи́на со скри́пкой.", he: "איש מבוגר עם כינור פתח את הדלת.", emoji: "🎻" },
    { en: "It turned out that he was a musician in an orchestra.", ru: "Оказа́лось, что он музыка́нт из орке́стра.", he: "התברר שהוא מוזיקאי בתזמורת.", emoji: "🎼" },
    { en: "He was practicing for a big concert.", ru: "Он гото́вился к большо́му конце́рту.", he: "הוא התאמן לקראת קונצרט גדול.", emoji: "🎶" },
    { en: "He apologized for the noise and invited her in for tea.", ru: "Он извини́лся за шум и пригласи́л её на чай.", he: "הוא התנצל על הרעש והזמין אותה לתה.", emoji: "☕" },
    { en: "They talked for two hours, in Russian!", ru: "Они́ проговори́ли два часа́ — по-ру́сски!", he: "הם דיברו שעתיים — ברוסית!", emoji: "🗣️" },
    { en: "Now he plays quietly in the evenings.", ru: "Тепе́рь по вечера́м он игра́ет ти́хо.", he: "עכשיו הוא מנגן בשקט בערבים.", emoji: "🤫" },
    { en: "And every Sunday, Mom brings him a cake.", ru: "А ка́ждое воскресе́нье ма́ма прино́сит ему́ пиро́г.", he: "ובכל יום ראשון אמא מביאה לו עוגה.", emoji: "🍰" }
  ],
  questions: [
    { q: { en: "What did the family hear through the wall?", ru: "Что семья́ слы́шала из-за стены́?", he: "מה המשפחה שמעה מבעד לקיר?" },
      options: [ { en: "A dog", ru: "Соба́ку", he: "כלב" }, { en: "A baby crying", ru: "Плач ребёнка", he: "בכי של תינוק" }, { en: "Loud music", ru: "Гро́мкую му́зыку", he: "מוזיקה רועשת" } ],
      answer: 2 },
    { q: { en: "Who was the new neighbor?", ru: "Кем был но́вый сосе́д?", he: "מי היה השכן החדש?" },
      options: [ { en: "A doctor", ru: "Врачо́м", he: "רופא" }, { en: "A musician", ru: "Музыка́нтом", he: "מוזיקאי" }, { en: "A teacher", ru: "Учи́телем", he: "מורה" } ],
      answer: 1 },
    { q: { en: "What did Mom bring the neighbor?", ru: "Что ма́ма принесла́ сосе́ду?", he: "מה אמא הביאה לשכן?" },
      options: [ { en: "A cake", ru: "Пиро́г", he: "עוגה" }, { en: "Flowers", ru: "Цветы́", he: "פרחים" }, { en: "A complaint", ru: "Жа́лобу", he: "תלונה" } ],
      answer: 0 }
  ]
});

LS_DATA.stories.push({
  id: "s_family_lang", level: 3, emoji: "📚",
  title: { en: "Learning Together", ru: "У́чимся вме́сте", he: "לומדים ביחד" },
  sentences: [
    { en: "Every evening after dinner, Mom and her son have a lesson.", ru: "Ка́ждый ве́чер по́сле у́жина у ма́мы с сы́ном уро́к.", he: "כל ערב אחרי ארוחת הערב יש לאמא ולבן שלה שיעור.", emoji: "📚" },
    { en: "Mom teaches Russian, and her son teaches English.", ru: "Ма́ма преподаёт ру́сский, а сын — англи́йский.", he: "אמא מלמדת רוסית, והבן שלה מלמד אנגלית.", emoji: "🔄" },
    { en: "Yesterday, the son tried to say a long Russian word.", ru: "Вчера́ сын пыта́лся сказа́ть дли́нное ру́сское сло́во.", he: "אתמול הבן ניסה להגיד מילה רוסית ארוכה.", emoji: "🗣️" },
    { en: "He said it five times, and every time it sounded different.", ru: "Он сказа́л его́ пять раз, и ка́ждый раз оно́ звуча́ло по-ра́зному.", he: "הוא אמר אותה חמש פעמים, ובכל פעם היא נשמעה אחרת.", emoji: "😅" },
    { en: "Mom laughed until she cried.", ru: "Ма́ма смея́лась до слёз.", he: "אמא צחקה עד דמעות.", emoji: "😂" },
    { en: "Then Mom tried to say the English sound \"th.\"", ru: "Пото́м ма́ма попро́бовала произнести́ англи́йский звук «th».", he: "ואז אמא ניסתה להגות את הצליל האנגלי \"th\".", emoji: "👅" },
    { en: "Her tongue did not want to stay between her teeth.", ru: "Язы́к не хоте́л остава́ться ме́жду зуба́ми.", he: "הלשון שלה לא רצתה להישאר בין השיניים.", emoji: "🦷" },
    { en: "Now it was the son's turn to laugh.", ru: "Тепе́рь уже́ смея́лся сын.", he: "עכשיו הגיע תורו של הבן לצחוק.", emoji: "😆" },
    { en: "They made a deal: no laughing at mistakes.", ru: "Они́ договори́лись: над оши́бками не смеёмся.", he: "הם סיכמו: לא צוחקים על טעויות.", emoji: "🤝" },
    { en: "Of course, they broke the deal the very next day.", ru: "Коне́чно, уже́ на сле́дующий день они́ нару́шили угово́р.", he: "כמובן, כבר למחרת הם הפרו את ההסכם.", emoji: "🙈" },
    { en: "But mistakes are part of learning, and laughing together helps.", ru: "Но оши́бки — часть учёбы, а смех вме́сте помога́ет.", he: "אבל טעויות הן חלק מהלמידה, וצחוק משותף עוזר.", emoji: "💡" },
    { en: "Little by little, they both speak better and better.", ru: "Ма́ло-пома́лу о́ба говоря́т всё лу́чше.", he: "לאט לאט שניהם מדברים יותר ויותר טוב.", emoji: "🌱" }
  ],
  questions: [
    { q: { en: "What does the son teach?", ru: "Что преподаёт сын?", he: "מה הבן מלמד?" },
      options: [ { en: "English", ru: "Англи́йский", he: "אנגלית" }, { en: "Russian", ru: "Ру́сский", he: "רוסית" }, { en: "Hebrew", ru: "Иври́т", he: "עברית" } ],
      answer: 0 },
    { q: { en: "Why did Mom cry?", ru: "Почему́ ма́ма пла́кала?", he: "למה אמא בכתה?" },
      options: [ { en: "She was sad", ru: "Ей бы́ло гру́стно", he: "היא הייתה עצובה" }, { en: "She laughed too much", ru: "Она́ сли́шком смея́лась", he: "היא צחקה יותר מדי" }, { en: "She was cutting onions", ru: "Она́ ре́зала лук", he: "היא חתכה בצל" } ],
      answer: 1 },
    { q: { en: "What deal did they make?", ru: "О чём они́ договори́лись?", he: "על מה הם סיכמו?" },
      options: [ { en: "To speak only English", ru: "Говори́ть то́лько по-англи́йски", he: "לדבר רק אנגלית" }, { en: "No TV after dinner", ru: "Не смотре́ть телеви́зор по́сле у́жина", he: "לא לראות טלוויזיה אחרי ארוחת הערב" }, { en: "No laughing at mistakes", ru: "Не смея́ться над оши́бками", he: "לא לצחוק על טעויות" } ],
      answer: 2 }
  ]
});

LS_DATA.stories.push({
  id: "s_new_phone", level: 1, emoji: "📱",
  title: { en: "Grandpa's New Phone", ru: "Но́вый телефо́н де́душки", he: "הטלפון החדש של סבא" },
  sentences: [
    { en: "Grandpa Boris has a new phone.", ru: "У де́душки Бори́са но́вый телефо́н.", he: "לסבא בוריס יש טלפון חדש.", emoji: "📱" },
    { en: "The phone is big and black.", ru: "Телефо́н большо́й и чёрный.", he: "הטלפון גדול ושחור.", emoji: "⬛" },
    { en: "Boris does not understand the buttons.", ru: "Бори́с не понима́ет кно́пки.", he: "בוריס לא מבין את הכפתורים.", emoji: "🤔" },
    { en: "He calls his grandson Dan.", ru: "Он звони́т вну́ку Да́ну.", he: "הוא מתקשר לנכד שלו, דן.", emoji: "📞" },
    { en: "Dan comes and helps him.", ru: "Дан прихо́дит и помога́ет ему́.", he: "דן בא ועוזר לו.", emoji: "🧑" },
    { en: "Now Boris sends photos to the family.", ru: "Тепе́рь Бори́с отправля́ет фо́то семье́.", he: "עכשיו בוריס שולח תמונות למשפחה.", emoji: "📸" },
    { en: "Everyone gets twenty photos of his cat!", ru: "Все получа́ют два́дцать фо́то его́ ко́шки!", he: "כולם מקבלים עשרים תמונות של החתולה שלו!", emoji: "😂" }
  ],
  questions: [
    { q: { en: "What color is the phone?", ru: "Како́го цве́та телефо́н?", he: "באיזה צבע הטלפון?" },
      options: [ { en: "White", ru: "Бе́лый", he: "לבן" }, { en: "Black", ru: "Чёрный", he: "שחור" }, { en: "Red", ru: "Кра́сный", he: "אדום" } ],
      answer: 1 },
    { q: { en: "Who helps Boris?", ru: "Кто помога́ет Бори́су?", he: "מי עוזר לבוריס?" },
      options: [ { en: "His grandson", ru: "Его́ внук", he: "הנכד שלו" }, { en: "His wife", ru: "Его́ жена́", he: "אשתו" }, { en: "A neighbor", ru: "Сосе́д", he: "שכן" } ],
      answer: 0 },
    { q: { en: "What is in the photos?", ru: "Что на фо́то?", he: "מה יש בתמונות?" },
      options: [ { en: "The sea", ru: "Мо́ре", he: "הים" }, { en: "Flowers", ru: "Цветы́", he: "פרחים" }, { en: "His cat", ru: "Его́ ко́шка", he: "החתולה שלו" } ],
      answer: 2 }
  ]
});

LS_DATA.stories.push({
  id: "s_first_snow", level: 1, emoji: "❄️",
  title: { en: "The First Snow", ru: "Пе́рвый снег", he: "השלג הראשון" },
  sentences: [
    { en: "Today it is very cold in Jerusalem.", ru: "Сего́дня в Иерусали́ме о́чень хо́лодно.", he: "היום קר מאוד בירושלים.", emoji: "🥶" },
    { en: "In the morning, Lena looks out the window.", ru: "У́тром Ле́на смо́трит в окно́.", he: "בבוקר לנה מסתכלת מהחלון.", emoji: "🪟" },
    { en: "Everything is white!", ru: "Всё бе́лое!", he: "הכול לבן!", emoji: "⬜" },
    { en: "It is the first snow of the year.", ru: "Э́то пе́рвый снег в э́том году́.", he: "זה השלג הראשון השנה.", emoji: "❄️" },
    { en: "The children run outside.", ru: "Де́ти бегу́т на у́лицу.", he: "הילדים רצים החוצה.", emoji: "🏃" },
    { en: "They make a small snowman.", ru: "Они́ де́лают ма́ленького снегови́ка.", he: "הם בונים איש שלג קטן.", emoji: "⛄" },
    { en: "Then they drink hot tea at home.", ru: "Пото́м они́ пьют горя́чий чай до́ма.", he: "אחר כך הם שותים תה חם בבית.", emoji: "🍵" }
  ],
  questions: [
    { q: { en: "Where is it cold today?", ru: "Где сего́дня хо́лодно?", he: "איפה קר היום?" },
      options: [ { en: "In Haifa", ru: "В Ха́йфе", he: "בחיפה" }, { en: "In Eilat", ru: "В Эйла́те", he: "באילת" }, { en: "In Jerusalem", ru: "В Иерусали́ме", he: "בירושלים" } ],
      answer: 2 },
    { q: { en: "What do the children make?", ru: "Что де́лают де́ти?", he: "מה הילדים בונים?" },
      options: [ { en: "A snowman", ru: "Снегови́ка", he: "איש שלג" }, { en: "A cake", ru: "Торт", he: "עוגה" }, { en: "A house", ru: "Дом", he: "בית" } ],
      answer: 0 },
    { q: { en: "What do they drink at home?", ru: "Что они́ пьют до́ма?", he: "מה הם שותים בבית?" },
      options: [ { en: "Cold juice", ru: "Холо́дный сок", he: "מיץ קר" }, { en: "Hot tea", ru: "Горя́чий чай", he: "תה חם" }, { en: "Milk", ru: "Молоко́", he: "חלב" } ],
      answer: 1 }
  ]
});

LS_DATA.stories.push({
  id: "s_dentist", level: 1, emoji: "🦷",
  title: { en: "At the Dentist", ru: "У зубно́го врача́", he: "אצל רופאת השיניים" },
  sentences: [
    { en: "Michael has a toothache.", ru: "У Михаи́ла боли́т зуб.", he: "למיכאל כואבת השן.", emoji: "🦷" },
    { en: "He cannot eat or sleep.", ru: "Он не мо́жет ни есть, ни спать.", he: "הוא לא יכול לאכול וגם לא לישון.", emoji: "😣" },
    { en: "He goes to the dentist.", ru: "Он идёт к зубно́му врачу́.", he: "הוא הולך לרופאת שיניים.", emoji: "🏥" },
    { en: "The dentist smiles and says: Open your mouth.", ru: "Врач улыба́ется и говори́т: «Откро́йте рот».", he: "הרופאה מחייכת ואומרת: תפתח את הפה.", emoji: "😁" },
    { en: "It does not hurt much.", ru: "Э́то не о́чень бо́льно.", he: "זה לא כואב הרבה.", emoji: "👍" },
    { en: "After ten minutes, the tooth is fine.", ru: "Че́рез де́сять мину́т зуб в поря́дке.", he: "אחרי עשר דקות השן בסדר.", emoji: "⏱️" },
    { en: "Michael smiles and goes home.", ru: "Михаи́л улыба́ется и идёт домо́й.", he: "מיכאל מחייך והולך הביתה.", emoji: "😊" }
  ],
  questions: [
    { q: { en: "What hurts Michael?", ru: "Что боли́т у Михаи́ла?", he: "מה כואב למיכאל?" },
      options: [ { en: "His head", ru: "Голова́", he: "הראש" }, { en: "His tooth", ru: "Зуб", he: "השן" }, { en: "His leg", ru: "Нога́", he: "הרגל" } ],
      answer: 1 },
    { q: { en: "What does the dentist say?", ru: "Что говори́т врач?", he: "מה הרופאה אומרת?" },
      options: [ { en: "Open your mouth", ru: "Откро́йте рот", he: "תפתח את הפה" }, { en: "Go home", ru: "Иди́те домо́й", he: "לך הביתה" }, { en: "Come back tomorrow", ru: "Приходи́те за́втра", he: "תחזור מחר" } ],
      answer: 0 },
    { q: { en: "How long does it take?", ru: "Ско́лько вре́мени э́то занима́ет?", he: "כמה זמן זה לוקח?" },
      options: [ { en: "An hour", ru: "Час", he: "שעה" }, { en: "Two days", ru: "Два дня", he: "יומיים" }, { en: "Ten minutes", ru: "Де́сять мину́т", he: "עשר דקות" } ],
      answer: 2 }
  ]
});

LS_DATA.stories.push({
  id: "s_picnic", level: 1, emoji: "🧺",
  title: { en: "A Picnic in the Park", ru: "Пикни́к в па́рке", he: "פיקניק בפארק" },
  sentences: [
    { en: "It is a sunny Saturday.", ru: "Сего́дня со́лнечная суббо́та.", he: "היום שבת שמשית.", emoji: "☀️" },
    { en: "The family goes to the park.", ru: "Семья́ идёт в парк.", he: "המשפחה הולכת לפארק.", emoji: "🌳" },
    { en: "Mom brings sandwiches and fruit.", ru: "Ма́ма берёт бутербро́ды и фру́кты.", he: "אמא לוקחת כריכים ופירות.", emoji: "🥪" },
    { en: "Dad brings a big blanket.", ru: "Па́па берёт большо́е покрыва́ло.", he: "אבא לוקח שמיכה גדולה.", emoji: "🧺" },
    { en: "They sit under a tree and eat.", ru: "Они́ сидя́т под де́ревом и едя́т.", he: "הם יושבים מתחת לעץ ואוכלים.", emoji: "🍉" },
    { en: "A bird comes and takes some bread.", ru: "Прилета́ет пти́ца и берёт хлеб.", he: "ציפור מגיעה ולוקחת לחם.", emoji: "🐦" },
    { en: "Everyone laughs.", ru: "Все смею́тся.", he: "כולם צוחקים.", emoji: "😄" }
  ],
  questions: [
    { q: { en: "What day is it?", ru: "Како́й сего́дня день?", he: "איזה יום היום?" },
      options: [ { en: "Monday", ru: "Понеде́льник", he: "יום שני" }, { en: "Friday", ru: "Пя́тница", he: "יום שישי" }, { en: "Saturday", ru: "Суббо́та", he: "שבת" } ],
      answer: 2 },
    { q: { en: "What does Dad bring?", ru: "Что берёт па́па?", he: "מה אבא לוקח?" },
      options: [ { en: "Sandwiches", ru: "Бутербро́ды", he: "כריכים" }, { en: "A blanket", ru: "Покрыва́ло", he: "שמיכה" }, { en: "A ball", ru: "Мяч", he: "כדור" } ],
      answer: 1 },
    { q: { en: "Who takes the bread?", ru: "Кто берёт хлеб?", he: "מי לוקח את הלחם?" },
      options: [ { en: "A bird", ru: "Пти́ца", he: "ציפור" }, { en: "A dog", ru: "Соба́ка", he: "כלב" }, { en: "A child", ru: "Ребёнок", he: "ילד" } ],
      answer: 0 }
  ]
});

LS_DATA.stories.push({
  id: "s_gift", level: 2, emoji: "🎁",
  title: { en: "A Gift for Mom", ru: "Пода́рок для ма́мы", he: "מתנה לאמא" },
  sentences: [
    { en: "Next week is Mom's birthday.", ru: "На сле́дующей неде́ле у ма́мы день рожде́ния.", he: "בשבוע הבא יום ההולדת של אמא.", emoji: "🎂" },
    { en: "Daniel wants to buy her a gift.", ru: "Дании́л хо́чет купи́ть ей пода́рок.", he: "דניאל רוצה לקנות לה מתנה.", emoji: "🎁" },
    { en: "He has only one hundred shekels.", ru: "У него́ то́лько сто ше́келей.", he: "יש לו רק מאה שקלים.", emoji: "💰" },
    { en: "First he goes to a flower shop.", ru: "Снача́ла он идёт в цвето́чный магази́н.", he: "קודם הוא הולך לחנות פרחים.", emoji: "💐" },
    { en: "The flowers are beautiful, but they die quickly.", ru: "Цветы́ краси́вые, но они́ бы́стро вя́нут.", he: "הפרחים יפים, אבל הם נובלים מהר.", emoji: "🥀" },
    { en: "Then he sees a small bookshop.", ru: "Пото́м он ви́дит ма́ленький кни́жный магази́н.", he: "אחר כך הוא רואה חנות ספרים קטנה.", emoji: "📚" },
    { en: "Mom loves to read, but she reads in Russian.", ru: "Ма́ма лю́бит чита́ть, но она́ чита́ет по-ру́сски.", he: "אמא אוהבת לקרוא, אבל היא קוראת ברוסית.", emoji: "📖" },
    { en: "The seller finds a Russian cookbook.", ru: "Продаве́ц нахо́дит ру́сскую кулина́рную кни́гу.", he: "המוכר מוצא ספר בישול ברוסית.", emoji: "🔍" },
    { en: "It costs ninety shekels.", ru: "Она́ сто́ит девяно́сто ше́келей.", he: "הוא עולה תשעים שקלים.", emoji: "🏷️" },
    { en: "Daniel is happy: the gift is perfect.", ru: "Дании́л дово́лен: пода́рок идеа́льный.", he: "דניאל מרוצה: המתנה מושלמת.", emoji: "😊" }
  ],
  questions: [
    { q: { en: "How much money does Daniel have?", ru: "Ско́лько де́нег у Дании́ла?", he: "כמה כסף יש לדניאל?" },
      options: [ { en: "Fifty shekels", ru: "Пятьдеся́т ше́келей", he: "חמישים שקלים" }, { en: "One hundred shekels", ru: "Сто ше́келей", he: "מאה שקלים" }, { en: "Two hundred shekels", ru: "Две́сти ше́келей", he: "מאתיים שקלים" } ],
      answer: 1 },
    { q: { en: "Why doesn't he buy flowers?", ru: "Почему́ он не покупа́ет цветы́?", he: "למה הוא לא קונה פרחים?" },
      options: [ { en: "They are expensive", ru: "Они́ дороги́е", he: "הם יקרים" }, { en: "Mom doesn't like flowers", ru: "Ма́ма не лю́бит цветы́", he: "אמא לא אוהבת פרחים" }, { en: "They die quickly", ru: "Они́ бы́стро вя́нут", he: "הם נובלים מהר" } ],
      answer: 2 },
    { q: { en: "What gift does he buy?", ru: "Како́й пода́рок он покупа́ет?", he: "איזו מתנה הוא קונה?" },
      options: [ { en: "A cookbook", ru: "Кулина́рную кни́гу", he: "ספר בישול" }, { en: "A scarf", ru: "Шарф", he: "צעיף" }, { en: "Chocolate", ru: "Шокола́д", he: "שוקולד" } ],
      answer: 0 }
  ]
});

LS_DATA.stories.push({
  id: "s_power_outage", level: 2, emoji: "🕯️",
  title: { en: "The Power Outage", ru: "Без све́та", he: "הפסקת חשמל" },
  sentences: [
    { en: "On Tuesday evening, the electricity went out.", ru: "Во вто́рник ве́чером пропа́ло электри́чество.", he: "ביום שלישי בערב החשמל נפל.", emoji: "💡" },
    { en: "The whole building was dark.", ru: "Весь дом был в темноте́.", he: "כל הבניין היה בחושך.", emoji: "🌑" },
    { en: "The TV and the internet did not work.", ru: "Телеви́зор и интерне́т не рабо́тали.", he: "הטלוויזיה והאינטרנט לא עבדו.", emoji: "📺" },
    { en: "Grandma found candles in the kitchen.", ru: "Ба́бушка нашла́ све́чи на ку́хне.", he: "סבתא מצאה נרות במטבח.", emoji: "🕯️" },
    { en: "The family sat together at the table.", ru: "Семья́ се́ла вме́сте за стол.", he: "המשפחה ישבה ביחד ליד השולחן.", emoji: "👨‍👩‍👧" },
    { en: "Grandma told stories about her childhood.", ru: "Ба́бушка расска́зывала исто́рии о своём де́тстве.", he: "סבתא סיפרה סיפורים על הילדות שלה.", emoji: "👵" },
    { en: "Then they played cards.", ru: "Пото́м они́ игра́ли в ка́рты.", he: "אחר כך הם שיחקו בקלפים.", emoji: "🃏" },
    { en: "After two hours, the light came back.", ru: "Че́рез два часа́ свет верну́лся.", he: "אחרי שעתיים האור חזר.", emoji: "💡" },
    { en: "But nobody wanted to turn on the TV.", ru: "Но никто́ не хоте́л включа́ть телеви́зор.", he: "אבל אף אחד לא רצה להדליק את הטלוויזיה.", emoji: "🙂" }
  ],
  questions: [
    { q: { en: "When did the electricity go out?", ru: "Когда́ пропа́ло электри́чество?", he: "מתי החשמל נפל?" },
      options: [ { en: "On Monday morning", ru: "В понеде́льник у́тром", he: "ביום שני בבוקר" }, { en: "On Friday night", ru: "В пя́тницу но́чью", he: "ביום שישי בלילה" }, { en: "On Tuesday evening", ru: "Во вто́рник ве́чером", he: "ביום שלישי בערב" } ],
      answer: 2 },
    { q: { en: "What did Grandma find?", ru: "Что нашла́ ба́бушка?", he: "מה סבתא מצאה?" },
      options: [ { en: "A flashlight", ru: "Фона́рик", he: "פנס" }, { en: "Candles", ru: "Све́чи", he: "נרות" }, { en: "Cards", ru: "Ка́рты", he: "קלפים" } ],
      answer: 1 },
    { q: { en: "How long was there no light?", ru: "Ско́лько вре́мени не бы́ло све́та?", he: "כמה זמן לא היה אור?" },
      options: [ { en: "Two hours", ru: "Два часа́", he: "שעתיים" }, { en: "Ten minutes", ru: "Де́сять мину́т", he: "עשר דקות" }, { en: "All night", ru: "Всю ночь", he: "כל הלילה" } ],
      answer: 0 }
  ]
});

LS_DATA.stories.push({
  id: "s_lost_passport", level: 2, emoji: "🛂",
  title: { en: "The Lost Passport", ru: "Поте́рянный па́спорт", he: "הדרכון שאבד" },
  sentences: [
    { en: "Olga was at the airport with her husband.", ru: "О́льга была́ в аэропорту́ с му́жем.", he: "אולגה הייתה בשדה התעופה עם בעלה.", emoji: "✈️" },
    { en: "Their flight to Rome was in two hours.", ru: "Их рейс в Рим был че́рез два часа́.", he: "הטיסה שלהם לרומא הייתה בעוד שעתיים.", emoji: "🕑" },
    { en: "Suddenly Olga could not find her passport.", ru: "Вдруг О́льга не смогла́ найти́ свой па́спорт.", he: "פתאום אולגה לא הצליחה למצוא את הדרכון שלה.", emoji: "😱" },
    { en: "She looked in her bag and in her pockets.", ru: "Она́ посмотре́ла в су́мке и в карма́нах.", he: "היא חיפשה בתיק ובכיסים.", emoji: "👜" },
    { en: "The passport was gone.", ru: "Па́спорт пропа́л.", he: "הדרכון נעלם.", emoji: "❌" },
    { en: "Her husband called the café where they ate breakfast.", ru: "Муж позвони́л в кафе́, где они́ за́втракали.", he: "בעלה התקשר לבית הקפה שבו הם אכלו ארוחת בוקר.", emoji: "☎️" },
    { en: "A waiter answered: \"Yes, we have a passport here!\"", ru: "Официа́нт отве́тил: «Да, у нас есть па́спорт!»", he: "מלצר ענה: \"כן, יש אצלנו דרכון!\"", emoji: "🙌" },
    { en: "Olga ran to the café and took it.", ru: "О́льга побежа́ла в кафе́ и забрала́ его́.", he: "אולגה רצה לבית הקפה ולקחה אותו.", emoji: "🏃‍♀️" },
    { en: "They made it to the flight just in time.", ru: "Они́ успе́ли на рейс в после́днюю мину́ту.", he: "הם הספיקו לטיסה ברגע האחרון.", emoji: "✅" },
    { en: "Now Olga always keeps her passport in one place.", ru: "Тепе́рь О́льга всегда́ храни́т па́спорт в одно́м ме́сте.", he: "עכשיו אולגה תמיד שומרת את הדרכון במקום אחד.", emoji: "📌" }
  ],
  questions: [
    { q: { en: "Where were they flying?", ru: "Куда́ они́ лете́ли?", he: "לאן הם טסו?" },
      options: [ { en: "To Paris", ru: "В Пари́ж", he: "לפריז" }, { en: "To Rome", ru: "В Рим", he: "לרומא" }, { en: "To London", ru: "В Ло́ндон", he: "ללונדון" } ],
      answer: 1 },
    { q: { en: "Where was the passport?", ru: "Где был па́спорт?", he: "איפה היה הדרכון?" },
      options: [ { en: "In the café", ru: "В кафе́", he: "בבית הקפה" }, { en: "In a taxi", ru: "В такси́", he: "במונית" }, { en: "At home", ru: "До́ма", he: "בבית" } ],
      answer: 0 },
    { q: { en: "Did they miss the flight?", ru: "Они́ опозда́ли на рейс?", he: "הם פספסו את הטיסה?" },
      options: [ { en: "Yes", ru: "Да", he: "כן" }, { en: "Yes, by one hour", ru: "Да, на час", he: "כן, בשעה" }, { en: "No, they made it", ru: "Нет, они́ успе́ли", he: "לא, הם הספיקו" } ],
      answer: 2 }
  ]
});

LS_DATA.stories.push({
  id: "s_train", level: 2, emoji: "🚆",
  title: { en: "A Train Journey", ru: "Пое́здка на по́езде", he: "נסיעה ברכבת" },
  sentences: [
    { en: "Sara takes the train from Tel Aviv to Haifa.", ru: "Са́ра е́дет на по́езде из Тель-Ави́ва в Ха́йфу.", he: "שרה נוסעת ברכבת מתל אביב לחיפה.", emoji: "🚆" },
    { en: "There are many people on the train, but she finds a seat by the window.", ru: "В по́езде мно́го люде́й, но она́ нахо́дит ме́сто у окна́.", he: "ברכבת יש הרבה אנשים, אבל היא מוצאת מקום ליד החלון.", emoji: "🪑" },
    { en: "An old man sits down next to her.", ru: "Ря́дом с ней сади́тся пожило́й мужчи́на.", he: "לידה מתיישב איש מבוגר.", emoji: "👴" },
    { en: "He is reading a newspaper in Russian.", ru: "Он чита́ет газе́ту на ру́сском.", he: "הוא קורא עיתון ברוסית.", emoji: "📰" },
    { en: "Sara asks him: \"Are you from Russia?\"", ru: "Са́ра спра́шивает его́: «Вы из Росси́и?»", he: "שרה שואלת אותו: \"אתה מרוסיה?\"", emoji: "❓" },
    { en: "\"No, from Riga,\" he says with a smile.", ru: "«Нет, из Ри́ги», — говори́т он с улы́бкой.", he: "\"לא, מריגה,\" הוא אומר בחיוך.", emoji: "😊" },
    { en: "They talk the whole way.", ru: "Они́ разгова́ривают всю доро́гу.", he: "הם מדברים כל הדרך.", emoji: "💬" },
    { en: "Outside, the sea shines in the sun.", ru: "За окно́м мо́ре блести́т на со́лнце.", he: "בחוץ הים מנצנץ בשמש.", emoji: "🌊" },
    { en: "The hour goes by very fast.", ru: "Час прохо́дит о́чень бы́стро.", he: "השעה עוברת מהר מאוד.", emoji: "⏱️" },
    { en: "At the station, they say goodbye like old friends.", ru: "На ста́нции они́ проща́ются как ста́рые друзья́.", he: "בתחנה הם נפרדים כמו חברים ותיקים.", emoji: "👋" }
  ],
  questions: [
    { q: { en: "Where is Sara going?", ru: "Куда́ е́дет Са́ра?", he: "לאן שרה נוסעת?" },
      options: [ { en: "To Eilat", ru: "В Эйла́т", he: "לאילת" }, { en: "To Jerusalem", ru: "В Иерусали́м", he: "לירושלים" }, { en: "To Haifa", ru: "В Ха́йфу", he: "לחיפה" } ],
      answer: 2 },
    { q: { en: "Where is the man from?", ru: "Отку́да мужчи́на?", he: "מאיפה האיש?" },
      options: [ { en: "From Russia", ru: "Из Росси́и", he: "מרוסיה" }, { en: "From Riga", ru: "Из Ри́ги", he: "מריגה" }, { en: "From Haifa", ru: "Из Ха́йфы", he: "מחיפה" } ],
      answer: 1 },
    { q: { en: "What do they do on the way?", ru: "Что они́ де́лают в доро́ге?", he: "מה הם עושים בדרך?" },
      options: [ { en: "They talk", ru: "Разгова́ривают", he: "מדברים" }, { en: "They sleep", ru: "Спят", he: "ישנים" }, { en: "They eat", ru: "Едя́т", he: "אוכלים" } ],
      answer: 0 }
  ]
});

LS_DATA.stories.push({
  id: "s_job_interview", level: 3, emoji: "💼",
  title: { en: "The Job Interview", ru: "Собесе́дование", he: "ראיון עבודה" },
  sentences: [
    { en: "Irina had a job interview at a big hotel.", ru: "У Ири́ны бы́ло собесе́дование в большо́й гости́нице.", he: "לאירינה היה ראיון עבודה במלון גדול.", emoji: "💼" },
    { en: "She wanted to work as a receptionist.", ru: "Она́ хоте́ла рабо́тать администра́тором.", he: "היא רצתה לעבוד בקבלה.", emoji: "🛎️" },
    { en: "The night before, she could not sleep at all.", ru: "Накану́не но́чью она́ совсе́м не могла́ спать.", he: "בלילה שלפני היא בכלל לא הצליחה לישון.", emoji: "🌙" },
    { en: "In the morning, she put on her best dress.", ru: "У́тром она́ наде́ла своё лу́чшее пла́тье.", he: "בבוקר היא לבשה את השמלה הכי יפה שלה.", emoji: "👗" },
    { en: "She arrived twenty minutes early.", ru: "Она́ пришла́ на два́дцать мину́т ра́ньше.", he: "היא הגיעה עשרים דקות מוקדם.", emoji: "⏰" },
    { en: "The manager asked her many questions.", ru: "Ме́неджер задава́л ей мно́го вопро́сов.", he: "המנהל שאל אותה הרבה שאלות.", emoji: "❓" },
    { en: "Then he asked: \"Do you speak English?\"", ru: "Пото́м он спроси́л: «Вы говори́те по-англи́йски?»", he: "ואז הוא שאל: \"את מדברת אנגלית?\"", emoji: "🗣️" },
    { en: "Irina was nervous, but she answered in English.", ru: "Ири́на волнова́лась, но отве́тила по-англи́йски.", he: "אירינה הייתה לחוצה, אבל היא ענתה באנגלית.", emoji: "😬" },
    { en: "She also said that she speaks Hebrew and Russian.", ru: "Она́ та́кже сказа́ла, что говори́т на иври́те и по-ру́сски.", he: "היא גם אמרה שהיא מדברת עברית ורוסית.", emoji: "🌍" },
    { en: "The manager smiled: \"Three languages! That is great for a hotel.\"", ru: "Ме́неджер улыбну́лся: «Три языка́! Для гости́ницы э́то прекра́сно».", he: "המנהל חייך: \"שלוש שפות! זה מצוין למלון.\"", emoji: "😊" },
    { en: "Two days later, Irina got a phone call.", ru: "Че́рез два дня Ири́не позвони́ли.", he: "יומיים אחר כך התקשרו לאירינה.", emoji: "📞" },
    { en: "She got the job!", ru: "Её взя́ли на рабо́ту!", he: "היא התקבלה לעבודה!", emoji: "🎉" }
  ],
  questions: [
    { q: { en: "Where was the interview?", ru: "Где бы́ло собесе́дование?", he: "איפה היה הראיון?" },
      options: [ { en: "At a bank", ru: "В ба́нке", he: "בבנק" }, { en: "At a hotel", ru: "В гости́нице", he: "במלון" }, { en: "At a school", ru: "В шко́ле", he: "בבית ספר" } ],
      answer: 1 },
    { q: { en: "How early did she arrive?", ru: "На ско́лько ра́ньше она́ пришла́?", he: "כמה מוקדם היא הגיעה?" },
      options: [ { en: "Five minutes early", ru: "На пять мину́т", he: "חמש דקות" }, { en: "One hour early", ru: "На час", he: "שעה" }, { en: "Twenty minutes early", ru: "На два́дцать мину́т", he: "עשרים דקות" } ],
      answer: 2 },
    { q: { en: "Why did the manager like her?", ru: "Почему́ она́ понра́вилась ме́неджеру?", he: "למה היא מצאה חן בעיני המנהל?" },
      options: [ { en: "She speaks three languages", ru: "Она́ говори́т на трёх языка́х", he: "היא מדברת שלוש שפות" }, { en: "She has a nice dress", ru: "У неё краси́вое пла́тье", he: "יש לה שמלה יפה" }, { en: "She lives near the hotel", ru: "Она́ живёт ря́дом с гости́ницей", he: "היא גרה ליד המלון" } ],
      answer: 0 }
  ]
});

LS_DATA.stories.push({
  id: "s_wedding", level: 3, emoji: "💍",
  title: { en: "The Wedding", ru: "Сва́дьба", he: "החתונה" },
  sentences: [
    { en: "Last week, my cousin Yael got married.", ru: "На про́шлой неде́ле моя́ двою́родная сестра́ Яэ́ль вы́шла за́муж.", he: "בשבוע שעבר בת הדודה שלי יעל התחתנה.", emoji: "💍" },
    { en: "The wedding was in a garden near the sea.", ru: "Сва́дьба была́ в саду́ у мо́ря.", he: "החתונה הייתה בגן אירועים ליד הים.", emoji: "🌊" },
    { en: "There were almost three hundred guests.", ru: "Там бы́ло почти́ три́ста госте́й.", he: "היו שם כמעט שלוש מאות אורחים.", emoji: "👥" },
    { en: "Yael wore a long white dress.", ru: "На Яэ́ли бы́ло дли́нное бе́лое пла́тье.", he: "יעל לבשה שמלה לבנה וארוכה.", emoji: "👰" },
    { en: "The groom, Amir, cried when he saw her.", ru: "Жени́х, Ами́р, запла́кал, когда́ уви́дел её.", he: "החתן, אמיר, בכה כשהוא ראה אותה.", emoji: "🤵" },
    { en: "Under the chuppah, he broke a glass, and everyone shouted: \"Mazal tov!\"", ru: "Под ху́пой он разби́л стака́н, и все закрича́ли: «Мазл тов!»", he: "מתחת לחופה הוא שבר כוס, וכולם צעקו: \"מזל טוב!\"", emoji: "🥂" },
    { en: "Then the music started and the dancing began.", ru: "Пото́м заигра́ла му́зыка, и начали́сь та́нцы.", he: "ואז התחילו המוזיקה והריקודים.", emoji: "💃" },
    { en: "My grandmother danced more than anyone.", ru: "Моя́ ба́бушка танцева́ла бо́льше всех.", he: "סבתא שלי רקדה יותר מכולם.", emoji: "👵" },
    { en: "The food was delicious, but there was too much of it.", ru: "Еда́ была́ вку́сной, но её бы́ло сли́шком мно́го.", he: "האוכל היה טעים, אבל היה ממנו יותר מדי.", emoji: "🍽️" },
    { en: "We came home at three in the morning.", ru: "Мы верну́лись домо́й в три часа́ но́чи.", he: "חזרנו הביתה בשלוש בלילה.", emoji: "🌙" },
    { en: "My feet hurt, but my heart was happy.", ru: "Но́ги боле́ли, но на душе́ бы́ло ра́достно.", he: "כאבו לי הרגליים, אבל הלב היה שמח.", emoji: "❤️" }
  ],
  questions: [
    { q: { en: "Where was the wedding?", ru: "Где была́ сва́дьба?", he: "איפה הייתה החתונה?" },
      options: [ { en: "In a hotel", ru: "В гости́нице", he: "במלון" }, { en: "In a garden near the sea", ru: "В саду́ у мо́ря", he: "בגן ליד הים" }, { en: "In a restaurant", ru: "В рестора́не", he: "במסעדה" } ],
      answer: 1 },
    { q: { en: "What did the groom do when he saw Yael?", ru: "Что сде́лал жени́х, когда́ уви́дел Яэ́ль?", he: "מה החתן עשה כשהוא ראה את יעל?" },
      options: [ { en: "He laughed", ru: "Засмея́лся", he: "צחק" }, { en: "He sang", ru: "Запе́л", he: "שר" }, { en: "He cried", ru: "Запла́кал", he: "בכה" } ],
      answer: 2 },
    { q: { en: "Who danced more than anyone?", ru: "Кто танцева́л бо́льше всех?", he: "מי רקד יותר מכולם?" },
      options: [ { en: "The grandmother", ru: "Ба́бушка", he: "סבתא" }, { en: "The groom", ru: "Жени́х", he: "החתן" }, { en: "Yael", ru: "Яэ́ль", he: "יעל" } ],
      answer: 0 }
  ]
});

LS_DATA.stories.push({
  id: "s_borscht", level: 3, emoji: "🍲",
  title: { en: "Borscht with Grandma", ru: "Борщ с ба́бушкой", he: "בורשט עם סבתא" },
  sentences: [
    { en: "Every winter, Grandma Valya makes borscht.", ru: "Ка́ждую зи́му ба́бушка Ва́ля ва́рит борщ.", he: "כל חורף סבתא ואליה מבשלת בורשט.", emoji: "🍲" },
    { en: "This year, she decided to teach her grandson Noam.", ru: "В э́том году́ она́ реши́ла научи́ть вну́ка Ноа́ма.", he: "השנה היא החליטה ללמד את הנכד שלה, נועם.", emoji: "👵" },
    { en: "Noam washed the beets, potatoes, carrots, and cabbage.", ru: "Ноа́м помы́л свёклу, карто́шку, морко́вку и капу́сту.", he: "נועם שטף סלק, תפוחי אדמה, גזר וכרוב.", emoji: "🥕" },
    { en: "Grandma showed him how to cut the vegetables.", ru: "Ба́бушка показа́ла ему́, как ре́зать о́вощи.", he: "סבתא הראתה לו איך לחתוך את הירקות.", emoji: "🔪" },
    { en: "\"Small pieces, not big ones!\" she said.", ru: "«Ма́ленькими кусо́чками, не больши́ми!» — сказа́ла она́.", he: "\"חתיכות קטנות, לא גדולות!\" היא אמרה.", emoji: "☝️" },
    { en: "First they cooked the meat for a whole hour.", ru: "Снача́ла они́ ва́рили мя́со це́лый час.", he: "קודם הם בישלו את הבשר שעה שלמה.", emoji: "🥩" },
    { en: "Then they added the vegetables one by one.", ru: "Пото́м они́ доба́вили о́вощи по о́череди.", he: "אחר כך הם הוסיפו את הירקות אחד אחרי השני.", emoji: "➕" },
    { en: "Noam asked: \"How much salt?\"", ru: "Ноа́м спроси́л: «Ско́лько со́ли?»", he: "נועם שאל: \"כמה מלח?\"", emoji: "🧂" },
    { en: "Grandma laughed: \"I never measure. I just know.\"", ru: "Ба́бушка засмея́лась: «Я никогда́ не ме́ряю. Я про́сто зна́ю».", he: "סבתא צחקה: \"אני אף פעם לא מודדת. אני פשוט יודעת.\"", emoji: "😄" },
    { en: "Two hours later, the borscht was red and beautiful.", ru: "Че́рез два часа́ борщ был кра́сный и краси́вый.", he: "אחרי שעתיים הבורשט היה אדום ויפה.", emoji: "❤️" },
    { en: "They ate it with sour cream and black bread.", ru: "Они́ е́ли его́ со смета́ной и чёрным хле́бом.", he: "הם אכלו אותו עם שמנת חמוצה ולחם שחור.", emoji: "🍞" },
    { en: "Noam said it was the best borscht in the world.", ru: "Ноа́м сказа́л, что э́то лу́чший борщ на све́те.", he: "נועם אמר שזה הבורשט הכי טוב בעולם.", emoji: "🏆" }
  ],
  questions: [
    { q: { en: "What did Noam wash?", ru: "Что помы́л Ноа́м?", he: "מה נועם שטף?" },
      options: [ { en: "The dishes", ru: "Посу́ду", he: "את הכלים" }, { en: "The vegetables", ru: "О́вощи", he: "את הירקות" }, { en: "The floor", ru: "Пол", he: "את הרצפה" } ],
      answer: 1 },
    { q: { en: "How does Grandma know how much salt to use?", ru: "Как ба́бушка зна́ет, ско́лько класть со́ли?", he: "איך סבתא יודעת כמה מלח לשים?" },
      options: [ { en: "She reads a recipe", ru: "Она́ чита́ет реце́пт", he: "היא קוראת מתכון" }, { en: "She asks Noam", ru: "Она́ спра́шивает Ноа́ма", he: "היא שואלת את נועם" }, { en: "She just knows", ru: "Она́ про́сто зна́ет", he: "היא פשוט יודעת" } ],
      answer: 2 },
    { q: { en: "What did they eat the borscht with?", ru: "С чем они́ е́ли борщ?", he: "עם מה הם אכלו את הבורשט?" },
      options: [ { en: "With sour cream and black bread", ru: "Со смета́ной и чёрным хле́бом", he: "עם שמנת חמוצה ולחם שחור" }, { en: "With rice", ru: "С ри́сом", he: "עם אורז" }, { en: "With cheese", ru: "С сы́ром", he: "עם גבינה" } ],
      answer: 0 }
  ]
});

LS_DATA.stories.push({
  id: "s_jerusalem", level: 3, emoji: "🏛️",
  title: { en: "A Day in Jerusalem", ru: "День в Иерусали́ме", he: "יום בירושלים" },
  sentences: [
    { en: "Tanya's friend Lisa came from Berlin to Israel.", ru: "По́друга Та́ни, Ли́за, прие́хала из Берли́на в Изра́иль.", he: "החברה של טניה, ליזה, הגיעה מברלין לישראל.", emoji: "✈️" },
    { en: "On Friday, they took the train to Jerusalem.", ru: "В пя́тницу они́ пое́хали на по́езде в Иерусали́м.", he: "ביום שישי הן נסעו ברכבת לירושלים.", emoji: "🚆" },
    { en: "First they walked in the Old City.", ru: "Снача́ла они́ гуля́ли по Ста́рому го́роду.", he: "קודם הן טיילו בעיר העתיקה.", emoji: "🏛️" },
    { en: "The narrow streets were full of people and smells.", ru: "У́зкие у́лицы бы́ли полны́ люде́й и за́пахов.", he: "הסמטאות הצרות היו מלאות אנשים וריחות.", emoji: "👃" },
    { en: "They stood at the Western Wall, and Lisa put a note between the stones.", ru: "Они́ постоя́ли у Стены́ Пла́ча, и Ли́за положи́ла запи́ску ме́жду камня́ми.", he: "הן עמדו ליד הכותל, וליזה שמה פתק בין האבנים.", emoji: "🧱" },
    { en: "Then they went to the Mahane Yehuda market.", ru: "Пото́м они́ пошли́ на ры́нок Махане́ Иегу́да.", he: "אחר כך הן הלכו לשוק מחנה יהודה.", emoji: "🛒" },
    { en: "Before Shabbat, the market was very loud and busy.", ru: "Пе́ред суббо́той на ры́нке бы́ло о́чень шу́мно и лю́дно.", he: "לפני שבת השוק היה רועש ועמוס מאוד.", emoji: "🔊" },
    { en: "They bought warm challah, olives, and sweet halva.", ru: "Они́ купи́ли тёплую ха́лу, масли́ны и сла́дкую халву́.", he: "הן קנו חלה חמה, זיתים וחלבה מתוקה.", emoji: "🥖" },
    { en: "In the evening, the city became very quiet.", ru: "Ве́чером го́род стал о́чень ти́хим.", he: "בערב העיר נהייתה שקטה מאוד.", emoji: "🌇" },
    { en: "The stones of the houses looked golden in the sunset.", ru: "На зака́те ка́мни домо́в каза́лись золоты́ми.", he: "בשקיעה אבני הבתים נראו זהובות.", emoji: "✨" },
    { en: "Lisa said: \"Now I understand why people love this city.\"", ru: "Ли́за сказа́ла: «Тепе́рь я понима́ю, почему́ лю́ди лю́бят э́тот го́род».", he: "ליזה אמרה: \"עכשיו אני מבינה למה אנשים אוהבים את העיר הזאת.\"", emoji: "❤️" }
  ],
  questions: [
    { q: { en: "How did they get to Jerusalem?", ru: "Как они́ добрали́сь до Иерусали́ма?", he: "איך הן הגיעו לירושלים?" },
      options: [ { en: "By car", ru: "На маши́не", he: "במכונית" }, { en: "By bus", ru: "На авто́бусе", he: "באוטובוס" }, { en: "By train", ru: "На по́езде", he: "ברכבת" } ],
      answer: 2 },
    { q: { en: "What did Lisa put between the stones?", ru: "Что Ли́за положи́ла ме́жду камня́ми?", he: "מה ליזה שמה בין האבנים?" },
      options: [ { en: "A coin", ru: "Моне́ту", he: "מטבע" }, { en: "A note", ru: "Запи́ску", he: "פתק" }, { en: "A flower", ru: "Цвето́к", he: "פרח" } ],
      answer: 1 },
    { q: { en: "What did they buy at the market?", ru: "Что они́ купи́ли на ры́нке?", he: "מה הן קנו בשוק?" },
      options: [ { en: "Challah, olives, and halva", ru: "Ха́лу, масли́ны и халву́", he: "חלה, זיתים וחלבה" }, { en: "Fish and rice", ru: "Ры́бу и рис", he: "דגים ואורז" }, { en: "Clothes", ru: "Оде́жду", he: "בגדים" } ],
      answer: 0 }
  ]
});
