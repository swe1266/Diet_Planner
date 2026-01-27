from django.db import models

class Patient(models.Model):
    name = models.CharField(max_length=100)
    gender = models.CharField(max_length=10)
    phone = models.CharField(max_length=15, unique=True)
    address = models.TextField()

    def __str__(self):
        return f"{self.name} ({self.phone})"

class Checkup(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    age = models.IntegerField()
    height = models.FloatField()
    weight = models.FloatField()
    bp = models.CharField(max_length=20)
    activity = models.FloatField()
    
    # --- NEW FIELD ---
    dietary = models.CharField(max_length=50, default="Non-Veg") 
    # -----------------
    plan_type = models.CharField(max_length=20, default="3-Meal")
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