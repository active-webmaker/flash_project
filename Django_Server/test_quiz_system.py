#!/usr/bin/env python
import os
import django

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "flash_server.settings")
django.setup()

from django.contrib.auth.models import User
from django.utils import timezone
from quiz.models import (
    QuizProfile, Topic, Difficulty, Question,
    QuizSession, SessionAnswer, Badge, UserBadge
)

print("=" * 70)
print("Flash AI Coding Agent - Quiz System Complete Test")
print("=" * 70)

# Test 1: Setup test user and quiz profile
print("\n[TEST 1: Quiz Profile Setup]")
test_user, created = User.objects.get_or_create(
    username="quiz_test_user",
    defaults={"email": "quiz@test.com"}
)
status = "[NEW]" if created else "[EXISTS]"
print(f"{status} User: {test_user.username} (ID: {test_user.id})")

quiz_profile, created = QuizProfile.objects.get_or_create(
    user=test_user,
    defaults={
        "total_points": 0,
        "level": 1,
        "streak_days": 0,
        "consecutive_correct": 0
    }
)
status = "[NEW]" if created else "[EXISTS]"
print(f"{status} Quiz Profile created")
print(f"  Initial State: Level={quiz_profile.level}, Points={quiz_profile.total_points}")

# Test 2: Get available topics and difficulties
print("\n[TEST 2: Get Available Topics and Difficulties]")
topics = Topic.objects.all()
difficulties = Difficulty.objects.all()

print(f"[OK] Topics: {topics.count()} found")
for topic in topics:
    question_count = topic.questions.count()
    print(f"  - {topic.name} ({question_count} questions)")

print(f"[OK] Difficulties: {difficulties.count()} found")
for diff in difficulties:
    print(f"  - {diff.name} (Level: {diff.level})")

# Test 3: Create quiz session
print("\n[TEST 3: Create Quiz Session]")
if topics.exists() and difficulties.exists():
    selected_topic = topics.first()
    selected_difficulty = difficulties.filter(name="EASY").first() or difficulties.first()

    session = QuizSession.objects.create(
        profile=quiz_profile,
        difficulty=selected_difficulty,
        is_finished=False,
        score=0
    )
    print(f"[OK] Session created (ID: {session.id})")
    print(f"  Topic: {selected_topic.name}")
    print(f"  Difficulty: {selected_difficulty.name}")
    print(f"  Start Time: {session.start_time}")

    # Add 3 questions to session
    questions = selected_topic.questions.all()[:3]
    session.questions.add(*questions)
    session.save()
    print(f"  Questions added: {session.questions.count()}")

    # Test 4: Answer questions
    print("\n[TEST 4: Answer Questions and Record Answers]")
    correct_count = 0

    for idx, question in enumerate(questions, 1):
        # Simulate user answering
        # We'll answer the first 2 correctly, and 1 incorrectly
        if idx <= 2:
            user_answer = question.correct_answer
            is_correct = True
            correct_count += 1
            result = "CORRECT"
        else:
            # Pick wrong answer
            options = question.options
            wrong_answers = [ans for ans in options if ans != question.correct_answer]
            user_answer = wrong_answers[0] if wrong_answers else "0"
            is_correct = False
            result = "INCORRECT"

        answer = SessionAnswer.objects.create(
            session=session,
            question=question,
            user_answer=user_answer,
            is_correct=is_correct
        )
        print(f"  Q{idx}: {result}")
        print(f"       Question: {question.question_text[:50]}...")
        print(f"       User Answer: {user_answer}, Correct: {question.correct_answer}")

    # Test 5: Calculate score and finish session
    print("\n[TEST 5: Calculate Score and Finish Session]")
    total_questions = session.questions.count()
    correct_answers = SessionAnswer.objects.filter(
        session=session,
        is_correct=True
    ).count()

    score = int((correct_answers / total_questions) * 100) if total_questions > 0 else 0

    session.score = score
    session.is_finished = True
    session.end_time = timezone.now()
    session.save()

    print(f"[OK] Session Finished")
    print(f"  Total Questions: {total_questions}")
    print(f"  Correct Answers: {correct_answers}")
    print(f"  Score: {score}%")
    print(f"  Duration: {session.end_time - session.start_time}")

    # Test 6: Award badges based on performance
    print("\n[TEST 6: Award Badges Based on Performance]")

    # Create or get badge
    badge, created = Badge.objects.get_or_create(
        badge_id="quiz_completionist",
        defaults={
            "name": "Quiz Completionist",
            "description": "Completed your first quiz",
            "points": 50
        }
    )
    status = "[NEW]" if created else "[EXISTS]"
    print(f"{status} Badge: {badge.name}")

    # Award badge if not already awarded
    user_badge, created = UserBadge.objects.get_or_create(
        profile=quiz_profile,
        badge=badge
    )
    status = "[NEW]" if created else "[EXISTS]"
    print(f"{status} Badge awarded to user")

    # Test 7: Update quiz profile with session results
    print("\n[TEST 7: Update Quiz Profile with Session Results]")
    quiz_profile.total_points += badge.points
    quiz_profile.consecutive_correct = correct_answers

    # Increase level if score is high
    if score >= 80:
        quiz_profile.level += 1
        print(f"[LEVEL UP] {quiz_profile.level - 1} -> {quiz_profile.level}")

    quiz_profile.save()

    print(f"[OK] Profile Updated")
    print(f"  Points: {quiz_profile.total_points}")
    print(f"  Level: {quiz_profile.level}")
    print(f"  Consecutive Correct: {quiz_profile.consecutive_correct}")
    print(f"  Badges Earned: {quiz_profile.badges.count()}")

    # Test 8: Query session history
    print("\n[TEST 8: Query Session History]")
    all_sessions = QuizSession.objects.filter(profile=quiz_profile)
    print(f"[OK] Total Sessions: {all_sessions.count()}")
    for sess in all_sessions:
        ans_count = sess.answers.count()
        correct = sess.answers.filter(is_correct=True).count()
        print(f"  Session {sess.id}: Score={sess.score}%, Answers={ans_count}, Correct={correct}")

else:
    print("[ERROR] No topics or difficulties found. Run populate_test_data.py first.")

print("\n" + "=" * 70)
print("Quiz System Test Completed")
print("=" * 70)

# Final Statistics
print("\n[FINAL STATISTICS]")
print(f"  Total Quiz Users: {QuizProfile.objects.count()}")
print(f"  Total Sessions: {QuizSession.objects.count()}")
print(f"  Total Answers: {SessionAnswer.objects.count()}")
print(f"  Total Badges: {Badge.objects.count()}")
print(f"  Total Awarded Badges: {UserBadge.objects.count()}")
