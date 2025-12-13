"""
Django Signals for Quiz App
Auto-creates QuizProfile when a User is created
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import QuizProfile


@receiver(post_save, sender=User)
def create_quiz_profile(sender, instance, created, **kwargs):
    """
    Signal handler that creates a QuizProfile whenever a new User is created.

    This ensures that every user automatically gets a quiz profile without
    requiring manual creation or separate API calls.

    Args:
        sender: The User model class
        instance: The User instance being saved
        created: Boolean indicating if this is a new instance
        **kwargs: Additional keyword arguments
    """
    if created:
        QuizProfile.objects.get_or_create(user=instance)


@receiver(post_save, sender=User)
def save_quiz_profile(sender, instance, created, **kwargs):
    """
    Signal handler that saves the QuizProfile whenever a User is saved.

    While typically the QuizProfile is only created once, this handler
    ensures consistency if the User instance is updated.

    Args:
        sender: The User model class
        instance: The User instance being saved
        created: Boolean indicating if this is a new instance
        **kwargs: Additional keyword arguments
    """
    if not created:
        # Only ensure profile exists on existing users
        if hasattr(instance, 'quiz_profile'):
            instance.quiz_profile.save()
