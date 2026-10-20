import json
import uuid
from datetime import timedelta

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from accounts.jwt_utils import encode_access_token
from accounts.models import User

from . import daily, league
from .models import (
    DailyActivity,
    DailyQuestion,
    LeagueMembership,
    Lesson,
    LessonProgress,
    Unit,
    UnitTestResult,
    UserStats,
)


class LearningFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='learner@example.test', password='Str0ng-Passphrase!')
        self.auth = {'HTTP_AUTHORIZATION': 'Bearer ' + encode_access_token(self.user, uuid.uuid4())}
        self.unit = Unit.objects.create(
            code='01', slug='basics', title='Basics', order=1, test_pass_threshold=0.5,
            test_questions=[
                {'id': 'q1', 'prompt': '2 + 2?', 'choices': ['3', '4'], 'answer_index': 1, 'explanation': 'Two pairs.'},
                {'id': 'q2', 'prompt': '1 + 1?', 'choices': ['2', '5'], 'answer_index': 0, 'explanation': 'One pair.'},
            ],
        )
        self.first = Lesson.objects.create(unit=self.unit, slug='one', title='Lesson one', order=1)
        self.second = Lesson.objects.create(unit=self.unit, slug='two', title='Lesson two', order=2)

    def post(self, path, data):
        return self.client.post('/api/learning/' + path, data=json.dumps(data), content_type='application/json', **self.auth)

    def test_next_step_follows_the_map(self):
        self.assertEqual(self.client.get('/api/learning/next-step', **self.auth).json()['id'], str(self.first.id))
        for lesson in (self.first, self.second):
            LessonProgress.objects.create(user=self.user, lesson=lesson, status=LessonProgress.Status.COMPLETED)
        step = self.client.get('/api/learning/next-step', **self.auth).json()
        self.assertEqual((step['kind'], step['id'], step['title']), ('test', str(self.unit.id), 'Basics'))
        self.assertEqual(self.client.get('/api/learning/next-step').status_code, 401)

    def test_today_plan_tracks_what_was_done_today(self):
        from ai_engine.models import AIUsageLog
        from startup.models import CashFlowEntry
        plan = self.client.get('/api/learning/today', **self.auth).json()
        self.assertEqual([c['key'] for c in plan['cards']], ['lesson', 'ai', 'startup'])
        self.assertEqual(plan['cards'][0]['id'], str(self.first.id))
        self.assertEqual((plan['done'], plan['total']), (0, 3))
        self.post(f'lessons/{self.first.id}/complete', {})
        AIUsageLog.objects.create(user=self.user, feature=AIUsageLog.Feature.ADVISOR, model_version='test')
        CashFlowEntry.objects.create(user=self.user, entry_type='revenue', category='Sales', amount=10)
        plan = self.client.get('/api/learning/today', **self.auth).json()
        self.assertEqual(plan['done'], 3)
        self.assertEqual(plan['cards'][0]['id'], str(self.second.id))
        self.assertEqual(plan['minutes_left'], 0)
        self.assertEqual(self.client.get('/api/learning/today').status_code, 401)

    def test_today_card_says_where_the_lesson_sits_in_its_unit(self):
        Lesson.objects.filter(pk=self.first.pk).update(estimated_minutes=8)
        card = self.client.get('/api/learning/today', **self.auth).json()['cards'][0]
        # The lesson's own estimate, not a flat five minutes.
        self.assertEqual((card['unit_done'], card['unit_total'], card['minutes']), (0, 2, 8))
        self.assertEqual((card['unit_code'], card['unit_title']), ('01', 'Basics'))
        LessonProgress.objects.create(user=self.user, lesson=self.first, status=LessonProgress.Status.COMPLETED)
        card = self.client.get('/api/learning/today', **self.auth).json()['cards'][0]
        self.assertEqual((card['id'], card['unit_done'], card['unit_total']), (str(self.second.id), 1, 2))

    def test_stats_show_the_league_without_taking_a_seat(self):
        # The dashboard reads the league on every visit; that must never seat
        # someone who has not opened the league themselves.
        standing = self.client.get('/api/learning/stats', **self.auth).json()['league']
        self.assertEqual((standing['division'], standing['rank'], standing['seated']), ('bronze', None, False))
        self.assertFalse(LeagueMembership.objects.filter(user=self.user).exists())
        self.client.get('/api/learning/league', **self.auth)
        standing = self.client.get('/api/learning/stats', **self.auth).json()['league']
        self.assertEqual((standing['seated'], standing['rank']), (True, 1))

    def test_unit_test_hides_answers_until_submitted(self):
        start = self.post(f'units/{self.unit.id}/test/start', {}).json()
        self.assertEqual(start['unit_title'], 'Basics')
        self.assertEqual(start['coin_reward'], 50)
        self.assertNotIn('answer_index', json.dumps(start))
        result = self.post(f'units/{self.unit.id}/test/submit', {'answers': [{'question_id': 'q1', 'choice_index': 1}, {'question_id': 'q2', 'choice_index': 1}]}).json()
        self.assertEqual((result['score'], result['passed'], result['coins_awarded']), (50, True, 50))
        self.assertEqual([r['correct'] for r in result['review']], [True, False])
        self.assertEqual(result['review'][1]['answer_index'], 0)
        again = self.post(f'units/{self.unit.id}/test/start', {}).json()
        self.assertEqual(again['coin_reward'], 0)


