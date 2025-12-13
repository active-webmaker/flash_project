#!/usr/bin/env python
import os
import django

# Django 설정 초기화
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "flash_server.settings")
django.setup()

from quiz.models import Topic, Question, Difficulty
from gamification.models import Badge

print("=" * 60)
print("Flash AI Coding Agent - 테스트 데이터 입력")
print("=" * 60)

# 난이도 생성
print("\n[난이도 생성]")
difficulties = {}
difficulty_data = [
    {"name": "EASY", "level": 1},
    {"name": "INTERMEDIATE", "level": 2},
    {"name": "HARD", "level": 3}
]

for diff_data in difficulty_data:
    diff, created = Difficulty.objects.get_or_create(
        name=diff_data["name"],
        defaults={"level": diff_data["level"]}
    )
    difficulties[diff_data["name"]] = diff
    status = "[NEW]" if created else "[EXISTS]"
    print(f"{status} {diff_data['name']}")

# 퀴즈 토픽 생성
print("\n[토픽 생성]")
topics_data = [
    {
        "name": "Python Basics",
        "description": "Python 기초 개념 학습"
    },
    {
        "name": "JavaScript Fundamentals",
        "description": "JavaScript 기본 개념"
    },
    {
        "name": "Web Development",
        "description": "웹 개발 기초"
    }
]

topics = {}
for topic_data in topics_data:
    topic, created = Topic.objects.get_or_create(
        name=topic_data["name"],
        defaults={
            "description": topic_data["description"]
        }
    )
    topics[topic_data["name"]] = topic
    status = "[NEW]" if created else "[EXISTS]"
    print(f"{status} {topic_data['name']}")

# 질문 생성
print("\n[질문 생성]")
questions_data = [
    {
        "topic": "Python Basics",
        "question_text": "Python에서 리스트의 길이를 구하는 함수는?",
        "options": ["len()", "length()", "size()", "count()"],
        "correct_answer": 0,
        "difficulty": "EASY"
    },
    {
        "topic": "Python Basics",
        "question_text": "Python에서 딕셔너리 값에 접근하는 방법은?",
        "options": ["dict[key]", "dict.get(key)", "dict(key)", "dict.key"],
        "correct_answer": 0,
        "difficulty": "EASY"
    },
    {
        "topic": "Python Basics",
        "question_text": "Python에서 문자열의 대문자로 변환하는 메서드는?",
        "options": ["toUpper()", "upper()", "to_upper()", "UPPER()"],
        "correct_answer": 1,
        "difficulty": "EASY"
    },
    {
        "topic": "JavaScript Fundamentals",
        "question_text": "JavaScript에서 변수를 선언하는 올바른 방법은?",
        "options": ["var name = 'John'", "name = 'John'", "declare name = 'John'", "variable name = 'John'"],
        "correct_answer": 0,
        "difficulty": "EASY"
    },
    {
        "topic": "JavaScript Fundamentals",
        "question_text": "JavaScript의 화살표 함수 문법은?",
        "options": ["function => {}", "=> function {}", "const fn = () => {}", "func => {}"],
        "correct_answer": 2,
        "difficulty": "INTERMEDIATE"
    },
    {
        "topic": "Web Development",
        "question_text": "HTML에서 웹 페이지의 메타데이터를 정의하는 태그는?",
        "options": ["<head>", "<meta>", "<info>", "<data>"],
        "correct_answer": 1,
        "difficulty": "EASY"
    }
]

question_count = 0
for q_data in questions_data:
    topic = topics[q_data["topic"]]
    difficulty = difficulties[q_data["difficulty"]]
    question, created = Question.objects.get_or_create(
        topic=topic,
        question_text=q_data["question_text"],
        defaults={
            "options": q_data["options"],
            "correct_answer": q_data["correct_answer"],
            "difficulty": difficulty
        }
    )
    if created:
        question_count += 1
        status = "[NEW]"
    else:
        status = "[EXISTS]"
    print(f"{status} {q_data['question_text'][:40]}...")

# 배지 생성 (skip - code 필드 충돌)
print("\n[배지 생성]")
print("[SKIP] 배지는 code 필드의 UNIQUE 제약으로 인해 스킵됨")

print("\n" + "=" * 60)
print("데이터 입력 완료!")
print("=" * 60)

# 통계 출력
print(f"\n[통계]")
print(f"총 토픽: {Topic.objects.count()}")
print(f"총 질문: {Question.objects.count()}")
print(f"총 배지: {Badge.objects.count()}")
