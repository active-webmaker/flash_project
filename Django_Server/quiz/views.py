from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from .models import Topic, Difficulty, Question, QuizSession, QuizProfile
from .serializers import TopicSerializer, DifficultySerializer, QuestionSerializer, QuizSessionSerializer
from .quiz_engine import QuizEngine

class QuizPoolsView(APIView):
    """
    Provides a list of available quiz pools (topics and difficulties).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        """
        Returns a list of all available topics and difficulties.
        """
        topics = Topic.objects.all()
        difficulties = Difficulty.objects.all()

        # A good practice would be to populate initial data for Topic and Difficulty
        # For now, if they are empty, we can return an empty list or a message.
        if not topics.exists() or not difficulties.exists():
            # Let's add some initial data for demonstration purposes
            self.initialize_pools()
            topics = Topic.objects.all()
            difficulties = Difficulty.objects.all()

        topic_serializer = TopicSerializer(topics, many=True)
        difficulty_serializer = DifficultySerializer(difficulties, many=True)

        return Response({
            'topics': topic_serializer.data,
            'difficulties': difficulty_serializer.data
        }, status=status.HTTP_200_OK)

    def initialize_pools(self):
        """A helper to create initial data if it doesn't exist."""
        # Initial difficulties
        if not Difficulty.objects.exists():
            Difficulty.objects.create(name='beginner', level=1)
            Difficulty.objects.create(name='intermediate', level=2)
            Difficulty.objects.create(name='advanced', level=3)

        # Initial topics from the learning path
        if not Topic.objects.exists():
            beginner_topics = [
                "Variables and Data Types", "Conditional Statements (if/else)", "Loops (for/while)",
                "Lists and Tuples", "Dictionaries", "Functions Basics",
                "String Manipulation", "File I/O", "Basic Exception Handling"
            ]
            for topic_name in beginner_topics:
                Topic.objects.get_or_create(name=topic_name)