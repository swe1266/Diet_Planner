from django.db import models
from django.contrib.auth.models import User

class PatientProfile(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    age = models.IntegerField()
    weight_kg = models.FloatField()
    height_cm = models.FloatField()
    gender = models.CharField(max_length=10, choices=[('male', 'Male'), ('female', 'Female')])
    activity_level = models.CharField(max_length=20, choices=[
        ('sedentary', 'Sedentary'), ('light', 'Light'), ('moderate', 'Moderate'), 
        ('active', 'Active'), ('very_active', 'Very Active')
    ])
    profile_type = models.CharField(max_length=20, choices=[
        ('general', 'General'), ('pregnant', 'Pregnant'), ('athlete', 'Athlete'), 
        ('diabetes', 'Diabetes'), ('post_surgery', 'Post Surgery')
    ])
    trimester = models.CharField(max_length=10, blank=True)  # For pregnant
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.profile_type}"
