from django.urls import path
from . import views

app_name = 'gamification'

urlpatterns = [
    # Web UI
    path('', views.home, name='home'),

    # API v1 endpoints
    path('api/v1/gami/profile', views.ProfileAPIView.as_view(), name='api_profile'),
    path('api/v1/gami/events', views.EventAPIView.as_view(), name='api_events'),
    path('api/v1/gami/badges', views.BadgeAPIView.as_view(), name='api_badges'),
    path('api/v1/gami/redeem', views.RedeemAPIView.as_view(), name='api_redeem'),
    path('api/v1/gami/leaderboard', views.LeaderboardAPIView.as_view(), name='api_leaderboard'),
    path('api/v1/gami/quests/complete', views.CompleteQuestAPIView.as_view(), name='api_quest_complete'),
]
