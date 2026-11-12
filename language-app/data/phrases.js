window.LS_DATA = window.LS_DATA || {};
LS_DATA.situations = [
  { id: "meet", emoji: "🤝", he: "היכרות", en: "Meeting people", ru: "Знакомство" },
  { id: "smalltalk", emoji: "💬", he: "שיחת חולין", en: "Small talk", ru: "Светская беседа" },
  { id: "cafe", emoji: "☕", he: "בבית קפה", en: "At the café", ru: "В кафе" },
  { id: "shop", emoji: "🛍️", he: "בחנות", en: "Shopping", ru: "В магазине" },
  { id: "directions", emoji: "🧭", he: "הכוונה בדרך", en: "Directions", ru: "Как пройти" },
  { id: "transport", emoji: "🚌", he: "תחבורה", en: "Transport", ru: "Транспорт" },
  { id: "doctor", emoji: "🩺", he: "אצל הרופא", en: "At the doctor", ru: "У врача" },
  { id: "home", emoji: "🏠", he: "בבית", en: "At home", ru: "Дома" },
  { id: "phone", emoji: "📞", he: "בטלפון", en: "On the phone", ru: "По телефону" },
  { id: "time", emoji: "📅", he: "זמן ותוכניות", en: "Time & plans", ru: "Время и планы" },
  { id: "emergency", emoji: "🚨", he: "חירום", en: "Emergency", ru: "Экстренная помощь" },
  { id: "feelings", emoji: "😊", he: "רגשות ודעות", en: "Feelings & opinions", ru: "Чувства и мнения" },
];
LS_DATA.phrases = LS_DATA.phrases || [];

// meet
LS_DATA.phrases.push(
  { id: "meet_01", sit: "meet", level: 1, en: "My name is Anna.", ru: "Меня́ зову́т А́нна.", he: "קוראים לי אנה." },
  { id: "meet_02", sit: "meet", level: 1, en: "What is your name?", ru: "Как вас зову́т?", he: "איך קוראים לך?" },
  { id: "meet_03", sit: "meet", level: 1, en: "Nice to meet you.", ru: "О́чень прия́тно.", he: "נעים מאוד." },
  { id: "meet_04", sit: "meet", level: 1, en: "Where are you from?", ru: "Отку́да вы?", he: "מאיפה אתה?" },
  { id: "meet_05", sit: "meet", level: 1, en: "I am from Israel.", ru: "Я из Изра́иля.", he: "אני מישראל." },
  { id: "meet_06", sit: "meet", level: 2, en: "I live in Tel Aviv.", ru: "Я живу́ в Тель-Ави́ве.", he: "אני גר בתל אביב." },
  { id: "meet_07", sit: "meet", level: 2, en: "How old are you?", ru: "Ско́лько вам лет?", he: "בן כמה אתה?" },
  { id: "meet_08", sit: "meet", level: 2, en: "I am thirty years old.", ru: "Мне три́дцать лет.", he: "אני בן שלושים." },
  { id: "meet_09", sit: "meet", level: 1, en: "Do you speak English?", ru: "Вы говори́те по-англи́йски?", he: "אתה מדבר אנגלית?" },
  { id: "meet_10", sit: "meet", level: 2, en: "I speak a little Russian.", ru: "Я немно́го говорю́ по-ру́сски.", he: "אני מדבר קצת רוסית." },
  { id: "meet_11", sit: "meet", level: 2, en: "This is my friend David.", ru: "Э́то мой друг Дави́д.", he: "זה החבר שלי דוד." },
  { id: "meet_12", sit: "meet", level: 2, en: "What do you do?", ru: "Кем вы рабо́таете?", he: "במה אתה עובד?" },
  { id: "meet_13", sit: "meet", level: 2, en: "I am a teacher.", ru: "Я учи́тель.", he: "אני מורה." },
  { id: "meet_14", sit: "meet", level: 1, en: "See you later!", ru: "До встре́чи!", he: "נתראה!" },
);

