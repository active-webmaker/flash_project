
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status
from .models import QuizProfile, Topic, Difficulty, Question, QuizSession, SessionAnswer

class QuizTests(APITestCase):
    def setUp(self):
        # 테스트용 사용자 생성 (QuizProfile은 signal에 의해 자동 생성됨)
        self.username = "testuser_quiz"
        self.password = "testpassword123"
        self.user = User.objects.create_user(username=self.username, password=self.password)
        self.quiz_profile = self.user.quiz_profile # 자동으로 생성된 프로필을 가져옴

        # JWT 토큰 획득 및 API 클라이언트 인증 설정
        token_url = '/api/v1/auth/login'
        response = self.client.post(token_url, {'username': self.username, 'password': self.password}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        access_token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + access_token)

        # 테스트용 데이터 생성
        self.topic = Topic.objects.create(name="Python Basics")
        self.difficulty = Difficulty.objects.create(name="beginner", level=1)
        self.question1 = Question.objects.create(
            topic=self.topic,
            difficulty=self.difficulty,
            question_text="What is the output of print(2 ** 3)?",
            options={"a": "6", "b": "8", "c": "9", "d": "12"},
            correct_answer="b",
            explanation="The ** operator is for exponentiation."
        )
        self.question2 = Question.objects.create(
            topic=self.topic,
            difficulty=self.difficulty,
            question_text="Which data type is immutable in Python?",
            options={"a": "List", "b": "Dictionary", "c": "Tuple", "d": "Set"},
            correct_answer="c",
            explanation="Tuples are immutable sequences."
        )

    def test_quiz_model_creation(self):
        """
        퀴즈 관련 모델들이 정상적으로 생성되는지 테스트합니다.
        """
        self.assertEqual(self.topic.name, "Python Basics")
        self.assertEqual(self.question1.topic, self.topic)
        self.assertTrue(Question.objects.count(), 2)

    def test_start_quiz_session(self):
        """
        퀴즈 세션을 시작하는 API를 테스트합니다.
        """
        url = '/api/v1/quiz/sessions'
        data = {
            "pool_id": self.topic.id,
            "num_questions": 1
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)
        self.assertEqual(len(response.data['questions']), 1)
        
        session_id = response.data['id']
        session = QuizSession.objects.get(id=session_id)
        self.assertEqual(session.profile, self.quiz_profile)
        self.assertFalse(session.is_finished)

    def test_submit_answer(self):
        """
        퀴즈 세션에 답안을 제출하고 채점하는 API를 테스트합니다.
        """
        # 1. 세션 생성
        session = QuizSession.objects.create(profile=self.quiz_profile)
        session.questions.add(self.question1)

        # 2. 정답 제출
        correct_answer_url = f'/api/v1/quiz/sessions/{session.id}/answers'
        correct_data = {
            "question_id": self.question1.id,
            "selected_option_id": "b" # 정답
        }
        response = self.client.post(correct_answer_url, correct_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_correct'])
        
        # DB 확인
        session.refresh_from_db()
        self.assertEqual(session.score, 10)
        answer_log = SessionAnswer.objects.get(session=session, question=self.question1)
        self.assertTrue(answer_log.is_correct)

        # 3. 오답 제출
        session.questions.add(self.question2)
        wrong_answer_url = f'/api/v1/quiz/sessions/{session.id}/answers'
        wrong_data = {
            "question_id": self.question2.id,
            "selected_option_id": "a" # 오답
        }
        response = self.client.post(wrong_answer_url, wrong_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['is_correct'])

        # DB 확인 (점수는 그대로여야 함)
        session.refresh_from_db()
        self.assertEqual(session.score, 10)
        answer_log = SessionAnswer.objects.get(session=session, question=self.question2)
        self.assertFalse(answer_log.is_correct)

    def test_finish_quiz_session(self):
        """
        퀴즈 세션을 종료하는 API를 테스트합니다.
        """
        session = QuizSession.objects.create(profile=self.quiz_profile, score=20)
        url = f'/api/v1/quiz/sessions/{session.id}/finish'

        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['score'], 20)

        session.refresh_from_db()
        self.assertTrue(session.is_finished)
        self.assertIsNotNone(session.end_time)
