import os
import json
from openai import OpenAI
from .models import Question, Topic, Difficulty

class QuizEngine:
    def __init__(self):
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set.")
        self.client = OpenAI(api_key=api_key)

    def generate_quiz_question(self, difficulty_name="beginner", topic_name=None):
        """Generates a quiz question using AI and saves it to the database."""
        try:
            difficulty = Difficulty.objects.get(name=difficulty_name)
            if topic_name:
                topic, _ = Topic.objects.get_or_create(name=topic_name)
            else:
                # If no topic is provided, we might need a default or random selection logic
                # For now, let's require a topic.
                if not topic_name:
                     raise ValueError("A topic name must be provided to generate a question.")

        except (Difficulty.DoesNotExist, ValueError) as e:
            return None, str(e)

        difficulty_desc = {
            "beginner": "Python 초보자를 위한 기초 문법 문제",
            "intermediate": "Python 중급자를 위한 객체지향 및 고급 문법 문제",
            "advanced": "Python 고급 개발자를 위한 심화 문제"
        }

        system_prompt = f"""You are a Python programming education expert.
        Please create a quiz for a {difficulty_desc.get(difficulty_name, "beginner")}.

        Topic: {topic.name}
        Difficulty: {difficulty_name}

        You must respond only in the following JSON format:
        {{
            "question": "Question content (can include code examples)",
            "options": {{
                "a": "Option 1",
                "b": "Option 2",
                "c": "Option 3",
                "d": "Option 4"
            }},
            "answer": "The key of the correct answer (a, b, c, or d)",
            "explanation": "A detailed 5-7 line explanation for the answer",
            "learning_tip": "A 1-2 line core concept that can be learned from this problem"
        }}"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Please create a '{topic.name}' problem with {difficulty_name} difficulty."}
                ],
                response_format={"type": "json_object"}
            )

            quiz_data = json.loads(response.choices[0].message.content)

            # Create and save the Question object
            question = Question.objects.create(
                topic=topic,
                difficulty=difficulty,
                question_text=quiz_data['question'],
                options=quiz_data['options'],
                correct_answer=quiz_data['answer'],
                explanation=quiz_data['explanation'],
                learning_tip=quiz_data.get('learning_tip', '')
            )
            return question, None
        except Exception as e:
            # Handle potential errors from OpenAI API or JSON parsing
            return None, str(e)
