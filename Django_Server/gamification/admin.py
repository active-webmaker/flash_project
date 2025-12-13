from django.contrib import admin
from .models import (
    UserProfile, EventType, UserEvent,
    Badge, UserBadge, Reward, UserReward, Leaderboard, DailyQuest
)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'level', 'xp', 'points', 'updated_at']
    list_filter = ['level', 'created_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(EventType)
class EventTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'xp_reward', 'points_reward', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'code']


@admin.register(UserEvent)
class UserEventAdmin(admin.ModelAdmin):
    list_display = ['user', 'event_type', 'completed_at']
    list_filter = ['event_type', 'completed_at']
    search_fields = ['user__username']
    readonly_fields = ['completed_at']


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ['icon', 'name', 'rarity', 'condition_type', 'condition_value', 'xp_reward', 'points_reward', 'is_active']
    list_filter = ['rarity', 'condition_type', 'is_active']
    search_fields = ['name', 'code', 'description']
    fieldsets = (
        ('기본 정보', {
            'fields': ('name', 'code', 'icon', 'description', 'rarity', 'is_active')
        }),
        ('보상', {
            'fields': ('xp_reward', 'points_reward')
        }),
        ('획득 조건', {
            'fields': ('condition_type', 'condition_value'),
            'description': '''
                <strong>조건 설정 방법:</strong><br>
                • <strong>레벨 도달:</strong> condition_value에 레벨 숫자 입력 (예: 5)<br>
                • <strong>누적 XP:</strong> condition_value에 XP 숫자 입력 (예: 500)<br>
                • <strong>누적 포인트:</strong> condition_value에 포인트 숫자 입력 (예: 100)<br>
                • <strong>특정 퀘스트 완료:</strong> condition_value에 퀘스트 타입 코드 입력<br>
                &nbsp;&nbsp;→ 사용 가능한 코드: <code>daily_login</code> (일일 출석), <code>ai_generated_0</code>, <code>ai_generated_1</code> (AI 퀘스트)<br>
                &nbsp;&nbsp;→ DailyQuest 모델의 quest_type 값 참조<br>
                • <strong>퀘스트 완료 횟수:</strong> condition_value에 횟수 입력 (예: 10)<br>
                • <strong>특정 이벤트 횟수:</strong> condition_value에 "이벤트코드:횟수" 형식으로 입력<br>
                &nbsp;&nbsp;→ 사용 가능한 코드: EventType 모델 참조 (<a href="/admin/gamification/eventtype/" target="_blank">이벤트 타입 보기</a>)<br>
                • <strong>수동 지급:</strong> 자동 지급 없음, 관리자가 직접 지급
            '''
        }),
    )


@admin.register(UserBadge)
class UserBadgeAdmin(admin.ModelAdmin):
    list_display = ['user', 'badge', 'earned_at']
    list_filter = ['badge', 'earned_at']
    search_fields = ['user__username', 'badge__name']
    readonly_fields = ['earned_at']


@admin.register(Reward)
class RewardAdmin(admin.ModelAdmin):
    list_display = ['icon', 'name', 'reward_type', 'points_cost', 'stock', 'is_active']
    list_filter = ['reward_type', 'is_active']
    search_fields = ['name']


@admin.register(UserReward)
class UserRewardAdmin(admin.ModelAdmin):
    list_display = ['user', 'reward', 'status', 'redeemed_at']
    list_filter = ['status', 'redeemed_at']
    search_fields = ['user__username', 'reward__name']
    readonly_fields = ['redeemed_at']


@admin.register(Leaderboard)
class LeaderboardAdmin(admin.ModelAdmin):
    list_display = ['user', 'period_type', 'rank', 'score', 'period_start', 'period_end']
    list_filter = ['period_type', 'period_start']
    search_fields = ['user__username']
    readonly_fields = ['created_at']


@admin.register(DailyQuest)
class DailyQuestAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'quest_type', 'date', 'is_completed', 'xp_reward', 'points_reward']
    list_filter = ['quest_type', 'is_completed', 'date']
    search_fields = ['user__username', 'title', 'quest_type']
    readonly_fields = ['completed_at', 'created_at']
    date_hierarchy = 'date'

    # quest_type을 쉽게 확인할 수 있도록 help_text 추가
    fieldsets = (
        ('퀘스트 정보', {
            'fields': ('user', 'title', 'description', 'date')
        }),
        ('퀘스트 타입 및 보상', {
            'fields': ('quest_type', 'xp_reward', 'points_reward'),
            'description': '<strong>quest_type</strong>은 배지 획득 조건에서 사용됩니다. (예: daily_login, ai_generated_0)'
        }),
        ('완료 상태', {
            'fields': ('is_completed', 'completed_at', 'created_at')
        }),
    )
