from rest_framework import serializers
from .models import (
    QuizProfile, Topic, Difficulty, Question, Badge, UserBadge, QuizSession, SessionAnswer
)

class TopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Topic
        fields = '__all__'

class DifficultySerializer(serializers.ModelSerializer):
    class Meta:
        model = Difficulty
        fields = '__all__'

class QuestionSerializer(serializers.ModelSerializer):
    topic = serializers.StringRelatedField()
    difficulty = serializers.StringRelatedField()

    class Meta:
        model = Question
        exclude = ('correct_answer', 'explanation', 'learning_tip') # Hide sensitive info during quiz

class AnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ('id', 'correct_answer', 'explanation', 'learning_tip')

class QuizProfileSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    level_name = serializers.SerializerMethodField()

    class Meta:
        model = QuizProfile
        fields = ('user', 'total_points', 'level', 'level_name', 'streak_days')

    def get_level_name(self, obj):
        # This logic can be expanded based on the LEVELS constant from the streamlit app
        # For now, a simple placeholder:
        return f"Level {obj.level} Developer"

class BadgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Badge
        fields = '__all__'

class UserBadgeSerializer(serializers.ModelSerializer):
    badge = BadgeSerializer()

    class Meta:
        model = UserBadge
        fields = ('badge', 'awarded_at')

class QuizSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizSession
        fields = ('id', 'profile', 'difficulty', 'start_time', 'is_finished', 'score')

class SessionAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = SessionAnswer
        fields = '__all__'

class QuizSessionDetailSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = QuizSession
        fields = ('id', 'profile', 'difficulty', 'start_time', 'is_finished', 'score', 'questions')

class SessionAnswerSubmitSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    selected_option_id = serializers.CharField()


class QuizPoolSerializer(serializers.ModelSerializer):
    title = serializers.CharField(source='name')
    question_count = serializers.SerializerMethodField()

    class Meta:
        model = Topic
        fields = ('id', 'title', 'description', 'question_count')

    def get_question_count(self, obj):
        return obj.questions.count()


class GeneratedQuizSerializer(serializers.Serializer):
    """
    Validates and persists generated quiz payloads coming from the LLM/Streamlit.
    """
    source = serializers.CharField(required=False, default='code_generation', max_length=50)
    questions = serializers.ListField(child=serializers.DictField(), allow_empty=False)
    metadata = serializers.DictField(required=False, default=dict)

    def validate_questions(self, value):
        """
        Basic shape validation: each item should have question, options (list len>=2), correct_index (int).
        """
        for idx, item in enumerate(value):
            if not isinstance(item, dict):
                raise serializers.ValidationError(f"Question {idx+1} is not an object.")
            if 'question' not in item or not str(item.get('question')).strip():
                raise serializers.ValidationError(f"Question {idx+1} is missing 'question'.")
            options = item.get('options')
            if not isinstance(options, list) or len(options) < 2:
                raise serializers.ValidationError(f"Question {idx+1} must have at least 2 options.")
            if 'correct_index' not in item or not isinstance(item.get('correct_index'), int):
                raise serializers.ValidationError(f"Question {idx+1} is missing a numeric 'correct_index'.")
        return value

    def create(self, validated_data):
        user = self.context['request'].user
        from .models import GeneratedQuiz
        return GeneratedQuiz.objects.create(
            user=user,
            source=validated_data.get('source', 'code_generation'),
            questions=validated_data['questions'],
            metadata=validated_data.get('metadata', {}),
        )
