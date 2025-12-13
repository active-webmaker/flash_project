from django.urls import path
from .views import QuizPoolsView

urlpatterns = [
    path('pools/', QuizPoolsView.as_view(), name='quiz-pools'),
    # API endpoints will be added here
]
