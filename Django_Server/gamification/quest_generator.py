"""
AI 퀘스트 생성기
"""
import random
import json
from datetime import date
from django.conf import settings
from .models import DailyQuest, UserProfile, UserEvent


def generate_ai_quests_with_llm(user):
    """
    OpenAI API를 사용하여 사용자 맞춤 퀘스트 생성

    Args:
        user: User 객체

    Returns:
        생성된 퀘스트 리스트 (dict)
    """
    try:
        from openai import OpenAI

        # API 키가 없으면 템플릿 사용
        if not settings.OPENAI_API_KEY:
            return None

        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        # 사용자 프로필 정보 가져오기
        profile = UserProfile.objects.filter(user=user).first()

        # 최근 활동 분석
        recent_events = UserEvent.objects.filter(user=user).order_by('-completed_at')[:5]
        recent_activities = [event.event_type.name for event in recent_events]

        # LLM에게 보낼 프롬프트
        prompt = f"""당신은 게이미피케이션 퀘스트 생성 전문가입니다.

사용자 정보:
- 레벨: {profile.level if profile else 1}
- 최근 활동: {', '.join(recent_activities) if recent_activities else '없음'}

위 정보를 바탕으로 사용자에게 적합한 일일 퀘스트 2개를 생성해주세요.
퀘스트는 개발자/학습자를 위한 것이어야 하며, 달성 가능하고 동기부여가 되어야 합니다.

다음 JSON 형식으로 정확히 응답해주세요:
[
  {{
    "title": "퀘스트 제목 (간결하게)",
    "description": "퀘스트 설명 (한 문장)",
    "xp_reward": 20,
    "points_reward": 2
  }},
  {{
    "title": "퀘스트 제목 (간결하게)",
    "description": "퀘스트 설명 (한 문장)",
    "xp_reward": 30,
    "points_reward": 3
  }}
]

**보상 규칙 (반드시 준수):**
- XP: 최소 10, 최대 50
- 포인트: 최소 1, 최대 5
- 난이도에 따라 조정:
  • 쉬운 퀘스트: 10-20 XP, 1-2 포인트
  • 보통 퀘스트: 20-35 XP, 2-4 포인트
  • 어려운 퀘스트: 35-50 XP, 4-5 포인트"""

        # OpenAI API 호출
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "당신은 게임 퀘스트 생성 전문가입니다. 항상 JSON 형식으로만 응답합니다."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=500
        )

        # 응답 파싱
        content = response.choices[0].message.content.strip()

        # JSON 추출 (코드 블록 제거)
        if '```json' in content:
            content = content.split('```json')[1].split('```')[0].strip()
        elif '```' in content:
            content = content.split('```')[1].split('```')[0].strip()

        quests_data = json.loads(content)

        return quests_data

    except Exception as e:
        print(f"AI 퀘스트 생성 오류: {e}")
        return None


def generate_hero_message(user):
    """
    OpenAI API를 사용하여 학습 격려 히어로 메시지 생성

    Args:
        user: User 객체

    Returns:
        dict: {"title": "메인 메시지", "subtitle": "보조 메시지"}
    """
    try:
        from openai import OpenAI

        # API 키가 없으면 기본 메시지 사용
        if not settings.OPENAI_API_KEY:
            print("⚠️ OPENAI_API_KEY가 설정되지 않음")
            return None

        print(f"✅ OpenAI API 키 확인됨")

        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        # 사용자 프로필 정보 가져오기
        profile = UserProfile.objects.filter(user=user).first()
        print(f"📊 프로필 정보: {profile}")

        current_level_xp = profile.get_current_level_xp() if profile else 0
        level_max_xp = profile.get_level_max_xp() if profile else 100
        print(f"📈 현재 레벨 XP: {current_level_xp}/{level_max_xp}")

        # LLM에게 보낼 프롬프트
        prompt = f"""당신은 학습자를 격려하는 동기부여 전문가입니다.

사용자 정보:
- 레벨: {profile.level if profile else 1}
- 현재 레벨 내 XP: {current_level_xp}/{level_max_xp}
- 총 누적 XP: {profile.xp if profile else 0}

사용자를 격려하고 동기부여할 수 있는 짧은 메시지를 생성해주세요.

**요구사항:**
1. **title**: 성장을 격려하는 메시지 (이모지 포함, 20자 이내)
   - 예: "🚀 멋지게 성장 중이에요!", "💪 꾸준함이 빛나는 순간!", "✨ 레벨업이 코앞이에요!"

2. **subtitle**: 동기부여 메시지 (이모지 포함, 25자 이내)
   - 예: "오늘도 한 걸음 더 나아가고 있어요 🔥", "당신의 노력이 빛을 발하고 있어요 ✨"

다음 JSON 형식으로 응답해주세요:
{{
  "title": "여기에 창의적인 격려 메시지",
  "subtitle": "여기에 동기부여 메시지"
}}

**중요:** 매번 다르고 창의적인 메시지를 만들어주세요. 긍정적이고 친근한 톤으로 작성해주세요!"""

        # OpenAI API 호출
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "당신은 학습자를 격려하는 전문가입니다. 항상 JSON 형식으로만 응답합니다."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.9,
            max_tokens=200
        )

        # 응답 파싱
        content = response.choices[0].message.content.strip()

        # JSON 추출 (코드 블록 제거)
        if '```json' in content:
            content = content.split('```json')[1].split('```')[0].strip()
        elif '```' in content:
            content = content.split('```')[1].split('```')[0].strip()

        message_data = json.loads(content)

        return message_data

    except Exception as e:
        print(f"AI 히어로 메시지 생성 오류: {e}")
        return None


