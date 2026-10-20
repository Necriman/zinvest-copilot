// Huquqiy sahifalar o‘zbek tilida. Tuzilishi docs.ru.js bilan bir xil.
export default {
  privacy: {
    title: 'Maxfiylik siyosati',
    intro:
      'Zinvest qanday ma’lumotlarni yig‘ishi, nima uchun, qayerda saqlashi va ularni qanday olish yoki o‘chirish mumkinligi. Biz faqat xizmat uchun kerakli narsani yig‘amiz, ma’lumotlarni sotmaymiz va reklama ko‘rsatmaymiz.',
    sections: [
      {
        h: 'Qanday ma’lumotlarni yig‘amiz',
        list: [
          'Hisob: ism, familiya (ixtiyoriy), email va parol — faqat xesh ko‘rinishida, asl parolni biz ko‘rmaymiz. Google orqali kirsangiz — Google hisobingiz identifikatori, undagi ism va email.',
          'Sozlamalar: til, mavzu, interfeys rangi, avatar (yuklasangiz).',
          'O‘qish: boshlang‘ich savollarga javoblar (istalganini o‘tkazib yuborish mumkin), test natijalari, darslar bo‘yicha natija, kunlar seriyasi, tangalar, qaydlar.',
          '«Mening startapim» bo‘limi (foydalansangiz): loyiha, jamoa, mahsulotlar va moliya haqida kiritganingiz, bozor tekshiruvi javoblari va natijasi.',
          'Sun’iy intellektga so‘rovlar: Zinvest AI’ga bergan savollaringiz va javob uchun kerakli kontekst (masalan, dars yoki startap ma’lumotlari).',
          'Hamjamiyat: postlar va asoschi profili, agar ularni e’lon qilsangiz.',
          'Telegram-bot (ulasangiz): Telegram ID’ingiz va botga yuborganlaringiz.',
          'Xavfsizlik: IP-manzil, qurilmaning tasodifiy identifikatori, brauzer va qurilma nomi, kirish vaqtlari, muvaffaqiyatsiz kirish urinishlari.',
        ],
      },
      {
        h: 'Nimalarni yig‘maymiz',
        p: ['Tug‘ilgan sana, pasport ma’lumotlari, bank kartasi ma’lumotlari. Zinvest’da reklama, reklama trekerlari va uchinchi tomon analitikasi yo‘q.'],
      },
      {
        h: 'Nima uchun kerak',
        list: [
          'Hisob yaratish, sizni kiritish va hisobni buzib kirishdan himoya qilish uchun.',
          'O‘quv rejasini tuzish, natija va qaydlarni saqlash uchun.',
          'Sun’iy intellekt savolga javob berishi va startap uchun bozorni tekshirishi uchun.',
          'Xizmat xatlarini yuborish uchun: kirish kodlari, emailni tasdiqlash, parolni tiklash.',
        ],
      },
      {
        h: 'Asoslar',
        p: [
          'Ro‘yxatdan o‘tishdagi roziligingiz va xizmatdan so‘raganingizni bajarish. Xavfsizlik ma’lumotlari (IP, kirish urinishlari) hisobingiz va xizmatni himoya qilish uchun ishlanadi. Rozilikni hisobni o‘chirib qaytarib olishingiz mumkin.',
        ],
      },
      {
        h: 'Sun’iy intellekt',
        p: [
          'Zinvest AI javoblari, o‘quv rejasi va bozor tekshiruvini Google Gemini modeli tayyorlaydi: savolingiz va kerakli kontekst Google API’ga yuboriladi. Bozor tekshiruvi Google Qidiruvda ma’lumot izlaydi. Sun’iy intellektga parol, karta raqami va boshqa nozik ma’lumotlarni yozmang. Javoblar noaniq bo‘lishi mumkin.',
        ],
      },
      {
        h: 'Ma’lumotlarni yana kim ishlaydi',
        list: [
          'Vercel — sayt va server xostingi.',
          'Supabase — ma’lumotlar bazasi; Amazon Web Services serverlari, Mumbay (Hindiston).',
          'Google — Google orqali kirish, Gemini modeli, bozor tekshiruvi uchun Google Qidiruv va Google Fonts shriftlari: brauzer ularni Google serverlaridan yuklaydi, shuning uchun Google IP-manzilingizni ko‘radi.',
          'Kodli xatlarni yetkazadigan pochta xizmati.',
          'Telegram — faqat botdan foydalansangiz.',
        ],
        p: ['Ular ma’lumotlarni bizning topshirig‘imiz bilan va faqat Zinvest ishlashi uchun ishlaydi. Biz ma’lumotlarni sotmaymiz va reklama uchun bermaymiz.'],
      },
      {
        h: 'Ma’lumotlar qayerda saqlanadi',
        p: [
          'Ma’lumotlar O‘zbekistondan tashqaridagi serverlarda (Hindiston) saqlanadi, sayt esa Vercel’ning global tarmog‘i orqali yetkaziladi. Ro‘yxatdan o‘tib, siz bunday transchegaraviy uzatishga rozilik bildirasiz.',
        ],
      },
      {
        h: 'Qancha saqlaymiz',
        p: [
          'Hisob ma’lumotlari — hisob mavjud ekan. Kirish kodlari 10 daqiqa amal qiladi. Xavfsizlik jurnallari hisoblarni himoya qilish uchun kerakli muddat saqlanadi. Hisob o‘chirilganda ma’lumotlar o‘chiriladi, qonun saqlashni talab qiladiganlaridan tashqari.',
        ],
      },
      {
        h: 'Huquqlaringiz',
        list: [
          'Ma’lumotlaringiz nusxasini olish: Sozlamalar → Maxfiylik va xavfsizlik → Ma’lumotlarimni yuklab olish.',
          'Tuzatish: Sozlamalar → Profil va Hisob.',
          'Hisob va barcha ma’lumotlarni o‘chirish: Sozlamalar → Maxfiylik va xavfsizlik → Hisobni o‘chirish. Kira olmasangiz, hisob ro‘yxatdan o‘tgan emaildan «Aloqa» bo‘limidagi manzilga yozing.',
          'Rozilikni qaytarib olish va shaxsga doir ma’lumotlarni himoya qilish bo‘yicha vakolatli organga shikoyat qilish.',
        ],
      },
      {
        h: 'Bolalar',
        p: [
          'Zinvest 16 yoshdan katta odamlar uchun. 13 yoshdan 15 yoshgacha faqat ota-ona yoki vasiy ruxsati bilan foydalanish mumkin; 13 yoshdan kichiklar foydalana olmaydi. Ota-ona yoki vasiy bizga yozib, bolaning hisobini o‘chirishni so‘rashi mumkin. Yosh haqida faqat «ha» deb so‘raymiz, tug‘ilgan sanani saqlamaymiz.',
        ],
      },
      {
        h: 'Xavfsizlik',
        p: [
          'Ulanish shifrlanadi (HTTPS), parollar xesh ko‘rinishida saqlanadi, kirish xatdagi kod bilan tasdiqlanadi, bir necha muvaffaqiyatsiz urinishdan keyin kirish vaqtincha bloklanadi. Admin-panelga kirish huquqi bor xodimlar ikki bosqichli autentifikatsiya bilan kiradi, ularning harakatlari jurnalga yoziladi.',
        ],
      },
      {
        h: 'O‘zgarishlar',
        p: ['Siyosat o‘zgarsa, sahifa tepasidagi sanani yangilaymiz va muhim o‘zgarishlar haqida ilovada xabar beramiz.'],
      },
    ],
  },

  terms: {
    title: 'Foydalanish shartlari',
    intro: 'Zinvest’dan foydalanish qoidalari. Ro‘yxatdan o‘tib yoki Google orqali kirib, siz ularni qabul qilasiz. Rozi bo‘lmasangiz, xizmatdan foydalanmang.',
    sections: [
      {
        h: 'Zinvest nima',
        p: ['Zinvest — ta’lim platformasi: moliya bo‘yicha darslar, testlar, qaydlar, sun’iy intellekt yordamchisi va startap uchun ish maydoni.'],
      },
      {
        h: 'Moliyaviy maslahat emas',
        p: [
          'Zinvest’dagi hamma narsa — darslar, sun’iy intellekt javoblari, bozor tekshiruvi — ta’limiy xarakterga ega va investitsiya, moliyaviy, soliq yoki huquqiy maslahat emas. Pul bo‘yicha qarorlarni o‘zingiz qabul qilasiz. Sun’iy intellekt xato qilishi mumkin: muhim xulosalarni tekshiring.',
        ],
      },
      {
        h: 'Kim foydalanishi mumkin',
        p: ['16 yoshdan katta odamlar yoki 13–15 yoshlilar ota-ona yoki vasiy ruxsati bilan. 13 yoshdan kichiklar Zinvest’dan foydalana olmaydi.'],
      },
      {
        h: 'Hisob',
        list: [
          'Haqiqiy email kiriting — kirish kodlari unga keladi.',
          'Hisobga kirishni boshqalarga bermang va begona kirishni sezsangiz, bizga xabar bering.',
          'Bir odam — bitta hisob.',
        ],
      },
      {
        h: 'Narx',
        p: [
          'Hozir Zinvest bepul, sun’iy intellekt uchun oylik so‘rovlar limiti bor, u «Tariflar» bo‘limida ko‘rsatilgan. Yashirin to‘lovlar yo‘q. Pullik funksiyalar paydo bo‘lsa, narx xariddan oldin ko‘rsatiladi va sizning aniq harakatingizsiz hech narsa yechilmaydi.',
        ],
      },
      {
        h: 'Nima qilish mumkin emas',
        list: [
          'Noqonuniy, haqoratli, firibgarlik mazmunidagi kontent yoki spam joylash.',
          'Boshqa odam yoki kompaniya nomidan o‘zini ko‘rsatish.',
          'Xizmatni buzish, limitlarni chetlab o‘tish, botlar bilan ma’lumotlarni ommaviy yuklab olish.',
          'Sun’iy intellektdan zararli kontent yaratish uchun foydalanish.',
        ],
      },
      {
        h: 'Sizning kontentingiz',
        p: [
          'Qaydlar, postlar va startap ma’lumotlari sizga tegishli. Siz ularni xizmat ishlashi uchun kerakli tarzda saqlash va ko‘rsatishga ruxsat berasiz (masalan, hamjamiyatdagi post boshqalarga ko‘rinadi). Ushbu qoidalarni buzgan postlarni moderatorlar yashirishi mumkin.',
        ],
      },
      {
        h: 'Bizning kontent',
        p: [
          'Zinvest darslari, matnlari, ayiq-maskoti, rasmlari va kodi mualliflik huquqi bilan himoyalangan. Ulardan shaxsiy o‘qish uchun foydalanish mumkin, lekin ruxsatsiz nusxalash va tarqatish mumkin emas.',
        ],
      },
      {
        h: 'Bloklash va o‘chirish',
        p: ['Hisobni istalgan vaqtda sozlamalarda o‘chirishingiz mumkin. Ushbu shartlarni buzgan hisobni cheklashimiz yoki bloklashimiz mumkin.'],
      },
      {
        h: 'Javobgarlik',
        p: [
          'Xizmat «boricha» taqdim etiladi. Biz uning uzluksiz va xatosiz ishlashiga harakat qilamiz, lekin buni kafolatlamaymiz va qonun ruxsat bergan darajada materiallar va sun’iy intellekt javoblari asosida qabul qilingan qarorlar uchun javob bermaymiz.',
        ],
      },
      {
        h: 'Shartlarning o‘zgarishi',
        p: ['O‘zgarishlar haqida ilovada xabar beramiz. O‘zgarishlardan keyin Zinvest’dan foydalanishni davom ettirsangiz, yangi tahrirni qabul qilgan bo‘lasiz.'],
      },
    ],
  },

  cookies: {
    title: 'Cookie siyosati',
    intro:
      'Zinvest faqat zarur cookie va brauzerning mahalliy xotirasidan foydalanadi — hisobda qolishingiz va sayt sozlamalaringizni eslab qolishi uchun. Reklama va analitika cookie’lari yo‘q, shuning uchun ularga rozilik so‘ramaymiz.',
    sections: [
      {
        h: 'Cookie',
        list: [
          'refresh_token — sizni 7 kungacha hisobda saqlaydi. Uni faqat server o‘qiy oladi (HttpOnly) va u faqat kirish yangilanganda yuboriladi.',
          'g_oauth — Google orqali kirish paytida 10 daqiqa yashaydi va kirishni soxtalashtirishdan himoya qiladi.',
        ],
      },
      {
        h: 'Brauzerning mahalliy xotirasi',
        list: [
          'Til, mavzu va interfeys rangi.',
          'Qurilmaning tasodifiy identifikatori — qurilmalaringiz ro‘yxatini ko‘rsatish va kirishni himoya qilish uchun.',
          'Yig‘ilgan yon panel, qaydlar varag‘i kengligi, ovozli o‘qish va ayiq animatsiyasi.',
          'Yopilgan e’lonlar va eslatmalar.',
        ],
      },
      {
        h: 'Uchinchi tomon xizmatlari',
        p: [
          'Shriftlar Google Fonts’dan yuklanadi: Google IP-manzilingizni ko‘radi, lekin cookie qo‘ymaydi. Google orqali kirish Google sahifasini ochadi, u yerda Google qoidalari amal qiladi.',
        ],
      },
      {
        h: 'Qanday o‘chirish mumkin',
        p: ['Cookie va xotirani brauzer sozlamalarida tozalash mumkin. refresh_token cookie’siz saytni har ochganda qaytadan kirishingiz kerak bo‘ladi.'],
      },
    ],
  },

  refund: {
    title: 'Pulni qaytarish siyosati',
    intro: 'Hozir Zinvest to‘liq bepul: biz to‘lov qabul qilmaymiz va karta ma’lumotlarini saqlamaymiz, shuning uchun qaytariladigan narsa yo‘q.',
    sections: [
      {
        h: 'Pullik funksiyalar paydo bo‘lsa',
        list: [
          'Narx va shartlar to‘lovdan oldin ko‘rsatiladi.',
          'Sizning aniq harakatingizsiz hech narsa yechilmaydi, obunani esa sozlamalarda rasmiylashtirish kabi oson bekor qilish mumkin bo‘ladi.',
          'Pulni qaytarish shartlari birinchi to‘lovdan oldin shu sahifada e’lon qilinadi.',
        ],
      },
      {
        h: 'Savollar',
        p: ['Agar sizdan Zinvest nomidan pul yechilgan deb o‘ylasangiz, bizga yozing — bu biz emasmiz, va biz aniqlashga yordam beramiz.'],
      },
    ],
  },

  licenses: {
    title: 'Litsenziyalar va mualliflik',
    intro: 'Zinvest ochiq dasturiy ta’minot va bepul shriftlar asosida qurilgan. Ularning mualliflariga rahmat.',
    sections: [
      {
        h: 'Shriftlar',
        p: ['Geologica, Nunito, Onest, Plus Jakarta Sans va JetBrains Mono — SIL Open Font License 1.1 litsenziyasi, Google Fonts’dan yuklanadi.'],
      },
      {
        h: 'Ikonkalar',
        p: ['Interfeys ikonkalari Lucide to‘plamiga asoslangan (ISC litsenziyasi).'],
      },
      {
        h: 'Kutubxonalar',
        list: [
          'MIT: Vue, Vue Router, Pinia, Vue I18n, Axios, Tiptap, KaTeX, MathLive, Mermaid, three.js, Vue Flow, lowlight, OverlayScrollbars, splitpanes, qrcode-generator, Tailwind CSS, PyJWT, gunicorn, redis-py, uuid6.',
          'BSD: Django, python-dotenv.',
          'Apache 2.0: Google Gen AI SDK, cryptography.',
          'LGPL: psycopg, LAME (lameenc orqali).',
          'HPND: Pillow.',
        ],
      },
      {
        h: 'Rasmlar',
        p: ['Ayiq-maskot, 3D ikonkalar va rasmlar Zinvest uchun, jumladan generativ vositalar yordamida yaratilgan.'],
      },
    ],
  },
}
