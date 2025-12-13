from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status
from .models import Project

class ApiTests(APITestCase):
    def setUp(self):
        # 테스트를 위한 사용자 생성
        self.username = "testuser"
        self.password = "testpassword123"
        self.user = User.objects.create_user(username=self.username, password=self.password)
        
        # JWT 토큰 획득 및 API 클라이언트 인증 설정
        token_url = '/api/v1/auth/login'
        response = self.client.post(token_url, {'username': self.username, 'password': self.password}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        access_token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + access_token)

    def test_health_check(self):
        """
        /api/v1/health 엔드포인트가 200 OK를 반환하는지 테스트합니다.
        """
        # 헬스 체크는 인증이 필요 없으므로 인증을 제거하고 테스트
        self.client.credentials()
        response = self.client.get('/api/v1/health')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {'status': 'ok'})

    def test_user_registration(self):
        """
        새로운 사용자를 성공적으로 생성할 수 있는지 테스트합니다.
        """
        # 로그아웃 상태에서 테스트
        self.client.credentials() # 인증 정보 제거
        
        url = '/api/v1/auth/register'
        data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "newpassword123",
            "password2": "newpassword123"
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username="newuser").exists())

    def test_create_and_list_projects(self):
        """
        인증된 사용자가 프로젝트를 생성하고, 해당 프로젝트가 목록에 포함되는지 테스트합니다.
        """
        # 1. 프로젝트 생성
        create_url = '/api/v1/git/projects/register'
        project_data = {
            "name": "Test Project",
            "local_path": "/path/to/project"
        }
        response = self.client.post(create_url, project_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Project.objects.count(), 1)
        self.assertEqual(Project.objects.get().name, "Test Project")

        # 2. 프로젝트 목록 조회
        list_url = '/api/v1/projects'
        response = self.client.get(list_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], "Test Project")

    def test_unauthenticated_access(self):
        """
        인증되지 않은 사용자가 보호된 엔드포인트에 접근할 수 없는지 테스트합니다.
        """
        self.client.credentials() # 인증 정보 제거
        list_url = '/api/v1/projects'
        response = self.client.get(list_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)