class LeagueTests(TestCase):
    """Points come from real work; the week closes into promotions and prizes."""

    def setUp(self):
        cache.clear()
        self.start = league.week_start()
        self.unit = Unit.objects.create(code="90", slug="league-unit", title="League unit", order=90)
        self.order = 0  # lesson order is unique per unit, so hand them out in sequence

    def _learner(self, email, lessons=0, tests=0, days=0):
        user = User.objects.create_user(email=email, password="Str0ng-Passphrase!")
        for i in range(lessons):
            self.order += 1
            lesson = Lesson.objects.create(unit=self.unit, slug=f"{email}-{i}", title=f"L{i}", order=self.order)
            LessonProgress.objects.create(
                user=user, lesson=lesson, status=LessonProgress.Status.COMPLETED, completed_at=timezone.now()
            )
        for _ in range(tests):
            UnitTestResult.objects.create(user=user, unit=self.unit, score=0.9, correct_count=9, total_count=10, passed=True)
        for d in range(days):
            DailyActivity.objects.create(user=user, date=self.start + timedelta(days=d))
        return user

    def test_points_come_from_work_not_from_granted_coins(self):
        user = self._learner("worker@example.test", lessons=2, tests=1, days=3)
        stats, _ = UserStats.objects.get_or_create(user=user)
        stats.add_coins(5000)  # support hands out coins: the board must not care
        stats.save()
        points = league.points_for([user.pk], self.start)[user.pk]
        self.assertEqual(points, 2 * 10 + 40 + 3 * 5)

    def test_a_retaken_test_is_only_worth_one_reward(self):
        user = self._learner("retaker@example.test", tests=3)
        self.assertEqual(league.points_for([user.pk], self.start)[user.pk], 40)

    def test_group_fills_before_a_second_one_starts(self):
        seats = {league.join(self._learner(f"seat{i}@example.test")).group_id for i in range(league.GROUP_SIZE)}
        self.assertEqual(len(seats), 1)
        overflow = league.join(self._learner("overflow@example.test"))
        self.assertNotIn(overflow.group_id, seats)

    def test_closing_the_week_promotes_the_top_and_pays_the_podium(self):
        winner = self._learner("first@example.test", lessons=5, days=5)
        second = self._learner("second@example.test", lessons=3)
        idle = self._learner("idle@example.test")
        for user in (winner, second, idle):
            league.join(user, self.start)

        league.close_week(self.start)
        seats = {m.user_id: m for m in LeagueMembership.objects.filter(week_start=self.start)}
        self.assertEqual(seats[winner.pk].rank, 1)
        self.assertEqual(seats[winner.pk].result, "promoted")
        self.assertEqual(seats[idle.pk].result, "stayed")  # nobody drops out of bronze
        self.assertEqual(UserStats.objects.get(user=winner).coins, league.PRIZE_COINS[0])

        # Re-running the command must not pay twice.
        league.close_week(self.start)
        self.assertEqual(UserStats.objects.get(user=winner).coins, league.PRIZE_COINS[0])
        # Next week starts one division up.
        self.assertEqual(league.join(winner, self.start + timedelta(days=7)).division, "silver")

    def test_the_board_never_shows_an_email(self):
        user = self._learner("private@example.test")
        league.join(user, self.start)
        self.assertNotIn("@", league.display_name(user))


