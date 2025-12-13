#!/usr/bin/env python
import os
import django
import json

# Django 설정 초기화
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "flash_server.settings")
django.setup()

from django.contrib.auth.models import User
from django.test import Client
from rest_framework_simplejwt.tokens import RefreshToken

print("=" * 60)
print("Flash AI - Gamification API Testing")
print("=" * 60)

# Setup test user
test_user, _ = User.objects.get_or_create(
    username="api_test_user",
    defaults={"email": "api@test.com"}
)

# Set password
test_user.set_password("testpass123")
test_user.save()

print(f"\n[Test User Setup]")
print(f"[OK] User created: {test_user.username} (ID: {test_user.id})")

# Create JWT tokens
refresh = RefreshToken.for_user(test_user)
access_token = str(refresh.access_token)

print(f"[OK] JWT Token generated")

# Setup Django test client
client = Client()

# Test 1: Get gamification profile
print("\n[TEST 1: GET /api/v1/gami/profile]")
response = client.get(
    "/api/v1/gami/profile",
    HTTP_AUTHORIZATION=f"Bearer {access_token}"
)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"[OK] Profile Retrieved:")
    print(f"  - Level: {data.get('level')}")
    print(f"  - XP: {data.get('xp')}")
    print(f"  - Points: {data.get('points')}")
    print(f"  - XP to Next Level: {data.get('xp_to_next_level')}")
else:
    print(f"[ERROR] {response.content}")

# Test 2: Get badges list
print("\n[TEST 2: GET /api/v1/gami/badges]")
response = client.get(
    "/api/v1/gami/badges",
    HTTP_AUTHORIZATION=f"Bearer {access_token}"
)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"[OK] Badges Retrieved: {len(data.get('badges', []))} badges")
    for badge in data.get('badges', [])[:3]:
        print(f"  - {badge.get('name')} ({badge.get('rarity')})")
else:
    print(f"[ERROR] {response.content}")

# Test 3: Get leaderboard
print("\n[TEST 3: GET /api/v1/gami/leaderboard]")
response = client.get(
    "/api/v1/gami/leaderboard",
    HTTP_AUTHORIZATION=f"Bearer {access_token}"
)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"[OK] Leaderboard Retrieved: {len(data.get('leaderboard', []))} users")
    for entry in data.get('leaderboard', [])[:3]:
        print(f"  Rank {entry.get('rank')}: {entry.get('username')} - {entry.get('score')} points")
else:
    print(f"[ERROR] {response.content}")

print("\n" + "=" * 60)
print("[All API Tests Completed]")
print("=" * 60)
