from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class UserProfile(models.Model):
    """사용자 게이미피케이션 프로필"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='gami_profile')
    points = models.IntegerField(default=0, help_text="누적 포인트")
    level = models.IntegerField(default=1, help_text="현재 레벨")
    xp = models.IntegerField(default=0, help_text="누적 경험치")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'gami_user_profile'
        verbose_name = '사용자 프로필'
        verbose_name_plural = '사용자 프로필'

    def get_xp_for_level(self, level):
        """특정 레벨에 도달하는데 필요한 누적 XP 계산"""
        if level == 1:
            return 0
        return (level - 1) * 100

    def get_current_level_xp(self):
        """현재 레벨 내에서의 XP"""
        current_level_required = self.get_xp_for_level(self.level)
        return self.xp - current_level_required

    def get_xp_to_next_level(self):
        """다음 레벨까지 필요한 XP"""
        next_level_required = self.get_xp_for_level(self.level + 1)
        return next_level_required - self.xp

    def get_level_progress(self):
        """현재 레벨의 진행 XP (레벨업 기준점부터)"""
        return self.get_current_level_xp()

    def get_level_max_xp(self):
        """현재 레벨에서 다음 레벨까지의 총 XP"""
        return 100  # 모든 레벨이 100 XP

    def __str__(self):
        return f"{self.user.username} - Lv.{self.level} ({self.get_current_level_xp()}/100 XP, 누적: {self.xp})"

    def add_xp(self, amount):
        """경험치 추가 및 레벨업 처리"""
        self.xp += amount

        # 레벨 재계산 (누적 XP 기반)
        new_level = (self.xp // 100) + 1
        level_up = False
        if new_level != self.level:
            old_level = self.level
            self.level = new_level
            level_up = True
            print(f"[LEVEL UP] {old_level} -> {self.level}")

        self.save()

        # 레벨업이나 XP 획득 시 배지 체크
        if level_up or amount > 0:
            from .badge_checker import check_and_award_badges
            check_and_award_badges(self.user)

    def add_points(self, amount):
        """포인트 추가"""
        self.points += amount
        self.save()

        # 포인트 획득 시 배지 체크
        if amount > 0:
            from .badge_checker import check_and_award_badges
            check_and_award_badges(self.user)


class EventType(models.Model):
    """이벤트 타입 정의"""
    name = models.CharField(max_length=100, unique=True, help_text="이벤트 이름")
    code = models.CharField(max_length=50, unique=True, help_text="이벤트 코드 (예: QUIZ_COMPLETE)")
    xp_reward = models.IntegerField(default=0, help_text="지급 경험치")
    points_reward = models.IntegerField(default=0, help_text="지급 포인트")
    description = models.TextField(blank=True, help_text="이벤트 설명")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'gami_event_type'
        verbose_name = '이벤트 타입'
        verbose_name_plural = '이벤트 타입'

    def __str__(self):
        return f"{self.name} (+{self.xp_reward}XP, +{self.points_reward}P)"


class UserEvent(models.Model):
    """사용자가 완료한 이벤트 기록"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='gami_events')
    event_type = models.ForeignKey(EventType, on_delete=models.CASCADE)
    metadata = models.JSONField(default=dict, blank=True, help_text="추가 정보")
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'gami_user_event'
        verbose_name = '사용자 이벤트'
        verbose_name_plural = '사용자 이벤트'
        ordering = ['-completed_at']

    def __str__(self):
        return f"{self.user.username} - {self.event_type.name} ({self.completed_at})"


class Badge(models.Model):
    """배지 정의"""
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(help_text="배지 획득 조건")
    icon = models.CharField(max_length=10, default="🏆", help_text="이모지 아이콘")
    xp_reward = models.IntegerField(default=0, help_text="획득시 지급 XP")
    points_reward = models.IntegerField(default=0, help_text="획득시 지급 포인트")
    rarity = models.CharField(
        max_length=20,
        choices=[
            ('common', '일반'),
            ('rare', '레어'),
            ('epic', '에픽'),
            ('legendary', '전설'),
        ],
        default='common'
    )

    # 자동 획득 조건
    condition_type = models.CharField(
        max_length=50,
        choices=[
            ('level', '레벨 도달'),
            ('total_xp', '누적 XP'),
            ('total_points', '누적 포인트'),
            ('quest_complete', '특정 퀘스트 완료'),
            ('quest_count', '퀘스트 완료 횟수'),
            ('event_count', '특정 이벤트 횟수'),
            ('manual', '수동 지급'),
        ],
        default='manual',
        help_text="배지 획득 조건 유형"
    )
    condition_value = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="조건 값 (예: 레벨 5, 퀘스트코드, 횟수 등)"
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'gami_badge'
        verbose_name = '배지'
        verbose_name_plural = '배지'

    def __str__(self):
        return f"{self.icon} {self.name} ({self.rarity})"