// smalltalk
LS_DATA.phrases.push(
  { id: "smalltalk_01", sit: "smalltalk", level: 1, en: "How are you?", ru: "Как дела́?", he: "מה שלומך?" },
  { id: "smalltalk_02", sit: "smalltalk", level: 1, en: "I'm fine, thank you.", ru: "Хорошо́, спаси́бо.", he: "טוב, תודה." },
  { id: "smalltalk_03", sit: "smalltalk", level: 1, en: "And you?", ru: "А у вас?", he: "ואצלך?" },
  { id: "smalltalk_04", sit: "smalltalk", level: 1, en: "What's new?", ru: "Что но́вого?", he: "מה חדש?" },
  { id: "smalltalk_05", sit: "smalltalk", level: 2, en: "Nothing special.", ru: "Ничего́ осо́бенного.", he: "שום דבר מיוחד." },
  { id: "smalltalk_06", sit: "smalltalk", level: 2, en: "The weather is nice today.", ru: "Сего́дня хоро́шая пого́да.", he: "מזג האוויר יפה היום." },
  { id: "smalltalk_07", sit: "smalltalk", level: 1, en: "It's very hot today.", ru: "Сего́дня о́чень жа́рко.", he: "חם מאוד היום." },
  { id: "smalltalk_08", sit: "smalltalk", level: 2, en: "How was your weekend?", ru: "Как прошли́ выходны́е?", he: "איך היה בסוף השבוע?" },
  { id: "smalltalk_09", sit: "smalltalk", level: 1, en: "It was great.", ru: "Бы́ло отли́чно.", he: "היה מעולה." },
  { id: "smalltalk_10", sit: "smalltalk", level: 2, en: "Do you have children?", ru: "У вас есть де́ти?", he: "יש לך ילדים?" },
  { id: "smalltalk_11", sit: "smalltalk", level: 2, en: "I have two children.", ru: "У меня́ дво́е дете́й.", he: "יש לי שני ילדים." },
  { id: "smalltalk_12", sit: "smalltalk", level: 2, en: "What do you like to do?", ru: "Что вы лю́бите де́лать?", he: "מה אתה אוהב לעשות?" },
  { id: "smalltalk_13", sit: "smalltalk", level: 2, en: "I like to read books.", ru: "Я люблю́ чита́ть кни́ги.", he: "אני אוהב לקרוא ספרים." },
  { id: "smalltalk_14", sit: "smalltalk", level: 1, en: "Have a nice day!", ru: "Хоро́шего дня!", he: "יום טוב!" },
);

// cafe
LS_DATA.phrases.push(
  { id: "cafe_01", sit: "cafe", level: 1, en: "A coffee, please.", ru: "Ко́фе, пожа́луйста.", he: "קפה, בבקשה." },
  { id: "cafe_02", sit: "cafe", level: 1, en: "Can I see the menu?", ru: "Мо́жно меню́?", he: "אפשר תפריט?" },
  { id: "cafe_03", sit: "cafe", level: 1, en: "I'd like tea, please.", ru: "Мне чай, пожа́луйста.", he: "אני רוצה תה, בבקשה." },
  { id: "cafe_04", sit: "cafe", level: 2, en: "With milk, no sugar.", ru: "С молоко́м, без са́хара.", he: "עם חלב, בלי סוכר." },
  { id: "cafe_05", sit: "cafe", level: 1, en: "A glass of water, please.", ru: "Стака́н воды́, пожа́луйста.", he: "כוס מים, בבקשה." },
  { id: "cafe_06", sit: "cafe", level: 3, en: "What do you recommend?", ru: "Что вы посове́туете?", he: "מה אתה ממליץ?" },
  { id: "cafe_07", sit: "cafe", level: 2, en: "I'm a vegetarian.", ru: "Я вегетариа́нец.", he: "אני צמחוני." },
  { id: "cafe_08", sit: "cafe", level: 2, en: "Is it very spicy?", ru: "Э́то о́чень о́стро?", he: "זה חריף מאוד?" },
  { id: "cafe_09", sit: "cafe", level: 1, en: "It's very tasty!", ru: "О́чень вку́сно!", he: "טעים מאוד!" },
  { id: "cafe_10", sit: "cafe", level: 1, en: "The check, please.", ru: "Счёт, пожа́луйста.", he: "חשבון, בבקשה." },
  { id: "cafe_11", sit: "cafe", level: 2, en: "Can I pay by card?", ru: "Мо́жно оплати́ть ка́ртой?", he: "אפשר לשלם בכרטיס?" },
  { id: "cafe_12", sit: "cafe", level: 2, en: "Is this table free?", ru: "Э́тот сто́лик свобо́ден?", he: "השולחן הזה פנוי?" },
  { id: "cafe_13", sit: "cafe", level: 2, en: "To go, please.", ru: "С собо́й, пожа́луйста.", he: "לקחת, בבקשה." },
  { id: "cafe_14", sit: "cafe", level: 2, en: "Another coffee, please.", ru: "Ещё оди́н ко́фе, пожа́луйста.", he: "עוד קפה אחד, בבקשה." },
);

