from django.shortcuts import render
from django.db import transaction
from django.utils import timezone
from datetime import datetime, timedelta
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import (
    UserProfile, EventType, UserEvent,
    Badge, UserBadge, Reward, UserReward, Leaderboard, DailyQuest
)
from .quest_generator import get_or_generate_daily_quests, complete_quest, generate_hero_message
from .serializers import (
    UserProfileSerializer, EventCreateSerializer, UserEventSerializer,
    BadgeSerializer, RedeemRequestSerializer, UserRewardSerializer,
    LeaderboardSerializer
)


def home(request):
    """
    Gamification 메인 화면을 렌더링하는 뷰
    """
    # 로그인한 사용자인 경우 실제 데이터 사용
    if request.user.is_authenticated:
        profile, _ = UserProfile.objects.get_or_create(user=request.user)

        # 사용자가 획득한 배지 수
        earned_badges = UserBadge.objects.filter(user=request.user).count()
        total_badges = Badge.objects.filter(is_active=True).count()

        # XP 관련 계산
        current_level_xp = profile.get_current_level_xp()
        level_max_xp = profile.get_level_max_xp()
        xp_percentage = (current_level_xp / level_max_xp * 100) if level_max_xp > 0 else 0

        # 오늘의 일일 퀘스트 조회/생성
        daily_quests = get_or_generate_daily_quests(request.user)

        # AI 히어로 메시지 생성
        hero_message = generate_hero_message(request.user)
        print(f"🤖 AI 히어로 메시지 결과: {hero_message}")
        if not hero_message:
            # AI 생성 실패시 기본 메시지
            print("⚠️ AI 메시지 생성 실패, 기본 메시지 사용")
            hero_message = {
                "title": f"🔥 오늘도 성장 중! 현재 경험치 {current_level_xp}/{level_max_xp}",
                "subtitle": "성장 게이지가 차오르고 있어요 🔋"
            }

        # 획득한 배지 조회
        user_badges = UserBadge.objects.filter(user=request.user).select_related('badge').order_by('-earned_at')[:6]

        # 미획득 배지 조회
        earned_badge_ids = UserBadge.objects.filter(user=request.user).values_list('badge_id', flat=True)
        available_badges = Badge.objects.filter(is_active=True).exclude(id__in=earned_badge_ids)[:6]

        # 리워드 조회
        rewards = Reward.objects.filter(is_active=True)[:3]

        # 리더보드 (간단한 전체 순위)
        from django.db.models import F
        all_profiles = UserProfile.objects.select_related('user').order_by('-points')

        # 현재 사용자 순위 찾기
        user_rank = 1
        for idx, p in enumerate(all_profiles, 1):
            if p.user == request.user:
                user_rank = idx
                break

        # 상위 3명
        top_users = all_profiles[:3]

        context = {
            'page_title': '메인 화면',
            'user_name': request.user.username,
            'user_level': profile.level,
            'user_xp': current_level_xp,
            'user_xp_max': level_max_xp,
            'user_xp_percentage': round(xp_percentage, 1),
            'user_points': profile.points,
            'user_rank': user_rank,
            'badges_earned': earned_badges,
            'badges_total': total_badges,
            'daily_quests': daily_quests,  # 일일 퀘스트로 변경
            'user_badges': user_badges,
            'available_badges': available_badges,
            'rewards': rewards,
            'top_users': top_users,
            'hero_title': hero_message['title'],
            'hero_subtitle': hero_message['subtitle'],
        }
    else:
        # 비로그인 사용자는 기본값
        context = {
            'page_title': '메인 화면',
            'user_name': '게스트',
            'user_level': 1,
            'user_xp': 0,
            'user_xp_max': 100,
            'user_xp_percentage': 0,
            'user_points': 0,
            'user_rank': 0,
            'badges_earned': 0,
            'badges_total': Badge.objects.filter(is_active=True).count(),
            'daily_quests': [],
            'user_badges': [],
            'available_badges': Badge.objects.filter(is_active=True)[:6],
            'rewards': Reward.objects.filter(is_active=True)[:3],
            'top_users': UserProfile.objects.select_related('user').order_by('-points')[:3],
        }

    return render(request, 'gami_home.html', context)