class DailyTests(TestCase):
    """Zinvest Daily: the set is fixed for the day, and it pays exactly once."""

    def setUp(self):
        self.user = User.objects.create_user(email='daily@example.test', password='Str0ng-Passphrase!')
        self.auth = {'HTTP_AUTHORIZATION': 'Bearer ' + encode_access_token(self.user, uuid.uuid4())}
        UserStats.objects.create(user=self.user)
        for i in range(12):
            DailyQuestion.objects.create(
                slug=f'q{i}', topic=DailyQuestion.Topic.INVESTING, answer=1,
                body={'ru': {'question': f'В{i}?', 'options': ['нет', 'да'], 'explain': 'потому что'},
                      'en': {'question': f'Q{i}?', 'options': ['no', 'yes'], 'explain': 'because'}},
            )

    def state(self, lang='ru'):
        return self.client.get(f'/api/learning/daily?lang={lang}', **self.auth).json()

    def answer(self, choice):
        return self.client.post('/api/learning/daily/answer', data=json.dumps({'choice': choice}),
                                content_type='application/json', **self.auth).json()

    def test_the_set_is_the_same_all_day(self):
        first = self.state()
        self.assertTrue(first['available'])
        self.assertEqual(first['size'], daily.SIZE)
        self.assertEqual([i['question'] for i in first['items']], [i['question'] for i in self.state()['items']])

    def test_an_unplayed_question_does_not_leak_its_answer(self):
        first = self.state()['items'][0]
        self.assertNotIn('answer', first)
        self.assertNotIn('explain', first)

    def test_answering_grades_and_explains(self):
        wrong = self.answer(0)
        self.assertFalse(wrong['correct'])
        self.assertEqual(wrong['answer'], 1)
        self.assertEqual(wrong['explain'], 'потому что')
        self.assertEqual(self.state()['answered'], 1)

    def test_finishing_pays_once_and_banks_the_day(self):
        for _ in range(daily.SIZE):
            result = self.answer(1)
        self.assertTrue(result['finished'])
        self.assertEqual(result['correct'], daily.SIZE)
        self.assertEqual(result['coins_awarded'], daily.COINS_BASE + daily.COINS_PER_CORRECT * daily.SIZE)

        stats = UserStats.objects.get(user=self.user)
        self.assertEqual(stats.coins, result['coins_awarded'])
        self.assertEqual(stats.day_streak, 1)
        self.assertTrue(DailyActivity.objects.filter(user=self.user).exists())

        # A replayed request must not pay a second time.
        again = self.client.post('/api/learning/daily/answer', data=json.dumps({'choice': 1}),
                                 content_type='application/json', **self.auth)
        self.assertEqual(again.status_code, 400)
        self.assertEqual(UserStats.objects.get(user=self.user).coins, result['coins_awarded'])

    def test_a_wrong_round_still_pays_the_base(self):
        for _ in range(daily.SIZE):
            result = self.answer(0)
        self.assertEqual(result['coins_awarded'], daily.COINS_BASE)

    def test_tomorrow_avoids_what_was_seen_today(self):
        today = timezone.localdate()
        seen = set(daily.run_for(self.user, today).questions)
        tomorrow = set(daily.pick(self.user, today + timedelta(days=1)))
        self.assertFalse(seen & tomorrow)

    def test_the_language_follows_the_switcher(self):
        self.assertTrue(self.state('en')['items'][0]['question'].startswith('Q'))
        self.assertTrue(self.state('ru')['items'][0]['question'].startswith('В'))


class LearningEarnsAITokensTests(TestCase):
    """A new lesson and a new day of study add to this month's AI limit; repeats do not."""

    setUp = LearningFlowTests.setUp  # the same learner, unit and two lessons
    post = LearningFlowTests.post

    def quota(self):
        return self.client.get('/api/ai/quota', **self.auth).json()

    def test_a_new_lesson_and_a_new_streak_day_add_to_the_limit_once(self):
        before = self.quota()
        self.assertEqual((before['base_limit'], before['bonus']), (30000, 0))
        self.post(f'lessons/{self.first.id}/complete', {})
        after = self.quota()
        self.assertEqual(after['bonus'], 3000)  # +2 000 for the lesson, +1 000 for today's streak day
        self.assertEqual((after['limit'], after['remaining']), (33000, 33000))
        self.post(f'lessons/{self.first.id}/complete', {})  # the same lesson again
        self.post(f'lessons/{self.second.id}/complete', {})  # a new lesson, same day: no second streak bonus
        self.assertEqual(self.quota()['bonus'], 5000)

    def test_the_bonus_lapses_with_the_month(self):
        from ai_engine.models import UserAIQuota

        self.post(f'lessons/{self.first.id}/complete', {})
        q = UserAIQuota.objects.get(user=self.user)
        self.assertTrue(q.maybe_rollover(q.reset_date))
        self.assertEqual((q.bonus_tokens, q.tokens_used_this_cycle, q.remaining()), (0, 0, 30000))
