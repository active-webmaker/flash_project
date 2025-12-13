#!/usr/bin/env python
"""
Django Quiz API 엔드포인트 테스트 스크립트
- /api/v1/quiz/pools 응답 확인
- 필요시 JWT 토큰 생성 후 인증된 요청 실행
"""

import os
import sys
import django
import json

# Django 프로젝트 경로 설정
project_dir = os.path.dirname(os.path.abspath(__file__))
django_dir = os.path.join(project_dir, 'Django_Server')
sys.path.insert(0, django_dir)

# Django 설정 초기화
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flash_server.settings')
django.setup()

from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from django.test import Client

def get_or_create_test_user():
    """테스트용 사용자 생성"""
    user, created = User.objects.get_or_create(
        username='testuser',
        defaults={'email': 'test@example.com'}
    )
    if created:
        user.set_password('testpass123')
        user.save()
        print(f"✓ 테스트 사용자 생성: {user.username}")
    else:
        print(f"✓ 기존 테스트 사용자 사용: {user.username}")
    return user

def get_jwt_token(user):
    """사용자용 JWT 토큰 생성"""
    refresh = RefreshToken.for_user(user)
    return str(refresh.access_token)

def test_quiz_pools_endpoint():
    """Quiz Pools 엔드포인트 테스트"""
    
    print("=" * 80)
    print("🧪 Django Quiz API 엔드포인트 테스트")
    print("=" * 80)
    
    # 1. 테스트 사용자 생성
    user = get_or_create_test_user()
    
    # 2. JWT 토큰 생성
    token = get_jwt_token(user)
    print(f"\n✓ JWT 토큰 생성됨 (처음 30자: {token[:30]}...)")
    
    # 3. Django Test Client를 사용한 API 테스트
    client = Client()
    
    # Quiz Pools 엔드포인트 테스트
    url = '/api/v1/quiz/pools'
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }
    
    print(f"\n📌 요청 정보:")
    print(f"  URL: {url}")
    print(f"  Method: GET")
    print(f"  Headers: {headers}")
    
    response = client.get(url, HTTP_AUTHORIZATION=f'Bearer {token}')
    
    print(f"\n📊 응답 정보:")
    print(f"  Status Code: {response.status_code}")
    print(f"  Content-Type: {response.get('Content-Type', 'N/A')}")
    
    # 응답 본문 파싱
    try:
        data = json.loads(response.content)
        print(f"\n📋 응답 데이터:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
        # 필드 검증
        if 'pools' in data:
            pools = data['pools']
            print(f"\n✅ 'pools' 필드 발견: {len(pools)}개 항목")
            
            if pools:
                first_pool = pools[0]
                print(f"\n🔍 첫 번째 Pool 구조:")
                for key, value in first_pool.items():
                    print(f"  - {key}: {value} ({type(value).__name__})")
                
                # Streamlit 호환성 확인
                print(f"\n✓ Streamlit 필드 검증:")
                print(f"  - 'title' (또는 'name'): {'✓' if first_pool.get('title') or first_pool.get('name') else '✗'}")
                print(f"  - 'description': {'✓' if first_pool.get('description') else '✗'}")
                print(f"  - 'question_count': {'✓' if first_pool.get('question_count') is not None else '✗'}")
        else:
            print(f"\n⚠️  'pools' 필드가 없습니다. 응답 구조를 확인하세요.")
    
    except json.JSONDecodeError as e:
        print(f"\n❌ JSON 파싱 실패: {e}")
        print(f"응답 내용 (원본): {response.content[:500]}")
    
    # 4. 요약
    print("\n" + "=" * 80)
    print("✅ 테스트 완료")
    print("=" * 80)
    
    if response.status_code == 200:
        print("\n✓ API 응답 상태: 정상 (200 OK)")
        print("\n📌 다음 단계:")
        print("  1. Streamlit 페이지 새로고침 (http://localhost:8501)")
        print("  2. Quiz 탭에서 'Python Basics', 'JavaScript Fundamentals' 등이 표시되는지 확인")
        print("  3. 각 카테고리의 문제 개수가 올바르게 표시되는지 확인")
    else:
        print(f"\n❌ API 응답 상태: {response.status_code}")
        print("→ Django 서버가 실행 중인지, 인증이 정상인지 확인하세요.")

if __name__ == '__main__':
    try:
        test_quiz_pools_endpoint()
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