// shop
LS_DATA.phrases.push(
  { id: "shop_01", sit: "shop", level: 1, en: "How much does it cost?", ru: "Ско́лько э́то сто́ит?", he: "כמה זה עולה?" },
  { id: "shop_02", sit: "shop", level: 1, en: "It's too expensive.", ru: "Э́то сли́шком до́рого.", he: "זה יקר מדי." },
  { id: "shop_03", sit: "shop", level: 2, en: "Do you have a smaller size?", ru: "У вас есть разме́р поме́ньше?", he: "יש לכם מידה יותר קטנה?" },
  { id: "shop_04", sit: "shop", level: 2, en: "Can I try it on?", ru: "Мо́жно приме́рить?", he: "אפשר למדוד?" },
  { id: "shop_05", sit: "shop", level: 3, en: "Where is the fitting room?", ru: "Где приме́рочная?", he: "איפה תא המדידה?" },
  { id: "shop_06", sit: "shop", level: 2, en: "I'm just looking.", ru: "Я про́сто смотрю́.", he: "אני רק מסתכל." },
  { id: "shop_07", sit: "shop", level: 2, en: "I'll take it.", ru: "Я возьму́ э́то.", he: "אני אקח את זה." },
  { id: "shop_08", sit: "shop", level: 3, en: "Do you have it in black?", ru: "А в чёрном цве́те есть?", he: "יש את זה בשחור?" },
  { id: "shop_09", sit: "shop", level: 1, en: "Where is the milk?", ru: "Где молоко́?", he: "איפה החלב?" },
  { id: "shop_10", sit: "shop", level: 2, en: "I need a bag.", ru: "Мне ну́жен паке́т.", he: "אני צריך שקית." },
  { id: "shop_11", sit: "shop", level: 2, en: "Is there a discount?", ru: "Есть ски́дка?", he: "יש הנחה?" },
  { id: "shop_12", sit: "shop", level: 2, en: "Cash or card?", ru: "Нали́чные и́ли ка́рта?", he: "מזומן או אשראי?" },
  { id: "shop_13", sit: "shop", level: 3, en: "Can I return this?", ru: "Мо́жно э́то верну́ть?", he: "אפשר להחזיר את זה?" },
  { id: "shop_14", sit: "shop", level: 2, en: "When do you close?", ru: "Когда́ вы закрыва́етесь?", he: "מתי אתם סוגרים?" },
);

// directions
LS_DATA.phrases.push(
  { id: "directions_01", sit: "directions", level: 1, en: "Excuse me, where is the train station?", ru: "Извини́те, где вокза́л?", he: "סליחה, איפה תחנת הרכבת?" },
  { id: "directions_02", sit: "directions", level: 1, en: "Is it far?", ru: "Э́то далеко́?", he: "זה רחוק?" },
  { id: "directions_03", sit: "directions", level: 1, en: "It's very close.", ru: "Э́то о́чень бли́зко.", he: "זה קרוב מאוד." },
  { id: "directions_04", sit: "directions", level: 1, en: "Go straight.", ru: "Иди́те пря́мо.", he: "לך ישר." },
  { id: "directions_05", sit: "directions", level: 1, en: "Turn left.", ru: "Поверни́те нале́во.", he: "תפנה שמאלה." },
  { id: "directions_06", sit: "directions", level: 2, en: "Turn right at the corner.", ru: "На углу́ поверни́те напра́во.", he: "בפינה תפנה ימינה." },
  { id: "directions_07", sit: "directions", level: 2, en: "How do I get to the beach?", ru: "Как пройти́ к пля́жу?", he: "איך מגיעים לחוף?" },
  { id: "directions_08", sit: "directions", level: 2, en: "It's on the left.", ru: "Э́то сле́ва.", he: "זה בצד שמאל." },
  { id: "directions_09", sit: "directions", level: 2, en: "I'm lost.", ru: "Я заблуди́лся.", he: "הלכתי לאיבוד." },
  { id: "directions_10", sit: "directions", level: 3, en: "Can you show me on the map?", ru: "Мо́жете показа́ть на ка́рте?", he: "אתה יכול להראות לי במפה?" },
  { id: "directions_11", sit: "directions", level: 2, en: "Is there a pharmacy nearby?", ru: "Ря́дом есть апте́ка?", he: "יש בית מרקחת קרוב?" },
  { id: "directions_12", sit: "directions", level: 2, en: "Next to the bank.", ru: "Ря́дом с ба́нком.", he: "ליד הבנק." },
  { id: "directions_13", sit: "directions", level: 3, en: "About five minutes on foot.", ru: "Мину́т пять пешко́м.", he: "בערך חמש דקות ברגל." },
  { id: "directions_14", sit: "directions", level: 1, en: "Where is the restroom?", ru: "Где туале́т?", he: "איפה השירותים?" },
);

