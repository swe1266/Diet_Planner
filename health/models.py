from django.db import models

class Patient(models.Model):
    name = models.CharField(max_length=100)
    gender = models.CharField(max_length=10)
    phone = models.CharField(max_length=10, unique=True)
    address = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.phone})"


class Checkup(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    age = models.IntegerField()
    height = models.FloatField()
    weight = models.FloatField()
    bp = models.CharField(max_length=10)
    activity = models.FloatField()

    bmi = models.FloatField()
    bmr = models.FloatField()
    tdee = models.FloatField()
    category = models.CharField(max_length=20)

    carbs = models.FloatField()
    protein = models.FloatField()
    fat = models.FloatField()

    visit_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.patient.name} - {self.visit_date.strftime('%d-%m-%Y')}"
