"""The practice trainer and "Up or down?"."""
import json
import uuid

from django.test import TestCase

from accounts.jwt_utils import encode_access_token
from accounts.models import User

from .models import DailyQuestion, MarketEpisode, UserStats


class PracticeTests(TestCase):
    """Questions come without answers until graded, and never the same one twice running."""

    def setUp(self):
        self.user = User.objects.create_user(email="practice@example.test", password="Str0ng-Passphrase!")
        self.auth = {"HTTP_AUTHORIZATION": "Bearer " + encode_access_token(self.user, uuid.uuid4())}
        for i in range(4):
            DailyQuestion.objects.create(
                slug=f"p{i}", topic=DailyQuestion.Topic.RISK if i else DailyQuestion.Topic.CREDIT, answer=2,
                body={"en": {"question": f"Q{i}?", "options": ["a", "b", "c", "d"], "explain": f"because {i}"}},
            )

    def next(self, query=""):
        return self.client.get("/api/learning/practice/next?lang=en" + query, **self.auth).json()

    def answer(self, qid, choice):
        return self.client.post(
            "/api/learning/practice/answer?lang=en", data=json.dumps({"id": qid, "choice": choice}),
            content_type="application/json", **self.auth,
        )

    def test_a_question_comes_without_its_answer_and_is_graded(self):
        question = self.next()["question"]
        self.assertNotIn("answer", question)
        self.assertNotIn("explain", question)
        graded = self.answer(question["id"], 2).json()
        self.assertTrue(graded["correct"])
        self.assertEqual((graded["answer"], graded["stats"]["today"]), (2, 1))
        self.assertFalse(self.answer(question["id"], 0).json()["correct"])
        self.assertEqual(self.answer(question["id"], 9).status_code, 400)
        self.assertEqual(self.answer("not-a-uuid", 0).status_code, 400)

    def test_asking_for_the_answer_shows_it_and_counts_as_not_right(self):
        question = self.next()["question"]
        response = self.client.post(
            "/api/learning/practice/answer?lang=en", data=json.dumps({"id": question["id"], "reveal": True}),
            content_type="application/json", **self.auth,
        ).json()
        self.assertEqual(
            (response["revealed"], response["correct"], response["chosen"], response["answer"]), (True, False, None, 2)
        )
        self.assertEqual((response["stats"]["today"], response["stats"]["today_correct"]), (1, 0))
        # Nothing was reasoned, so there is no mistake for the AI to analyse.
        self.assertIsNone(self.client.get("/api/ai/context?lang=en", **self.auth).json()["mistake"])

    def test_topic_filter_and_no_immediate_repeat(self):
        credit = self.next("&topic=credit")["question"]
        self.assertEqual(credit["topic"], "credit")
        for _ in range(10):
            self.assertNotEqual(self.next(f"&after={credit['id']}")["question"]["id"], credit["id"])

    def test_a_practice_mistake_is_what_the_ai_offers_to_explain(self):
        wrong = self.next()["question"]
        self.answer(wrong["id"], 0)
        mistake = self.client.get("/api/ai/context?lang=en", **self.auth).json()["mistake"]
        self.assertEqual(
            (mistake["source"], mistake["question"], mistake["chosen"], mistake["correct"]),
            ("practice", wrong["question"], "a", "c"),
        )


class PredictTests(TestCase):
    """The future stays hidden, a right call pays once, and a day has three rounds."""

    def setUp(self):
        self.user = User.objects.create_user(email="predict@example.test", password="Str0ng-Passphrase!")
        self.auth = {"HTTP_AUTHORIZATION": "Bearer " + encode_access_token(self.user, uuid.uuid4())}
        UserStats.objects.create(user=self.user)
        self.episodes = [
            MarketEpisode.objects.create(
                slug=f"e{i}", asset="Test", before=[100, 90, 80],
                after=[120, 140] if i % 2 == 0 else [60, 50],
                direction="up" if i % 2 == 0 else "down", order=i,
                body={"en": {"when": "then", "headline": "news", "question": "where?", "explain": "why", "lesson": "so"}},
            )
            for i in range(4)
        ]

    def state(self):
        return self.client.get("/api/learning/predict?lang=en", **self.auth).json()

    def call(self, episode_id, choice):
        return self.client.post(
            "/api/learning/predict/answer?lang=en", data=json.dumps({"id": episode_id, "choice": choice}),
            content_type="application/json", **self.auth,
        )

    def test_the_round_hides_what_happened_next(self):
        round_ = self.state()["round"]
        self.assertEqual(round_["id"], str(self.episodes[0].id))
        for secret in ("after", "direction", "explain", "lesson"):
            self.assertNotIn(secret, round_)

    def test_a_right_call_pays_once_and_the_day_has_three_rounds(self):
        first, second, third, fourth = (str(e.id) for e in self.episodes)
        right = self.call(first, "up").json()
        self.assertEqual((right["correct"], right["coins"], right["after"]), (True, 5, [120, 140]))
        self.assertEqual(UserStats.objects.get(user=self.user).coins, 5)
        self.assertEqual(self.call(first, "up").status_code, 409)
        wrong = self.call(second, "up").json()
        self.assertEqual((wrong["correct"], wrong["coins"], wrong["stats"]["streak"]), (False, 0, 0))
        self.call(third, "down")
        self.assertEqual(self.call(fourth, "down").status_code, 429)
        state = self.state()
        self.assertEqual((state["left_today"], state["round"], state["stats"]["played"]), (0, None, 3))
        self.assertEqual(UserStats.objects.get(user=self.user).coins, 5)

    def test_nonsense_is_refused(self):
        self.assertEqual(self.call(str(self.episodes[0].id), "sideways").status_code, 400)
        self.assertEqual(self.call("nope", "up").status_code, 400)