// transport
LS_DATA.phrases.push(
  { id: "transport_01", sit: "transport", level: 1, en: "Where is the bus stop?", ru: "Где авто́бусная остано́вка?", he: "איפה תחנת האוטובוס?" },
  { id: "transport_02", sit: "transport", level: 2, en: "Which bus goes downtown?", ru: "Како́й авто́бус идёт в центр?", he: "איזה אוטובוס נוסע למרכז?" },
  { id: "transport_03", sit: "transport", level: 1, en: "One ticket, please.", ru: "Оди́н биле́т, пожа́луйста.", he: "כרטיס אחד, בבקשה." },
  { id: "transport_04", sit: "transport", level: 1, en: "How much is a ticket?", ru: "Ско́лько сто́ит биле́т?", he: "כמה עולה כרטיס?" },
  { id: "transport_05", sit: "transport", level: 2, en: "When is the next train?", ru: "Когда́ сле́дующий по́езд?", he: "מתי הרכבת הבאה?" },
  { id: "transport_06", sit: "transport", level: 1, en: "To the airport, please.", ru: "В аэропо́рт, пожа́луйста.", he: "לשדה התעופה, בבקשה." },
  { id: "transport_07", sit: "transport", level: 2, en: "Stop here, please.", ru: "Останови́те здесь, пожа́луйста.", he: "תעצור כאן, בבקשה." },
  { id: "transport_08", sit: "transport", level: 2, en: "How long does it take?", ru: "Ско́лько вре́мени е́хать?", he: "כמה זמן הנסיעה?" },
  { id: "transport_09", sit: "transport", level: 2, en: "I need to get off here.", ru: "Мне ну́жно здесь вы́йти.", he: "אני צריך לרדת כאן." },
  { id: "transport_10", sit: "transport", level: 2, en: "Is this seat free?", ru: "Э́то ме́сто свобо́дно?", he: "המקום הזה פנוי?" },
  { id: "transport_11", sit: "transport", level: 2, en: "The bus is late.", ru: "Авто́бус опа́здывает.", he: "האוטובוס מאחר." },
  { id: "transport_12", sit: "transport", level: 3, en: "Where can I get a taxi?", ru: "Где мо́жно взять такси́?", he: "איפה אפשר לתפוס מונית?" },
  { id: "transport_13", sit: "transport", level: 3, en: "Does this train go to Haifa?", ru: "Э́тот по́езд идёт в Ха́йфу?", he: "הרכבת הזאת נוסעת לחיפה?" },
);