# 간단한 퀘스트 템플릿 (AI 생성 실패 시 사용)
QUEST_TEMPLATES = [
    {
        "title": "코드 마스터",
        "description": "오늘 코드를 3회 이상 커밋하세요",
        "xp_reward": 30,
        "points_reward": 3,
    },
    {
        "title": "학습의 시간",
        "description": "새로운 기술 문서를 읽고 학습하세요",
        "xp_reward": 20,
        "points_reward": 2,
    },
    {
        "title": "버그 헌터",
        "description": "버그를 1개 이상 수정하세요",
        "xp_reward": 40,
        "points_reward": 4,
    },
    {
        "title": "코드 리뷰어",
        "description": "동료의 코드를 리뷰하고 피드백을 남기세요",
        "xp_reward": 25,
        "points_reward": 3,
    },
    {
        "title": "테스트 작성가",
        "description": "새로운 테스트 케이스를 작성하세요",
        "xp_reward": 35,
        "points_reward": 4,
    },
    {
        "title": "문서화 달인",
        "description": "코드에 주석이나 문서를 추가하세요",
        "xp_reward": 22,
        "points_reward": 2,
    },
    {
        "title": "리팩토링 마스터",
        "description": "레거시 코드를 개선하세요",
        "xp_reward": 45,
        "points_reward": 5,
    },
    {
        "title": "협업의 달인",
        "description": "팀원과 함께 페어 프로그래밍을 해보세요",
        "xp_reward": 32,
        "points_reward": 3,
    },
]


def generate_daily_quests(user, target_date=None):
    """
    사용자를 위한 일일 퀘스트 생성

    Args:
        user: User 객체
        target_date: 퀘스트 날짜 (기본값: 오늘)

    Returns:
        생성된 퀘스트 리스트
    """
    if target_date is None:
        target_date = date.today()

    # 이미 오늘 퀘스트가 있는지 확인
    existing_quests = DailyQuest.objects.filter(
        user=user,
        date=target_date
    )

    if existing_quests.exists():
        return list(existing_quests)

    quests = []

    # 1. 일일 출석 퀘스트 (항상 생성)
    daily_login, created = DailyQuest.objects.get_or_create(
        user=user,
        quest_type='daily_login',
        date=target_date,
        defaults={
            'title': "일일 출석",
            'description': "오늘 하루도 화이팅! 출석 체크를 완료하세요",
            'xp_reward': 10,
            'points_reward': 1,
        }
    )
    quests.append(daily_login)

    # 2. AI 생성 퀘스트 2개
    quest_data_list = None

    # AI로 퀘스트 생성 시도
    if settings.USE_AI_QUEST_GENERATION and settings.OPENAI_API_KEY:
        quest_data_list = generate_ai_quests_with_llm(user)

    # AI 생성 실패시 템플릿 사용
    if not quest_data_list:
        selected_templates = random.sample(QUEST_TEMPLATES, 2)
        quest_data_list = selected_templates

    for idx, quest_data in enumerate(quest_data_list):
        # 각 퀘스트에 고유한 식별자 추가
        quest_code = f"ai_generated_{idx}"

        quest, created = DailyQuest.objects.get_or_create(
            user=user,
            date=target_date,
            quest_type=quest_code,
            defaults={
                'title': quest_data['title'],
                'description': quest_data['description'],
                'xp_reward': quest_data['xp_reward'],
                'points_reward': quest_data['points_reward'],
            }
        )
        quests.append(quest)

    return quests


def get_or_generate_daily_quests(user, target_date=None, auto_complete_login=True):
    """
    사용자의 오늘 퀘스트를 가져오거나 생성

    Args:
        user: User 객체
        target_date: 퀘스트 날짜 (기본값: 오늘)
        auto_complete_login: 일일 출석 자동 완료 여부

    Returns:
        오늘의 퀘스트 리스트 (최대 3개)
    """
    if target_date is None:
        target_date = date.today()

    # 기존 퀘스트 조회
    quests = DailyQuest.objects.filter(
        user=user,
        date=target_date
    ).order_by('is_completed', 'id')

    # 없으면 생성
    if not quests.exists():
        quests = generate_daily_quests(user, target_date)
    else:
        quests = list(quests)

    # 일일 출석 자동 완료
    if auto_complete_login:
        for quest in quests:
            if quest.quest_type == 'daily_login' and not quest.is_completed:
                quest.complete()
                print(f"✅ 일일 출석 자동 완료! +{quest.xp_reward} XP, +{quest.points_reward} 포인트")

    return quests


def complete_quest(quest_id, user):
    """
    퀘스트 완료 처리

    Args:
        quest_id: 퀘스트 ID
        user: User 객체

    Returns:
        (success: bool, message: str, quest: DailyQuest or None)
    """
    try:
        quest = DailyQuest.objects.get(id=quest_id, user=user)

        if quest.is_completed:
            return False, "이미 완료된 퀘스트입니다.", quest

        # 퀘스트 완료 (보상 지급 포함)
        success = quest.complete()

        if success:
            return True, f"퀘스트 완료! +{quest.xp_reward} XP, +{quest.points_reward} 포인트", quest
        else:
            return False, "퀘스트 완료 처리 중 오류가 발생했습니다.", quest

    except DailyQuest.DoesNotExist:
        return False, "퀘스트를 찾을 수 없습니다.", None
