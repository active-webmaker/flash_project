#!/usr/bin/env python
import os
import django

# Django 설정 초기화
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "flash_server.settings")
django.setup()

from django.contrib.auth.models import User
from gamification.models import UserProfile, EventType, Badge, UserBadge

print("=" * 60)
print("Flash AI Coding Agent - 게이미피케이션 시스템 테스트")
print("=" * 60)

# 테스트 사용자 생성 또는 조회
print("\n[테스트 사용자 설정]")
test_user, created = User.objects.get_or_create(
    username="gamification_test",
    defaults={"email": "gami@test.com"}
)
status = "[NEW]" if created else "[EXISTS]"
print(f"{status} {test_user.username} (ID: {test_user.id})")

# 게이미피케이션 프로필 생성 또는 조회
print("\n[게이미피케이션 프로필 초기화]")
profile, created = UserProfile.objects.get_or_create(user=test_user)
status = "[NEW]" if created else "[EXISTS]"
print(f"{status} 프로필 생성")
print(f"  초기 상태: Level={profile.level}, XP={profile.xp}, Points={profile.points}")

# 1. XP 추가 테스트
print("\n[테스트 1: XP 추가 및 레벨업]")

# 레벨업 필요 XP: 각 레벨당 100 XP
# Level 1 → Level 2: 100 XP 필요
# Level 2 → Level 3: 200 XP 필요
# Level 3 → Level 4: 300 XP 필요

print(f"\n[XP 추가 전] Level={profile.level}, XP={profile.xp}, Current Level XP={profile.get_current_level_xp()}")

# 50 XP 추가 (레벨업 안함)
print(f"\n[50 XP 추가 중...]")
profile.add_xp(50)
print(f"[결과] Level={profile.level}, XP={profile.xp}, Current Level XP={profile.get_current_level_xp()}")
print(f"   다음 레벨까지: {profile.get_xp_to_next_level()} XP 필요")

# 50 XP 추가 (레벨업 발생)
print(f"\n[50 XP 추가 중...]")
profile.add_xp(50)
print(f"[결과] Level={profile.level}, XP={profile.xp}, Current Level XP={profile.get_current_level_xp()}")
print(f"   다음 레벨까지: {profile.get_xp_to_next_level()} XP 필요")

# 100 XP 추가 (Level 3으로)
print(f"\n[100 XP 추가 중...]")
profile.add_xp(100)
print(f"[결과] Level={profile.level}, XP={profile.xp}, Current Level XP={profile.get_current_level_xp()}")
print(f"   다음 레벨까지: {profile.get_xp_to_next_level()} XP 필요")

# 2. 포인트 추가 테스트
print("\n[테스트 2: 포인트 추가]")
print(f"\n[포인트 추가 전] Points={profile.points}")

profile.add_points(50)
print(f"[결과] 50 포인트 추가: Points={profile.points}")

profile.add_points(100)
print(f"[결과] 100 포인트 추가: Points={profile.points}")

# 3. 이벤트 타입 설정
print("\n[테스트 3: 이벤트 타입 설정]")

event_types = [
    {"name": "퀴즈 완료", "code": "QUIZ_COMPLETE", "xp_reward": 25, "points_reward": 10},
    {"name": "문제 풀이", "code": "QUESTION_SOLVED", "xp_reward": 10, "points_reward": 5},
    {"name": "스트릭 달성", "code": "STREAK_7", "xp_reward": 50, "points_reward": 20},
]

for event_data in event_types:
    event, created = EventType.objects.get_or_create(
        code=event_data["code"],
        defaults={
            "name": event_data["name"],
            "xp_reward": event_data["xp_reward"],
            "points_reward": event_data["points_reward"],
            "is_active": True
        }
    )
    status = "[NEW]" if created else "[EXISTS]"
    print(f"{status} {event.name} (Code: {event.code}) - +{event.xp_reward}XP, +{event.points_reward}P")

# 4. 배지 설정
print("\n[테스트 4: 배지 설정]")

badges_data = [
    {
        "name": "첫 퀴즈",
        "code": "FIRST_QUIZ",
        "description": "첫 번째 퀴즈 완료",
        "icon": "🎯",
        "rarity": "common",
        "condition_type": "quest_count",
        "condition_value": "1"
    },
    {
        "name": "레벨 5 달성",
        "code": "LEVEL_5",
        "description": "레벨 5 도달",
        "icon": "⭐",
        "rarity": "rare",
        "condition_type": "level",
        "condition_value": "5"
    },
    {
        "name": "XP 마스터",
        "code": "XP_MASTER",
        "description": "500 XP 획득",
        "icon": "🔥",
        "rarity": "epic",
        "condition_type": "total_xp",
        "condition_value": "500"
    }
]

for badge_data in badges_data:
    badge, created = Badge.objects.get_or_create(
        code=badge_data["code"],
        defaults={
            "name": badge_data["name"],
            "description": badge_data["description"],
            "icon": badge_data["icon"],
            "rarity": badge_data["rarity"],
            "condition_type": badge_data["condition_type"],
            "condition_value": badge_data["condition_value"],
            "is_active": True
        }
    )
    status = "[NEW]" if created else "[EXISTS]"
    print(f"{status} {badge.name} ({badge.rarity}) - Condition: {badge.condition_type}")

# 5. 최종 상태 출력
print("\n" + "=" * 60)
print("게이미피케이션 시스템 테스트 완료!")
print("=" * 60)

print(f"\n[최종 사용자 프로필 상태]")
profile.refresh_from_db()
print(f"  사용자: {profile.user.username}")
print(f"  레벨: {profile.level}")
print(f"  누적 XP: {profile.xp}")
print(f"  포인트: {profile.points}")
print(f"  레벨 진행도: {profile.get_current_level_xp()}/100 XP")
print(f"  다음 레벨까지: {profile.get_xp_to_next_level()} XP 필요")

print(f"\n[이벤트 타입 통계]")
print(f"  등록된 이벤트 타입: {EventType.objects.count()}개")

print(f"\n[배지 통계]")
print(f"  등록된 배지: {Badge.objects.count()}개")
print(f"  사용자 보유 배지: {UserBadge.objects.filter(user=test_user).count()}개")

print("\n[모든 테스트 완료!]")