// doctor
LS_DATA.phrases.push(
  { id: "doctor_01", sit: "doctor", level: 1, en: "I don't feel well.", ru: "Я пло́хо себя́ чу́вствую.", he: "אני לא מרגיש טוב." },
  { id: "doctor_02", sit: "doctor", level: 1, en: "I have a headache.", ru: "У меня́ боли́т голова́.", he: "כואב לי הראש." },
  { id: "doctor_03", sit: "doctor", level: 1, en: "My stomach hurts.", ru: "У меня́ боли́т живо́т.", he: "כואבת לי הבטן." },
  { id: "doctor_04", sit: "doctor", level: 1, en: "I have a fever.", ru: "У меня́ температу́ра.", he: "יש לי חום." },
  { id: "doctor_05", sit: "doctor", level: 2, en: "I have a cough.", ru: "У меня́ ка́шель.", he: "יש לי שיעול." },
  { id: "doctor_06", sit: "doctor", level: 2, en: "Since yesterday.", ru: "Со вчера́шнего дня.", he: "מאתמול." },
  { id: "doctor_07", sit: "doctor", level: 1, en: "I need a doctor.", ru: "Мне ну́жен врач.", he: "אני צריך רופא." },
  { id: "doctor_08", sit: "doctor", level: 3, en: "I'm allergic to penicillin.", ru: "У меня́ аллерги́я на пеницилли́н.", he: "יש לי אלרגיה לפניצילין." },
  { id: "doctor_09", sit: "doctor", level: 3, en: "Do you take any medicine?", ru: "Вы принима́ете каки́е-нибудь лека́рства?", he: "אתה לוקח תרופות?" },
  { id: "doctor_10", sit: "doctor", level: 3, en: "Take one pill twice a day.", ru: "Принима́йте по одно́й табле́тке два ра́за в день.", he: "קח כדור אחד פעמיים ביום." },
  { id: "doctor_11", sit: "doctor", level: 1, en: "Where does it hurt?", ru: "Где боли́т?", he: "איפה כואב?" },
  { id: "doctor_12", sit: "doctor", level: 2, en: "I need a doctor's appointment.", ru: "Мне ну́жно записа́ться к врачу́.", he: "אני צריך תור לרופא." },
  { id: "doctor_13", sit: "doctor", level: 1, en: "My throat hurts.", ru: "У меня́ боли́т го́рло.", he: "כואב לי הגרון." },
);

// home
LS_DATA.phrases.push(
  { id: "home_01", sit: "home", level: 1, en: "Dinner is ready!", ru: "У́жин гото́в!", he: "ארוחת הערב מוכנה!" },
  { id: "home_02", sit: "home", level: 1, en: "I'm going to sleep.", ru: "Я иду́ спать.", he: "אני הולך לישון." },
  { id: "home_03", sit: "home", level: 1, en: "Good night!", ru: "Споко́йной но́чи!", he: "לילה טוב!" },
  { id: "home_04", sit: "home", level: 1, en: "Good morning!", ru: "До́брое у́тро!", he: "בוקר טוב!" },
  { id: "home_05", sit: "home", level: 1, en: "Where are my keys?", ru: "Где мои́ ключи́?", he: "איפה המפתחות שלי?" },
  { id: "home_06", sit: "home", level: 2, en: "Turn off the light, please.", ru: "Вы́ключи свет, пожа́луйста.", he: "תכבה את האור, בבקשה." },
  { id: "home_07", sit: "home", level: 2, en: "Close the window, please.", ru: "Закро́й окно́, пожа́луйста.", he: "תסגור את החלון, בבקשה." },
  { id: "home_08", sit: "home", level: 1, en: "I'm hungry.", ru: "Я хочу́ есть.", he: "אני רעב." },
  { id: "home_09", sit: "home", level: 2, en: "What's for dinner?", ru: "Что на у́жин?", he: "מה יש לארוחת ערב?" },
  { id: "home_10", sit: "home", level: 2, en: "Can you help me?", ru: "Мо́жешь мне помо́чь?", he: "אתה יכול לעזור לי?" },
  { id: "home_11", sit: "home", level: 1, en: "I'm home!", ru: "Я до́ма!", he: "אני בבית!" },
  { id: "home_12", sit: "home", level: 2, en: "Wash your hands.", ru: "Помо́й ру́ки.", he: "תשטוף ידיים." },
  { id: "home_13", sit: "home", level: 2, en: "Let's watch a movie.", ru: "Дава́й посмо́трим фильм.", he: "בוא נראה סרט." },
  { id: "home_14", sit: "home", level: 3, en: "I'll do the dishes.", ru: "Я помо́ю посу́ду.", he: "אני אשטוף את הכלים." },
);

