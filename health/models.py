from django.db import models

class Patient(models.Model):
    name = models.CharField(max_length=100)
    gender = models.CharField(max_length=10)
    phone = models.CharField(max_length=15, unique=True)
    address = models.TextField()
    
    # Note: Medical history removed as per new "Body Type" logic
    
    def __str__(self):
        return f"{self.name} ({self.phone})"

class Checkup(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    age = models.IntegerField()
    height = models.FloatField(help_text="cm")
    weight = models.FloatField(help_text="kg")
    activity = models.FloatField(help_text="Multiplier (1.2 - 1.9)")
    
    # Preferences
    dietary = models.CharField(max_length=50, default="Non-Veg") 
    plan_type = models.CharField(max_length=20, default="3-Meal")
    
    # Computed Metrics
    bmi = models.FloatField()
    bmr = models.FloatField()
    tdee = models.FloatField()
    category = models.CharField(max_length=20) # Underweight, Normal, Overweight, Obese
    
    # Target Macros (Computed)
    protein_target = models.FloatField(default=0)
    carbs_target = models.FloatField(default=0)
    fat_target = models.FloatField(default=0)
    
    date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.patient.name} - {self.date}"

class FoodItem(models.Model):
    CATEGORY_CHOICES = [('Breakfast','Breakfast'), ('Lunch','Lunch'), ('Dinner','Dinner'), ('Snack','Snack')]
    DIET_TYPE = [('Veg','Veg'), ('Non-Veg','Non-Veg'), ('Vegan','Vegan')]

    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    diet_type = models.CharField(max_length=20, choices=DIET_TYPE)
    
    # Nutrition (Per Serving Base)
    calories = models.IntegerField()
    protein = models.FloatField()
    carbs = models.FloatField()
    fat = models.FloatField()
    
    # Critical Filtering Fields
    fiber = models.FloatField(default=0, help_text="Important for Obese/Weight Loss")
    sugar = models.FloatField(default=0, help_text="Filter for unhealthy items")
    
    # Portion Logic
    unit_name = models.CharField(max_length=20, default="Serving", help_text="e.g. Cup, Nos")
    serving_desc = models.CharField(max_length=50, default="1 Serving")
    
    def __str__(self):
        return f"{self.name} ({self.calories} kcal)"

class AssignedMeal(models.Model):
    checkup = models.ForeignKey(Checkup, on_delete=models.CASCADE)
    day = models.CharField(max_length=15)
    meal_type = models.CharField(max_length=20)
    food_item = models.ForeignKey(FoodItem, on_delete=models.CASCADE)
    
    # Dynamic Portion Results
    quantity_text = models.CharField(max_length=50) # e.g. "2.5 Cups"
    total_calories = models.IntegerField()

    def __str__(self):
        return f"{self.checkup.patient.name} - {self.day} - {self.meal_type}"
