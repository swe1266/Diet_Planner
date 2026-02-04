from django.db import models

class Patient(models.Model):
    name = models.CharField(max_length=100)
    gender = models.CharField(max_length=10)
    phone = models.CharField(max_length=15, unique=True)
    address = models.TextField()
    
    # Clinical Data
    medical_history = models.CharField(max_length=200, default="None", help_text="diabetes, renal, cardiac")
    allergies = models.CharField(max_length=200, default="None", help_text="Comma separated ingredients")

    def __str__(self):
        return f"{self.name} ({self.phone})"

class Checkup(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    age = models.IntegerField()
    height = models.FloatField()
    weight = models.FloatField()
    bp = models.CharField(max_length=20)
    activity = models.FloatField()
    dietary = models.CharField(max_length=50, default="Non-Veg") 
    plan_type = models.CharField(max_length=20, default="3-Meal")
    
    # Metrics
    bmi = models.FloatField()
    bmr = models.FloatField()
    tdee = models.FloatField()
    category = models.CharField(max_length=20)
    carbs = models.FloatField()
    protein = models.FloatField()
    fat = models.FloatField()
    date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.patient.name} - {self.date}"

class FoodItem(models.Model):
    CATEGORY_CHOICES = [('Breakfast','Breakfast'), ('Lunch','Lunch'), ('Dinner','Dinner'), ('Snack','Snack')]
    DIET_TYPE = [('Veg','Veg'), ('Non-Veg','Non-Veg'), ('Vegan','Vegan')]

    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    diet_type = models.CharField(max_length=20, choices=DIET_TYPE)
    
    # Nutrition (Per Unit)
    calories = models.IntegerField()
    protein = models.FloatField()
    carbs = models.FloatField()
    fat = models.FloatField()
    sodium = models.FloatField(default=0, help_text="mg")
    sugar = models.FloatField(default=0, help_text="g")
    
    # --- NEW CLINICAL FIELDS (These were missing!) ---
    potassium = models.FloatField(default=0, help_text="mg (Renal)")
    phosphorus = models.FloatField(default=0, help_text="mg (Renal)")
    ingredients = models.TextField(default="", help_text="For allergy check")
    unit_name = models.CharField(max_length=20, default="Serving", help_text="e.g. Idli, Cup")
    serving_desc = models.CharField(max_length=50, default="1 Serving")  # <--- This caused your error

    # Flags
    is_diabetes_safe = models.BooleanField(default=False)
    is_renal_safe = models.BooleanField(default=False)     
    is_cardiac_safe = models.BooleanField(default=False)   
    is_hypertension_safe = models.BooleanField(default=False) 
    
    def __str__(self):
        return f"{self.name} ({self.calories} kcal)"

class AssignedMeal(models.Model):
    checkup = models.ForeignKey(Checkup, on_delete=models.CASCADE)
    day = models.CharField(max_length=15)
    meal_type = models.CharField(max_length=20)
    food_item = models.ForeignKey(FoodItem, on_delete=models.CASCADE)
    
    # Stores the calculated portion
    quantity_text = models.CharField(max_length=50, default="1 Serving") 
    total_calories = models.IntegerField()

    def __str__(self):
        return f"{self.checkup.patient.name} - {self.day} - {self.meal_type}"