// phone
LS_DATA.phrases.push(
  { id: "phone_01", sit: "phone", level: 1, en: "Hello?", ru: "Алло́?", he: "הלו?" },
  { id: "phone_02", sit: "phone", level: 1, en: "Who is this?", ru: "Кто э́то?", he: "מי זה?" },
  { id: "phone_03", sit: "phone", level: 2, en: "Can I speak to Dana?", ru: "Мо́жно поговори́ть с Да́ной?", he: "אפשר לדבר עם דנה?" },
  { id: "phone_04", sit: "phone", level: 1, en: "One moment, please.", ru: "Одну́ мину́ту, пожа́луйста.", he: "רגע אחד, בבקשה." },
  { id: "phone_05", sit: "phone", level: 2, en: "I can't hear you well.", ru: "Вас пло́хо слы́шно.", he: "לא שומעים אותך טוב." },
  { id: "phone_06", sit: "phone", level: 2, en: "Please speak more slowly.", ru: "Говори́те, пожа́луйста, ме́дленнее.", he: "תדבר יותר לאט, בבקשה." },
  { id: "phone_07", sit: "phone", level: 2, en: "I'll call you back.", ru: "Я вам перезвоню́.", he: "אני אחזור אליך." },
  { id: "phone_08", sit: "phone", level: 1, en: "Call me tomorrow.", ru: "Позвони́ мне за́втра.", he: "תתקשר אליי מחר." },
  { id: "phone_09", sit: "phone", level: 2, en: "What's your phone number?", ru: "Како́й у вас но́мер телефо́на?", he: "מה מספר הטלפון שלך?" },
  { id: "phone_10", sit: "phone", level: 3, en: "My phone is dying.", ru: "У меня́ сади́тся телефо́н.", he: "הסוללה שלי נגמרת." },
  { id: "phone_11", sit: "phone", level: 3, en: "You have the wrong number.", ru: "Вы оши́блись но́мером.", he: "טעית במספר." },
  { id: "phone_12", sit: "phone", level: 2, en: "Send me a message.", ru: "Напиши́ мне сообще́ние.", he: "תשלח לי הודעה." },
  { id: "phone_13", sit: "phone", level: 2, en: "Please repeat that.", ru: "Повтори́те, пожа́луйста.", he: "תחזור על זה, בבקשה." },
);

// time
LS_DATA.phrases.push(
  { id: "time_01", sit: "time", level: 1, en: "What time is it?", ru: "Кото́рый час?", he: "מה השעה?" },
  { id: "time_02", sit: "time", level: 1, en: "It's three o'clock.", ru: "Сейча́с три часа́.", he: "השעה שלוש." },
  { id: "time_03", sit: "time", level: 2, en: "What are you doing tomorrow?", ru: "Что ты де́лаешь за́втра?", he: "מה אתה עושה מחר?" },
  { id: "time_04", sit: "time", level: 2, en: "Are you free tonight?", ru: "Ты свобо́ден сего́дня ве́чером?", he: "אתה פנוי הערב?" },
  { id: "time_05", sit: "time", level: 2, en: "Let's meet at six.", ru: "Дава́й встре́тимся в шесть.", he: "בוא ניפגש בשש." },
  { id: "time_06", sit: "time", level: 1, en: "I'm busy today.", ru: "Я сего́дня за́нят.", he: "אני עסוק היום." },
  { id: "time_07", sit: "time", level: 2, en: "Maybe next week.", ru: "Мо́жет быть, на сле́дующей неде́ле.", he: "אולי בשבוע הבא." },
  { id: "time_08", sit: "time", level: 3, en: "I'll be there in ten minutes.", ru: "Бу́ду че́рез де́сять мину́т.", he: "אני אגיע בעוד עשר דקות." },
  { id: "time_09", sit: "time", level: 2, en: "Sorry, I'm late.", ru: "Извини́, я опозда́л.", he: "סליחה שאיחרתי." },
  { id: "time_10", sit: "time", level: 2, en: "See you on Sunday.", ru: "Уви́димся в воскресе́нье.", he: "נתראה ביום ראשון." },
  { id: "time_11", sit: "time", level: 1, en: "What day is today?", ru: "Како́й сего́дня день?", he: "איזה יום היום?" },
  { id: "time_12", sit: "time", level: 1, en: "Today is Monday.", ru: "Сего́дня понеде́льник.", he: "היום יום שני." },
  { id: "time_13", sit: "time", level: 2, en: "When does it start?", ru: "Когда́ э́то начина́ется?", he: "מתי זה מתחיל?" },
  { id: "time_14", sit: "time", level: 1, en: "I don't have time.", ru: "У меня́ нет вре́мени.", he: "אין לי זמן." },
);

