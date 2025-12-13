from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status
from .models import UserProfile, Badge
from .badge_checker import check_and_award_badges

class GamificationTests(APITestCase):
    def setUp(self):
        # 테스트용 사용자 및 프로필 생성
        self.username = "testuser_gami"
        self.password = "testpassword123"
        self.user = User.objects.create_user(username=self.username, password=self.password)
        self.profile = UserProfile.objects.create(user=self.user)
        
        # JWT 토큰 획득 및 API 클라이언트 인증 설정
        token_url = '/api/v1/auth/login'
        response = self.client.post(token_url, {'username': self.username, 'password': self.password}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        access_token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + access_token)

    def test_user_profile_creation(self):
        """
        User가 생성될 때 UserProfile이 자동으로 생성되는지 테스트합니다.
        (실제로는 signal로 처리하는 것이 더 좋지만, 여기서는 get_or_create로직을 테스트)
        """
        new_user = User.objects.create_user(username="newbie")
        profile, created = UserProfile.objects.get_or_create(user=new_user)
        self.assertTrue(created)
        self.assertEqual(profile.level, 1)
        self.assertEqual(profile.xp, 0)

    def test_add_xp_and_level_up(self):
        """
        XP를 추가했을 때 레벨업이 정상적으로 동작하는지 테스트합니다.
        (레벨업 기준: 100XP 당 1레벨)
        """
        self.profile.add_xp(150)
        # Refresh from DB
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.xp, 150)
        self.assertEqual(self.profile.level, 2) # 100XP로 레벨 2 달성

        self.profile.add_xp(150)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.xp, 300)
        self.assertEqual(self.profile.level, 4) # 누적 300XP로 레벨 4 달성

    def test_badge_award_by_level(self):
        """
        특정 레벨에 도달했을 때 배지가 자동으로 지급되는지 테스트합니다.
        """
        # 레벨 5 달성 배지 생성
        level_5_badge = Badge.objects.create(
            name="Level 5 Achiever",
            code="LVL_5",
            description="Reached level 5.",
            condition_type='level',
            condition_value='5',
            xp_reward=50
        )

        # 레벨 5가 되기 전에는 배지가 없음
        self.profile.add_xp(399) # Level 4 (XP: 399)
        self.profile.refresh_from_db()
        check_and_award_badges(self.user)
        self.assertFalse(self.user.gami_badges.filter(badge=level_5_badge).exists())

        # 레벨 5 달성
        self.profile.add_xp(1) # Level 5 (XP: 400)
        self.profile.refresh_from_db()
        
        # add_xp 메서드 내부에서 check_and_award_badges가 호출되어 배지가 지급됩니다.
        # 따라서, 데이터베이스에 배지가 정상적으로 기록되었는지만 확인합니다.
        self.assertTrue(self.user.gami_badges.filter(badge=level_5_badge).exists())

    def test_get_profile_api(self):
        """
        /api/v1/gami/profile API가 프로필 정보를 정확히 반환하는지 테스트합니다.
        """
        url = '/api/v1/gami/profile'
        self.profile.add_xp(50)
        self.profile.refresh_from_db()

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['level'], 1)
        self.assertEqual(response.data['xp'], 50)

    def test_get_badges_api(self):
        """
        /api/v1/gami/badges API가 배지 목록을 정확히 반환하는지 테스트합니다.
        """
        # 테스트용 배지 2개 생성
        badge1 = Badge.objects.create(name="Badge 1", code="B1", description="Desc 1")
        badge2 = Badge.objects.create(name="Badge 2", code="B2", description="Desc 2")

        # 사용자에게 badge1 지급
        self.user.gami_badges.create(badge=badge1)

        url = '/api/v1/gami/badges'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('badges', response.data)

        all_badges = response.data['badges']
        earned_badges = [b for b in all_badges if b['is_earned']]
        available_badges = [b for b in all_badges if not b['is_earned']]

        self.assertEqual(len(earned_badges), 1)
        self.assertEqual(earned_badges[0]['name'], "Badge 1")
        self.assertEqual(len(available_badges), 1)
        self.assertEqual(available_badges[0]['name'], "Badge 2")