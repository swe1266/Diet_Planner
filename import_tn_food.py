import csv
import os
import django

# 1. Setup Django Environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dietplanner.settings')
django.setup()

from health.models import FoodItem

def import_csv():
    file_path = 'tamil_nadu_foods.csv'
    
    # Check if file exists
    if not os.path.exists(file_path):
        print(f"❌ Error: '{file_path}' not found! Make sure you created it.")
        return

    # Clear old data so we don't have duplicates
    print("🧹 Clearing old food data...")
    FoodItem.objects.all().delete()

    print("🚀 Starting import...")
    
    with open(file_path, 'r') as file:
        reader = csv.DictReader(file)
        count = 0
        for row in reader:
            FoodItem.objects.create(
                name=row['name'],
                category=row['category'],
                diet_type=row['diet_type'],
                calories=int(row['calories']),
                protein=float(row['protein']),
                carbs=float(row['carbs']),
                fat=float(row['fat']),
                # CSV stores True/False as strings, so we convert them:
                is_diabetes_safe=row['is_diabetes_safe'] == 'True',
                is_high_protein=row['is_high_protein'] == 'True',
                serving_desc=row['serving_desc']
            )
            count += 1
            print(f"   Added: {row['name']}")
            
    print(f"\n✅ SUCCESS: Imported {count} Tamil Nadu food items!")

if __name__ == "__main__":
    import_csv()