// emergency
LS_DATA.phrases.push(
  { id: "emergency_01", sit: "emergency", level: 1, en: "Help!", ru: "Помоги́те!", he: "הצילו!" },
  { id: "emergency_02", sit: "emergency", level: 1, en: "Call an ambulance!", ru: "Вы́зовите ско́рую!", he: "תזמינו אמבולנס!" },
  { id: "emergency_03", sit: "emergency", level: 1, en: "Call the police!", ru: "Вы́зовите поли́цию!", he: "תזמינו משטרה!" },
  { id: "emergency_04", sit: "emergency", level: 1, en: "Fire!", ru: "Пожа́р!", he: "שריפה!" },
  { id: "emergency_05", sit: "emergency", level: 1, en: "I need help.", ru: "Мне нужна́ по́мощь.", he: "אני צריך עזרה." },
  { id: "emergency_06", sit: "emergency", level: 2, en: "Someone is hurt.", ru: "Кто́-то ра́нен.", he: "מישהו נפגע." },
  { id: "emergency_07", sit: "emergency", level: 2, en: "I lost my passport.", ru: "Я потеря́л па́спорт.", he: "איבדתי את הדרכון." },
  { id: "emergency_08", sit: "emergency", level: 3, en: "My wallet was stolen.", ru: "У меня́ укра́ли кошелёк.", he: "גנבו לי את הארנק." },
  { id: "emergency_09", sit: "emergency", level: 1, en: "Where is the hospital?", ru: "Где больни́ца?", he: "איפה בית החולים?" },
  { id: "emergency_10", sit: "emergency", level: 2, en: "It's an emergency!", ru: "Э́то сро́чно!", he: "זה מקרה חירום!" },
  { id: "emergency_11", sit: "emergency", level: 1, en: "Are you okay?", ru: "Вы в поря́дке?", he: "אתה בסדר?" },
  { id: "emergency_12", sit: "emergency", level: 2, en: "Don't worry.", ru: "Не волну́йтесь.", he: "אל תדאג." },
  { id: "emergency_13", sit: "emergency", level: 1, en: "Be careful!", ru: "Осторо́жно!", he: "זהירות!" },
);

// feelings
LS_DATA.phrases.push(
  { id: "feelings_01", sit: "feelings", level: 1, en: "I'm very happy.", ru: "Я о́чень рад.", he: "אני מאוד שמח." },
  { id: "feelings_02", sit: "feelings", level: 1, en: "I'm tired.", ru: "Я уста́л.", he: "אני עייף." },
  { id: "feelings_03", sit: "feelings", level: 1, en: "I'm sad.", ru: "Мне гру́стно.", he: "אני עצוב." },
  { id: "feelings_04", sit: "feelings", level: 1, en: "I like it.", ru: "Мне нра́вится.", he: "אני אוהב את זה." },
  { id: "feelings_05", sit: "feelings", level: 1, en: "I don't like it.", ru: "Мне не нра́вится.", he: "אני לא אוהב את זה." },
  { id: "feelings_06", sit: "feelings", level: 2, en: "I think so.", ru: "Ду́маю, да.", he: "אני חושב שכן." },
  { id: "feelings_07", sit: "feelings", level: 2, en: "I don't think so.", ru: "Не ду́маю.", he: "אני לא חושב שכן." },
  { id: "feelings_08", sit: "feelings", level: 2, en: "I agree with you.", ru: "Я с тобо́й согла́сен.", he: "אני מסכים איתך." },
  { id: "feelings_09", sit: "feelings", level: 1, en: "That's a good idea!", ru: "Хоро́шая иде́я!", he: "רעיון טוב!" },
  { id: "feelings_10", sit: "feelings", level: 2, en: "I'm worried.", ru: "Я волну́юсь.", he: "אני דואג." },
  { id: "feelings_11", sit: "feelings", level: 2, en: "What do you think?", ru: "Как ты ду́маешь?", he: "מה אתה חושב?" },
  { id: "feelings_12", sit: "feelings", level: 2, en: "It's not important.", ru: "Э́то не ва́жно.", he: "זה לא חשוב." },
  { id: "feelings_13", sit: "feelings", level: 2, en: "I'm bored.", ru: "Мне ску́чно.", he: "משעמם לי." },
  { id: "feelings_14", sit: "feelings", level: 3, en: "In my opinion, it's great.", ru: "По-мо́ему, э́то здо́рово.", he: "לדעתי, זה מצוין." },
);
