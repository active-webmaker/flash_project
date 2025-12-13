#!/usr/bin/env python
"""
Django 퀴즈 데이터 검증 스크립트
- Topic (퀴즈 카테고리) 존재 여부 확인
- Question 데이터 개수 확인
- 만약 데이터가 없으면 샘플 데이터 생성
"""

import os
import sys
import django

# Django 프로젝트 경로 설정
project_dir = os.path.dirname(os.path.abspath(__file__))
django_dir = os.path.join(project_dir, 'Django_Server')
sys.path.insert(0, django_dir)

# Django 설정 초기화
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flash_server.settings')
django.setup()

from quiz.models import Topic, Question, Difficulty

def check_and_populate_quiz_data():
    """퀴즈 데이터 확인 및 필요시 샘플 생성"""
    
    print("=" * 80)
    print("📊 Django 퀴즈 데이터 검증")
    print("=" * 80)
    
    # 1. Topic 확인
    topics = Topic.objects.all()
    print(f"\n✓ Topic 총 개수: {topics.count()}")
    
    if topics.count() == 0:
        print("⚠️  Topic이 없습니다. 샘플 데이터를 생성합니다...")
        
        sample_topics = [
            {
                'name': 'Python Basics',
                'description': 'Python 기본 문법과 데이터 구조'
            },
            {
                'name': 'Web Development',
                'description': 'HTML, CSS, JavaScript를 이용한 웹 개발'
            },
            {
                'name': 'Database Design',
                'description': 'SQL 및 데이터베이스 설계 원칙'
            },
            {
                'name': 'API Development',
                'description': 'REST API 설계 및 구현'
            },
        ]
        
        for topic_data in sample_topics:
            topic, created = Topic.objects.get_or_create(**topic_data)
            if created:
                print(f"  ✓ 생성됨: {topic.name}")
            else:
                print(f"  - 이미 존재: {topic.name}")
    else:
        for topic in topics:
            question_count = topic.questions.count()
            print(f"  - {topic.name}: {question_count}개 문제")
    
    # 2. Difficulty 확인
    difficulties = Difficulty.objects.all()
    print(f"\n✓ Difficulty 총 개수: {difficulties.count()}")
    
    if difficulties.count() == 0:
        print("⚠️  Difficulty가 없습니다. 샘플 데이터를 생성합니다...")
        
        sample_difficulties = [
            {'name': 'Beginner', 'level': 1},
            {'name': 'Intermediate', 'level': 2},
            {'name': 'Advanced', 'level': 3},
        ]
        
        for diff_data in sample_difficulties:
            diff, created = Difficulty.objects.get_or_create(**diff_data)
            if created:
                print(f"  ✓ 생성됨: {diff.name} (Level {diff.level})")
            else:
                print(f"  - 이미 존재: {diff.name}")
    else:
        for difficulty in difficulties:
            question_count = difficulty.questions.count()
            print(f"  - {difficulty.name} (Level {difficulty.level}): {question_count}개 문제")
    
    # 3. Question 확인
    questions = Question.objects.all()
    print(f"\n✓ Question 총 개수: {questions.count()}")
    
    if questions.count() == 0:
        print("⚠️  Question이 없습니다. 샘플 데이터를 생성합니다...")
        
        # 먼저 Topic과 Difficulty가 있는지 확인
        topics = Topic.objects.all()
        difficulties = Difficulty.objects.all()
        
        if not topics.exists():
            print("❌ Topic이 없어서 Question을 생성할 수 없습니다.")
            return False
        
        if not difficulties.exists():
            print("❌ Difficulty가 없어서 Question을 생성할 수 없습니다.")
            return False
        
        topic = topics.first()
        difficulty = difficulties.first()
        
        sample_questions = [
            {
                'topic': topic,
                'difficulty': difficulty,
                'question_text': 'Python에서 리스트의 메서드가 아닌 것은?',
                'options': {
                    'a': 'append()',
                    'b': 'pop()',
                    'c': 'insert()',
                    'd': 'push()'
                },
                'correct_answer': 'd',
                'explanation': 'Python 리스트에는 push() 메서드가 없습니다. 대신 append()를 사용합니다.',
                'learning_tip': 'Python 리스트의 모든 메서드를 확인하려면 dir(list)를 사용하세요.'
            },
            {
                'topic': topic,
                'difficulty': difficulty,
                'question_text': '다음 중 Python의 불변 데이터 타입은?',
                'options': {
                    'a': 'list',
                    'b': 'dict',
                    'c': 'tuple',
                    'd': 'set'
                },
                'correct_answer': 'c',
                'explanation': 'Tuple은 불변(immutable) 데이터 타입입니다. 생성 후 수정할 수 없습니다.',
                'learning_tip': '불변 데이터 타입(tuple, string)은 딕셔너리의 키로 사용할 수 있습니다.'
            },
        ]
        
        for q_data in sample_questions:
            question, created = Question.objects.create(**q_data)
            if created:
                print(f"  ✓ 생성됨: {question.question_text[:50]}...")
        
        print(f"\n✓ 샘플 Question 생성 완료 (총 {len(sample_questions)}개)")
    else:
        print(f"  ✓ 문제가 데이터베이스에 존재합니다.")
        for topic in topics:
            count = Question.objects.filter(topic=topic).count()
            print(f"    - {topic.name}: {count}개 문제")
    
    print("\n" + "=" * 80)
    print("✅ 검증 완료")
    print("=" * 80)
    print("\n📌 다음 단계:")
    print("  1. Streamlit Quiz 탭 새로고침")
    print("  2. '/api/v1/quiz/pools' 엔드포인트 확인")
    print("  3. Django 관리자 페이지 (http://localhost:8000/admin)에서 Topic 추가 가능")
    
    return True

if __name__ == '__main__':
    try:
        check_and_populate_quiz_data()
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
