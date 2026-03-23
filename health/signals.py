from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.core.management import call_command
from .models import Disease, FoodItem

@receiver(post_migrate)
def load_initial_data(sender, **kwargs):
    """
    Automatically load food and disease fixtures if the database is empty
    after migrations are applied.
    """
    # Only run for our app
    if sender.name == 'health':
        if Disease.objects.count() == 0 and FoodItem.objects.count() == 0:
            print("--- Auto-loading production datasets (JSON fixtures) ---")
            try:
                call_command('loaddata', 'disease.json')
                call_command('loaddata', 'food.json')
                print("--- Data loading complete! ---")
            except Exception as e:
                print(f"--- Error loading fixtures: {e} ---")
