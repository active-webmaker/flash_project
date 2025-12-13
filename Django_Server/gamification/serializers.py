from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    UserProfile, EventType, UserEvent,
    Badge, UserBadge, Reward, UserReward, Leaderboard
)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']


class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    xp_percentage = serializers.SerializerMethodField()
    current_level_xp = serializers.SerializerMethodField()
    xp_to_next_level = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = [
            'user', 'points', 'level', 'xp', 'current_level_xp', 'xp_to_next_level',
            'xp_percentage', 'created_at', 'updated_at'
        ]

    def get_current_level_xp(self, obj):
        """현재 레벨 내에서의 XP"""
        return obj.get_current_level_xp()

    def get_xp_to_next_level(self, obj):
        """다음 레벨까지 필요한 XP"""
        return obj.get_xp_to_next_level()

    def get_xp_percentage(self, obj):
        """현재 레벨 진행도 퍼센트"""
        level_max_xp = obj.get_level_max_xp()
        if level_max_xp == 0:
            return 100
        return round((obj.get_current_level_xp() / level_max_xp) * 100, 1)


class EventTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventType
        fields = ['id', 'name', 'code', 'xp_reward', 'points_reward', 'description']


class UserEventSerializer(serializers.ModelSerializer):
    event_type = EventTypeSerializer(read_only=True)

    class Meta:
        model = UserEvent
        fields = ['id', 'event_type', 'metadata', 'completed_at']


class EventCreateSerializer(serializers.Serializer):
    """이벤트 생성용 Serializer"""
    event_code = serializers.CharField(max_length=50)
    metadata = serializers.JSONField(required=False, default=dict)

    def validate_event_code(self, value):
        """이벤트 코드가 존재하는지 검증"""
        if not EventType.objects.filter(code=value, is_active=True).exists():
            raise serializers.ValidationError(f"이벤트 코드 '{value}'를 찾을 수 없습니다.")
        return value


class BadgeSerializer(serializers.ModelSerializer):
    is_earned = serializers.SerializerMethodField()
    earned_at = serializers.SerializerMethodField()

    class Meta:
        model = Badge
        fields = [
            'id', 'name', 'code', 'description', 'icon',
            'xp_reward', 'points_reward', 'rarity',
            'is_earned', 'earned_at'
        ]

    def get_is_earned(self, obj):
        """사용자가 이 배지를 획득했는지"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return UserBadge.objects.filter(user=request.user, badge=obj).exists()
        return False

    def get_earned_at(self, obj):
        """배지 획득 시간"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            user_badge = UserBadge.objects.filter(user=request.user, badge=obj).first()
            if user_badge:
                return user_badge.earned_at
        return None


class UserBadgeSerializer(serializers.ModelSerializer):
    badge = BadgeSerializer(read_only=True)

    class Meta:
        model = UserBadge
        fields = ['id', 'badge', 'earned_at']


class RewardSerializer(serializers.ModelSerializer):
    can_redeem = serializers.SerializerMethodField()

    class Meta:
        model = Reward
        fields = [
            'id', 'name', 'description', 'icon',
            'points_cost', 'reward_type', 'stock',
            'can_redeem'
        ]

    def get_can_redeem(self, obj):
        """사용자가 이 리워드를 교환할 수 있는지"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            profile = UserProfile.objects.filter(user=request.user).first()
            if profile:
                has_points = profile.points >= obj.points_cost
                has_stock = obj.stock == -1 or obj.stock > 0
                return has_points and has_stock and obj.is_active
        return False


class RedeemRequestSerializer(serializers.Serializer):
    """리워드 교환 요청 Serializer"""
    reward_id = serializers.IntegerField()

    def validate_reward_id(self, value):
        """리워드가 존재하고 활성화 상태인지 검증"""
        if not Reward.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError("유효하지 않은 리워드입니다.")
        return value


class UserRewardSerializer(serializers.ModelSerializer):
    reward = RewardSerializer(read_only=True)

    class Meta:
        model = UserReward
        fields = ['id', 'reward', 'status', 'redeemed_at', 'metadata']


class LeaderboardSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    is_current_user = serializers.SerializerMethodField()

    class Meta:
        model = Leaderboard
        fields = [
            'user', 'period_type', 'period_start', 'period_end',
            'rank', 'score', 'is_current_user'
        ]

    def get_is_current_user(self, obj):
        """현재 로그인한 사용자인지"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.user == request.user
        return False

class LeaderboardEntrySerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    score = serializers.IntegerField(source='xp')
    rank = serializers.IntegerField()

    class Meta:
        model = UserProfile
        fields = ('rank', 'user', 'score')
