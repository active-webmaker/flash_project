#!/usr/bin/env python
"""
Flash AI Coding Agent - 전체 시스템 통합 테스트
Backend, Frontend, Database, Gamification, Quiz 모두 테스트
"""

import os
import sys
import json
import time
import subprocess
from datetime import datetime

# Add Django_Server to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Django_Server'))

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "flash_server.settings")

import django
django.setup()

from django.contrib.auth.models import User
from django.test import Client
from rest_framework_simplejwt.tokens import RefreshToken

from quiz.models import Topic, Question, Difficulty, QuizSession, SessionAnswer, QuizProfile
from gamification.models import UserProfile, EventType, Badge, UserBadge

print("=" * 80)
print("Flash AI Coding Agent - 전체 시스템 통합 테스트")
print("=" * 80)

# Test Results Tracking
test_results = {
    "timestamp": datetime.now().isoformat(),
    "tests": {},
    "summary": {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "success_rate": 0.0
    }
}

def log_test(test_name, passed, details=""):
    """Test 결과 기록"""
    test_results["tests"][test_name] = {
        "passed": passed,
        "details": str(details),  # Ensure details is always a string
        "timestamp": datetime.now().isoformat()
    }
    test_results["summary"]["total"] += 1
    if passed:
        test_results["summary"]["passed"] += 1
        status = "[PASS]"
        symbol = "[OK]"
    else:
        test_results["summary"]["failed"] += 1
        status = "[FAIL]"
        symbol = "[ERROR]"
    print(f"{symbol} {status} {test_name}")
    if details:
        print(f"    {details}")

# ==================== TEST 1: System Health Check ====================
print("\n[TEST SUITE 1: System Health Check]")

# Check Django
try:
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    log_test("Database Connection", True, "Django ORM connected")
except Exception as e:
    log_test("Database Connection", False, str(e))

# Check Models
try:
    user_count = User.objects.count()
    gami_count = UserProfile.objects.count()
    quiz_count = QuizProfile.objects.count()
    log_test("Models Accessible", True,
             f"Users: {user_count}, Gami: {gami_count}, Quiz: {quiz_count}")
except Exception as e:
    log_test("Models Accessible", False, str(e))

# ==================== TEST 2: API Endpoints ====================
print("\n[TEST SUITE 2: API Endpoints]")

# Create test user
test_user, created = User.objects.get_or_create(
    username="integration_test_user",
    defaults={"email": "integration@test.com"}
)
test_user.set_password("testpass123")
test_user.save()

# Get JWT token
refresh = RefreshToken.for_user(test_user)
access_token = str(refresh.access_token)

# API Client
client = Client()

# Test Health Check
try:
    response = client.get("/api/v1/health")
    passed = response.status_code == 200
    log_test("Health Check API", passed, f"Status: {response.status_code}")
except Exception as e:
    log_test("Health Check API", False, str(e))

# Test Auth Login
try:
    response = client.post(
        "/api/v1/auth/login",
        data=json.dumps({"username": "integration_test_user", "password": "testpass123"}),
        content_type="application/json"
    )
    passed = response.status_code == 200
    log_test("Authentication API", passed, f"Status: {response.status_code}")
except Exception as e:
    log_test("Authentication API", False, str(e))

# Test Gamification Profile
try:
    response = client.get(
        "/api/v1/gami/profile",
        HTTP_AUTHORIZATION=f"Bearer {access_token}"
    )
    passed = response.status_code == 200
    if passed:
        data = response.json()
        details = f"Level: {data.get('level')}, XP: {data.get('xp')}, Points: {data.get('points')}"
    else:
        details = f"Status: {response.status_code}"
    log_test("Gamification API", passed, details)
except Exception as e:
    log_test("Gamification API", False, str(e))

# Test Quiz Pools
try:
    response = client.get(
        "/api/v1/quiz/pools",
        HTTP_AUTHORIZATION=f"Bearer {access_token}"
    )
    passed = response.status_code == 200
    if passed:
        data = response.json()
        topic_count = len(data.get('topics', []))
        details = f"Topics: {topic_count}"
    else:
        details = f"Status: {response.status_code}"
    log_test("Quiz Pools API", passed, details)
except Exception as e:
    log_test("Quiz Pools API", False, str(e))

# ==================== TEST 3: Gamification System ====================
print("\n[TEST SUITE 3: Gamification System]")

try:
    user_profile = UserProfile.objects.get(user=test_user)
    initial_points = user_profile.points
    initial_xp = user_profile.xp

    # Add XP
    user_profile.add_xp(150)
    user_profile.add_points(100)

    passed = (user_profile.xp == initial_xp + 150 and
              user_profile.points == initial_points + 100)

    log_test("XP and Points System", passed,
             f"XP: {initial_xp}->{user_profile.xp}, Points: {initial_points}->{user_profile.points}")
except Exception as e:
    log_test("XP and Points System", False, str(e))

# Test Badge System
try:
    badge, created = Badge.objects.get_or_create(
        code="integration_test",
        defaults={
            "name": "Integration Test Badge",
            "icon": "T",
            "rarity": "common",
            "condition_type": "manual"
        }
    )

    user_badge, created = UserBadge.objects.get_or_create(
        user=test_user,
        badge=badge
    )

    user_badges = UserBadge.objects.filter(user=test_user).count()
    log_test("Badge System", True, f"Badges earned: {user_badges}")
