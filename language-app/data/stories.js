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
