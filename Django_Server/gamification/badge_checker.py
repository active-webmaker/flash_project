"""
배지 자동 획득 체크 시스템
"""
from .models import Badge, UserBadge, UserProfile, DailyQuest, UserEvent


def check_and_award_badges(user):
    """
    사용자가 획득할 수 있는 모든 배지를 체크하고 지급

    Args:
        user: User 객체

    Returns:
        새로 획득한 배지 리스트
    """
    newly_earned_badges = []

    # 이미 획득한 배지 ID 리스트
    earned_badge_ids = UserBadge.objects.filter(user=user).values_list('badge_id', flat=True)

    # 활성화된 모든 배지 중 아직 획득하지 않은 배지들 조회
    available_badges = Badge.objects.filter(
        is_active=True
    ).exclude(
        id__in=earned_badge_ids
    )

    # 사용자 프로필 정보
    profile = UserProfile.objects.filter(user=user).first()
    if not profile:
        return newly_earned_badges

    for badge in available_badges:
        if check_badge_condition(user, profile, badge):
            # 배지 지급
            user_badge = UserBadge.objects.create(
                user=user,
                badge=badge
            )

            # 배지 보상 지급
            if badge.xp_reward > 0:
                profile.add_xp(badge.xp_reward)
            if badge.points_reward > 0:
                profile.add_points(badge.points_reward)

            newly_earned_badges.append(badge)
            print(f"[BADGE] 배지 획득! {badge.name} (+{badge.xp_reward} XP, +{badge.points_reward} 포인트)")

    return newly_earned_badges


def check_badge_condition(user, profile, badge):
    """
    배지 획득 조건을 체크

    Args:
        user: User 객체
        profile: UserProfile 객체
        badge: Badge 객체

    Returns:
        조건 충족 여부 (bool)
    """
    condition_type = badge.condition_type
    condition_value = badge.condition_value

    # 수동 지급 배지는 자동으로 지급하지 않음
    if condition_type == 'manual':
        return False

    # 레벨 도달
    if condition_type == 'level':
        try:
            required_level = int(condition_value)
            return profile.level >= required_level
        except (ValueError, TypeError):
            return False

    # 누적 XP
    elif condition_type == 'total_xp':
        try:
            required_xp = int(condition_value)
            return profile.xp >= required_xp
        except (ValueError, TypeError):
            return False

    # 누적 포인트
    elif condition_type == 'total_points':
        try:
            required_points = int(condition_value)
            return profile.points >= required_points
        except (ValueError, TypeError):
            return False

    # 특정 퀘스트 완료
    elif condition_type == 'quest_complete':
        if not condition_value:
            return False
        # quest_type 코드로 완료된 퀘스트 찾기
        completed_quest = DailyQuest.objects.filter(
            user=user,
            quest_type=condition_value,
            is_completed=True
        ).exists()
        return completed_quest

    # 퀘스트 완료 횟수
    elif condition_type == 'quest_count':
        try:
            required_count = int(condition_value)
            completed_count = DailyQuest.objects.filter(
                user=user,
                is_completed=True
            ).count()
            return completed_count >= required_count
        except (ValueError, TypeError):
            return False

    # 특정 이벤트 횟수
    elif condition_type == 'event_count':
        # 형식: "이벤트코드:횟수" (예: "quiz_completed:10")
        if not condition_value or ':' not in condition_value:
            return False

        try:
            event_code, required_count_str = condition_value.split(':', 1)
            required_count = int(required_count_str)

            event_count = UserEvent.objects.filter(
                user=user,
                event_type__code=event_code
            ).count()

            return event_count >= required_count
        except (ValueError, TypeError):
            return False

    return False
