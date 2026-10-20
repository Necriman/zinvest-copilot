"""Authored educational cases; practice does not grant completion rewards.

Each case carries its words in all three languages; the answer is shared, so a
case is graded the same whatever language it was read in.
"""
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from accounts.auth import require_auth
from config import languages
from .models import Unit

CASES = [
    {'id': 'budget-buffer', 'unit': 'finance-fundamentals', 'answer_index': 1, 'text': {
        'en': {'prompt': 'A founder has $4,000 available, fixed costs of $1,800 and variable costs of $700 this month. A $1,200 equipment purchase is planned. How much cash remains after all three costs?',
               'choices': ['$1,500', '$300', '$1,200', '$2,200'],
               'explanation': '4,000 − 1,800 − 700 − 1,200 = 300. The one-off purchase also reduces cash.'},
        'ru': {'prompt': 'У основателя есть $4 000. В этом месяце постоянные расходы — $1 800, переменные — $700, и запланирована покупка оборудования за $1 200. Сколько денег останется после всех трёх трат?',
               'choices': ['$1 500', '$300', '$1 200', '$2 200'],
               'explanation': '4 000 − 1 800 − 700 − 1 200 = 300. Разовая покупка тоже уменьшает деньги на счёте.'},
        'uz': {'prompt': 'Asoschida $4 000 bor. Bu oy doimiy xarajatlar — $1 800, o‘zgaruvchan xarajatlar — $700, va $1 200 lik uskuna xaridi rejalashtirilgan. Uchala xarajatdan keyin qancha pul qoladi?',
               'choices': ['$1 500', '$300', '$1 200', '$2 200'],
               'explanation': '4 000 − 1 800 − 700 − 1 200 = 300. Bir martalik xarid ham pulni kamaytiradi.'},
    }},
    {'id': 'compound-return', 'unit': 'investing-basics', 'answer_index': 1, 'text': {
        'en': {'prompt': 'In a hypothetical example, $1,000 grows by 10% in year one and falls by 10% in year two. No fees or cash flows apply. What is the final value?',
               'choices': ['$1,000', '$990', '$1,010', '$900'],
               'explanation': '1,000 × 1.10 × 0.90 = 990. Equal percentage gains and losses do not cancel because the base changes.'},
        'ru': {'prompt': 'Условный пример: $1 000 в первый год выросли на 10%, а во второй упали на 10%. Комиссий и пополнений нет. Какая сумма в итоге?',
               'choices': ['$1 000', '$990', '$1 010', '$900'],
               'explanation': '1 000 × 1,10 × 0,90 = 990. Одинаковые проценты роста и падения не компенсируют друг друга: меняется база.'},
        'uz': {'prompt': 'Shartli misol: $1 000 birinchi yili 10% o‘sdi, ikkinchi yili 10% tushdi. Komissiya va qo‘shimcha pul yo‘q. Oxirida qancha bo‘ladi?',
               'choices': ['$1 000', '$990', '$1 010', '$900'],
               'explanation': '1 000 × 1,10 × 0,90 = 990. Bir xil foizdagi o‘sish va tushish bir-birini qoplamaydi: asos o‘zgaradi.'},
    }},
    {'id': 'break-even', 'unit': 'financial-analysis', 'answer_index': 2, 'text': {
        'en': {'prompt': 'A product sells for $40 and costs $25 per unit to deliver. Fixed monthly costs are $3,000. Assuming all units sell and no other costs, how many units cover all costs?',
               'choices': ['75', '120', '200', '300'],
               'explanation': 'Each unit contributes $15. Break-even is 3,000 ÷ 15 = 200 units.'},
        'ru': {'prompt': 'Товар продаётся за $40, а его поставка стоит $25 за штуку. Постоянные расходы — $3 000 в месяц. Если продаётся всё и других затрат нет, сколько штук покроют все расходы?',
               'choices': ['75', '120', '200', '300'],
               'explanation': 'Каждая штука приносит $15. Точка безубыточности: 3 000 ÷ 15 = 200 штук.'},
        'uz': {'prompt': 'Mahsulot $40 ga sotiladi, bir donasini yetkazish $25 turadi. Oylik doimiy xarajatlar — $3 000. Hammasi sotilsa va boshqa xarajat bo‘lmasa, nechta dona barcha xarajatlarni qoplaydi?',
               'choices': ['75', '120', '200', '300'],
               'explanation': 'Har bir dona $15 keltiradi. Zararsizlik nuqtasi: 3 000 ÷ 15 = 200 dona.'},
    }},
    {'id': 'runway-scenario', 'unit': 'financial-analysis', 'answer_index': 1, 'text': {
        'en': {'prompt': 'A startup has $60,000 cash. Monthly cash receipts are $8,000 and cash payments are $18,000. With no changes or financing, what is its approximate runway?',
               'choices': ['3.3 months', '6 months', '7.5 months', '10 months'],
               'explanation': 'Monthly net cash burn is 18,000 − 8,000 = 10,000. Runway is 60,000 ÷ 10,000 = 6 months.'},
        'ru': {'prompt': 'У стартапа $60 000. Каждый месяц поступает $8 000, а уходит $18 000. Если ничего не менять и не привлекать деньги, на сколько примерно хватит запаса?',
               'choices': ['3,3 месяца', '6 месяцев', '7,5 месяца', '10 месяцев'],
               'explanation': 'Чистый отток в месяц: 18 000 − 8 000 = 10 000. Запас: 60 000 ÷ 10 000 = 6 месяцев.'},
        'uz': {'prompt': 'Startapda $60 000 bor. Har oy $8 000 tushadi va $18 000 chiqadi. Hech narsa o‘zgarmasa va yangi pul jalb qilinmasa, zaxira taxminan necha oyga yetadi?',
               'choices': ['3,3 oy', '6 oy', '7,5 oy', '10 oy'],
               'explanation': 'Oylik sof chiqim: 18 000 − 8 000 = 10 000. Zaxira: 60 000 ÷ 10 000 = 6 oy.'},
    }},
]


def _words(case):
    return languages.pick(case['text'])


@csrf_exempt
@require_auth
def challenges(request):
    units={u.slug:u for u in Unit.objects.filter(slug__in=[c['unit'] for c in CASES])}
    cases=[c for c in CASES if c['unit'] in units]
    if request.method=='GET':
        return JsonResponse({'challenges':[
            {'id':c['id'],'unit':c['unit'],'prompt':_words(c)['prompt'],'choices':_words(c)['choices'],
             'unit_title':units[c['unit']].tr('title')}
            for c in cases
        ]})
    if request.method=='POST':
        try:
            data=json.loads(request.body)
        except (ValueError,UnicodeDecodeError):
            return JsonResponse({'detail':'Invalid JSON.'},status=400)
        if not isinstance(data,dict):
            return JsonResponse({'detail':'Expected an object.'},status=400)
        case=next((c for c in cases if c['id']==data.get('id')),None)
        choice=data.get('choice_index')
        if not case or type(choice) is not int or not 0<=choice<len(_words(case)['choices']):
            return JsonResponse({'detail':'Choose a valid answer.'},status=400)
        return JsonResponse({'correct':choice==case['answer_index'],'answer_index':case['answer_index'],'explanation':_words(case)['explanation']})
    return JsonResponse({'detail':'Method not allowed.'},status=405)