class UserBadge(models.Model):
    """사용자가 획득한 배지"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='gami_badges')
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE)
    earned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'gami_user_badge'
        verbose_name = '사용자 배지'
        verbose_name_plural = '사용자 배지'
        unique_together = ['user', 'badge']
        ordering = ['-earned_at']

    def __str__(self):
        return f"{self.user.username} - {self.badge.name}"


class Reward(models.Model):
    """교환 가능한 리워드"""
    name = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.CharField(max_length=10, default="🎁")
    points_cost = models.IntegerField(help_text="필요 포인트")
    reward_type = models.CharField(
        max_length=20,
        choices=[
            ('coupon', '쿠폰'),
            ('role', '역할'),
            ('item', '아이템'),
        ],
        default='coupon'
    )
    metadata = models.JSONField(default=dict, blank=True, help_text="리워드 세부 정보")
    stock = models.IntegerField(default=-1, help_text="재고 (-1: 무제한)")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'gami_reward'
        verbose_name = '리워드'
        verbose_name_plural = '리워드'

    def __str__(self):
        return f"{self.icon} {self.name} ({self.points_cost}P)"


class UserReward(models.Model):
    """사용자가 교환한 리워드"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='gami_rewards')
    reward = models.ForeignKey(Reward, on_delete=models.CASCADE)
    redeemed_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', '대기중'),
            ('approved', '승인됨'),
            ('completed', '완료됨'),
            ('cancelled', '취소됨'),
        ],
        default='pending'
    )
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'gami_user_reward'
        verbose_name = '사용자 리워드'
        verbose_name_plural = '사용자 리워드'
        ordering = ['-redeemed_at']

    def __str__(self):
        return f"{self.user.username} - {self.reward.name} ({self.status})"


class Leaderboard(models.Model):
    """리더보드 스냅샷 (주간/월간)"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='gami_leaderboard')
    period_type = models.CharField(
        max_length=20,
        choices=[
            ('daily', '일일'),
            ('weekly', '주간'),
            ('monthly', '월간'),
            ('all_time', '전체'),
        ]
    )
    period_start = models.DateField()
    period_end = models.DateField()
    rank = models.IntegerField()
    score = models.IntegerField(help_text="해당 기간 획득 점수")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'gami_leaderboard'
        verbose_name = '리더보드'
        verbose_name_plural = '리더보드'
        ordering = ['period_type', 'rank']
        indexes = [
            models.Index(fields=['period_type', 'period_start', 'period_end']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.period_type} #{self.rank} ({self.score})"


class DailyQuest(models.Model):
    """일일 퀘스트 (AI 생성 또는 고정)"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='gami_daily_quests')
    title = models.CharField(max_length=200, help_text="퀘스트 제목")
    description = models.TextField(help_text="퀘스트 설명")
    quest_type = models.CharField(
        max_length=50,
        choices=[
            ('daily_login', '일일 출석'),
            ('ai_generated', 'AI 생성'),
        ],
        default='ai_generated'
    )
    xp_reward = models.IntegerField(default=30, help_text="보상 경험치 (최대 50)")
    points_reward = models.IntegerField(default=3, help_text="보상 포인트 (최대 5)")
    date = models.DateField(help_text="퀘스트 날짜")
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'gami_daily_quest'
        verbose_name = '일일 퀘스트'
        verbose_name_plural = '일일 퀘스트'
        unique_together = ['user', 'date', 'quest_type']
        ordering = ['-date', 'is_completed']
        indexes = [
            models.Index(fields=['user', 'date']),
        ]

    def __str__(self):
        status = "✅" if self.is_completed else "⏳"
        return f"{status} {self.user.username} - {self.title} ({self.date})"

    def complete(self):
        """퀘스트 완료 처리"""
        if not self.is_completed:
            self.is_completed = True
            self.completed_at = timezone.now()
            self.save()

            # 사용자 프로필에 보상 지급
            profile, _ = UserProfile.objects.get_or_create(user=self.user)
            profile.add_xp(self.xp_reward)
            profile.add_points(self.points_reward)

            return True
        return False