class ProfileAPIView(APIView):
    """
    GET /api/v1/gami/profile
    사용자 프로필 조회 (포인트, 레벨, XP)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        serializer = UserProfileSerializer(profile)
        return Response(serializer.data, status=status.HTTP_200_OK)


class EventAPIView(APIView):
    """
    POST /api/v1/gami/events
    이벤트 수집 (퀴즈 완료, 커밋 완료, 첫 빌드 등)
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = EventCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        event_code = serializer.validated_data['event_code']
        metadata = serializer.validated_data.get('metadata', {})

        try:
            with transaction.atomic():
                # 이벤트 타입 조회
                event_type = EventType.objects.get(code=event_code, is_active=True)

                # 사용자 프로필 가져오기 또는 생성
                profile, _ = UserProfile.objects.get_or_create(user=request.user)

                # 이벤트 기록 생성
                user_event = UserEvent.objects.create(
                    user=request.user,
                    event_type=event_type,
                    metadata=metadata
                )

                # 경험치 및 포인트 지급
                if event_type.xp_reward > 0:
                    profile.add_xp(event_type.xp_reward)
                if event_type.points_reward > 0:
                    profile.add_points(event_type.points_reward)

                # 응답 데이터
                response_data = {
                    'event': UserEventSerializer(user_event).data,
                    'profile': UserProfileSerializer(profile).data,
                    'rewards': {
                        'xp': event_type.xp_reward,
                        'points': event_type.points_reward
                    }
                }

                return Response(response_data, status=status.HTTP_201_CREATED)

        except EventType.DoesNotExist:
            return Response(
                {'error': f"이벤트 '{event_code}'를 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BadgeAPIView(APIView):
    """
    GET /api/v1/gami/badges
    보유/획득 가능 배지 목록
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # 모든 활성 배지 조회
        badges = Badge.objects.filter(is_active=True)
        serializer = BadgeSerializer(
            badges,
            many=True,
            context={'request': request}
        )

        # 획득한 배지와 미획득 배지 분리
        earned_badges = [b for b in serializer.data if b['is_earned']]
        available_badges = [b for b in serializer.data if not b['is_earned']]

        return Response({
            'earned': earned_badges,
            'available': available_badges,
            'total_earned': len(earned_badges),
            'total_available': len(available_badges)
        }, status=status.HTTP_200_OK)


class RedeemAPIView(APIView):
    """
    POST /api/v1/gami/redeem
    리워드 교환 (쿠폰/역할)
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = RedeemRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        reward_id = serializer.validated_data['reward_id']

        try:
            with transaction.atomic():
                # 리워드 조회
                reward = Reward.objects.select_for_update().get(
                    id=reward_id,
                    is_active=True
                )

                # 사용자 프로필 조회
                profile = UserProfile.objects.select_for_update().get(user=request.user)

                # 포인트 충분한지 확인
                if profile.points < reward.points_cost:
                    return Response(
                        {'error': '포인트가 부족합니다.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # 재고 확인
                if reward.stock == 0:
                    return Response(
                        {'error': '재고가 부족합니다.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # 포인트 차감
                profile.points -= reward.points_cost
                profile.save()

                # 재고 차감 (무제한이 아닌 경우)
                if reward.stock > 0:
                    reward.stock -= 1
                    reward.save()

                # 리워드 교환 기록
                user_reward = UserReward.objects.create(
                    user=request.user,
                    reward=reward,
                    status='pending'
                )

                return Response({
                    'message': '리워드 교환이 완료되었습니다.',
                    'user_reward': UserRewardSerializer(user_reward).data,
                    'remaining_points': profile.points
                }, status=status.HTTP_201_CREATED)

        except Reward.DoesNotExist:
            return Response(
                {'error': '유효하지 않은 리워드입니다.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except UserProfile.DoesNotExist:
            return Response(
                {'error': '사용자 프로필을 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LeaderboardAPIView(APIView):
    """
    GET /api/v1/gami/leaderboard
    리더보드 조회 (기간/필터 지원)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # 쿼리 파라미터
        period = request.query_params.get('period', 'weekly')  # daily, weekly, monthly, all_time
        limit = int(request.query_params.get('limit', 10))

        # 기간 설정
        today = timezone.now().date()

        if period == 'daily':
            period_start = today
            period_end = today
        elif period == 'weekly':
            period_start = today - timedelta(days=today.weekday())
            period_end = period_start + timedelta(days=6)
        elif period == 'monthly':
            period_start = today.replace(day=1)
            next_month = period_start.replace(day=28) + timedelta(days=4)
            period_end = next_month - timedelta(days=next_month.day)
        else:  # all_time
            period_start = datetime(2000, 1, 1).date()
            period_end = today

        # 리더보드 조회 (스냅샷이 있으면 사용, 없으면 실시간 계산)
        leaderboard = Leaderboard.objects.filter(
            period_type=period,
            period_start=period_start,
            period_end=period_end
        ).order_by('rank')[:limit]

        if not leaderboard.exists():
            # 실시간 리더보드 계산
            leaderboard_data = self._calculate_realtime_leaderboard(
                period_start, period_end, limit
            )
        else:
            serializer = LeaderboardSerializer(
                leaderboard,
                many=True,
                context={'request': request}
            )
            leaderboard_data = serializer.data

        return Response({
            'period': period,
            'period_start': period_start,
            'period_end': period_end,
            'leaderboard': leaderboard_data
        }, status=status.HTTP_200_OK)

    def _calculate_realtime_leaderboard(self, start_date, end_date, limit):
        """실시간 리더보드 계산"""
        from django.db.models import Sum, Count

        # 기간 내 이벤트 기준으로 점수 계산
        users_scores = UserEvent.objects.filter(
            completed_at__date__gte=start_date,
            completed_at__date__lte=end_date
        ).values('user').annotate(
            score=Sum('event_type__points_reward')
        ).order_by('-score')[:limit]

        result = []
        for idx, item in enumerate(users_scores, 1):
            from django.contrib.auth.models import User
            user = User.objects.get(id=item['user'])
            result.append({
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email
                },
                'rank': idx,
                'score': item['score'] or 0,
                'is_current_user': user.id == self.request.user.id
            })

        return result


class CompleteQuestAPIView(APIView):
    """
    POST /api/v1/gami/quests/complete
    일일 퀘스트 완료 처리
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        quest_id = request.data.get('quest_id')

        if not quest_id:
            return Response(
                {'error': 'quest_id가 필요합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        success, message, quest = complete_quest(quest_id, request.user)

        if success:
            # 업데이트된 프로필 정보 가져오기
            profile = UserProfile.objects.get(user=request.user)

            return Response({
                'message': message,
                'quest': {
                    'id': quest.id,
                    'title': quest.title,
                    'xp_reward': quest.xp_reward,
                    'points_reward': quest.points_reward,
                    'is_completed': quest.is_completed,
                },
                'profile': {
                    'level': profile.level,
                    'xp': profile.xp,
                    'xp_to_next_level': profile.xp_to_next_level,
                    'points': profile.points,
                }
            }, status=status.HTTP_200_OK)
        else:
            return Response(
                {'error': message},
                status=status.HTTP_400_BAD_REQUEST
            )