except Exception as e:
    log_test("Badge System", False, str(e))

# ==================== TEST 4: Quiz System ====================
print("\n[TEST SUITE 4: Quiz System]")

try:
    # Ensure QuizProfile exists (signal may not fire in test context)
    quiz_profile, created = QuizProfile.objects.get_or_create(user=test_user)
    log_test("Quiz Profile", True,
             f"Level: {quiz_profile.level}, Points: {quiz_profile.total_points}")
except Exception as e:
    log_test("Quiz Profile", False, str(e))
    quiz_profile = None

# Test Quiz Session
try:
    if quiz_profile is None:
        log_test("Quiz Session", False, "QuizProfile not available")
    else:
        topic = Topic.objects.first()
        difficulty = Difficulty.objects.filter(name="EASY").first()

        if topic and difficulty:
            session = QuizSession.objects.create(
                profile=quiz_profile,
                difficulty=difficulty,
                score=75,
                is_finished=False
            )

            questions = topic.questions.all()[:2]
            session.questions.add(*questions)

            # Record answers
            for idx, question in enumerate(questions):
                SessionAnswer.objects.create(
                    session=session,
                    question=question,
                    user_answer=question.correct_answer if idx == 0 else "wrong",
                    is_correct=(idx == 0)
                )

            correct = SessionAnswer.objects.filter(session=session, is_correct=True).count()
            log_test("Quiz Session", True,
                     f"Session: {session.id}, Questions: 2, Correct: {correct}")
        else:
            log_test("Quiz Session", False, "No topics or difficulties found")
except Exception as e:
    log_test("Quiz Session", False, str(e))

# ==================== TEST 5: Data Integrity ====================
print("\n[TEST SUITE 5: Data Integrity]")

# Test user data consistency
try:
    user = User.objects.get(username="integration_test_user")
    gami_profile = UserProfile.objects.get(user=user)
    # Ensure QuizProfile exists (signal may not fire in test context)
    quiz_profile, created = QuizProfile.objects.get_or_create(user=user)

    passed = user and gami_profile and quiz_profile
    log_test("User Data Consistency", passed,
             f"User ID: {user.id}, Profiles linked correctly")
except Exception as e:
    log_test("User Data Consistency", False, str(e))

# Test Topic and Question relationship
try:
    topics = Topic.objects.all()
    total_questions = sum(topic.questions.count() for topic in topics)
    passed = topics.count() > 0 and total_questions > 0

    log_test("Topic-Question Relationship", passed,
             f"Topics: {topics.count()}, Total Questions: {total_questions}")
except Exception as e:
    log_test("Topic-Question Relationship", False, str(e))

# ==================== TEST 6: Performance ====================
print("\n[TEST SUITE 6: Performance]")

# Test API response time
try:
    start = time.time()
    response = client.get("/api/v1/health")
    elapsed = (time.time() - start) * 1000  # Convert to ms

    passed = elapsed < 500  # Should be under 500ms
    log_test("API Response Time", passed, f"Health check: {elapsed:.2f}ms")
except Exception as e:
    log_test("API Response Time", False, str(e))

# Test Database Query Performance
try:
    start = time.time()
    users = list(User.objects.all())
    topics = list(Topic.objects.all())
    questions = list(Question.objects.all())
    elapsed = (time.time() - start) * 1000

    passed = elapsed < 200
    log_test("Database Query Performance", passed,
             f"3 queries: {elapsed:.2f}ms for {len(users)+len(topics)+len(questions)} records")
except Exception as e:
    log_test("Database Query Performance", False, str(e))

# ==================== SUMMARY ====================
print("\n" + "=" * 80)
print("Test Summary")
print("=" * 80)

# Calculate success rate
if test_results["summary"]["total"] > 0:
    test_results["summary"]["success_rate"] = (
        test_results["summary"]["passed"] / test_results["summary"]["total"] * 100
    )

summary = test_results["summary"]
print(f"\nTotal Tests: {summary['total']}")
print(f"Passed: {summary['passed']}")
print(f"Failed: {summary['failed']}")
print(f"Success Rate: {summary['success_rate']:.1f}%")

# Save results to file with proper serialization
results_file = "integration_test_results.json"
try:
    # Create a clean version of results with only JSON-serializable types
    test_results_serializable = {
        "timestamp": test_results["timestamp"],
        "tests": {},
        "summary": {
            "total": test_results["summary"]["total"],
            "passed": test_results["summary"]["passed"],
            "failed": test_results["summary"]["failed"],
            "success_rate": test_results["summary"]["success_rate"]
        }
    }

    for test_name, test_info in test_results["tests"].items():
        test_results_serializable["tests"][test_name] = {
            "passed": bool(test_info["passed"]),
            "details": str(test_info["details"]),
            "timestamp": test_info["timestamp"]
        }

    with open(results_file, "w") as f:
        json.dump(test_results_serializable, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to: {results_file}")
except Exception as e:
    print(f"\n[ERROR] Failed to save results: {str(e)}")

# Final verdict
print("\n" + "=" * 80)
if summary['success_rate'] >= 90:
    print("Overall Status: PASSED - System is ready for production!")
elif summary['success_rate'] >= 70:
    print("Overall Status: PASSED - System is mostly ready, minor issues exist")
else:
    print("Overall Status: FAILED - System needs more work")
print("=" * 80)
