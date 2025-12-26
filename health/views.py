from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from .models import PatientProfile
from django.http import JsonResponse

@login_required
def calculator(request):
    if request.method == 'POST':
        # Get form data
        age = float(request.POST['age'])
        weight = float(request.POST['weight'])
        height = float(request.POST['height'])
        gender = request.POST['gender']
        activity = request.POST.get('activity', 'sedentary')
        profile_type = request.POST.get('profile_type', 'general')
        trimester = request.POST.get('trimester', '')
        
        # Save profile
        PatientProfile.objects.create(
            user=request.user, age=age, weight_kg=weight, height_cm=height,
            gender=gender, activity_level=activity, profile_type=profile_type,
            trimester=trimester
        )
        
        # BMI
        height_m = height / 100
        bmi = weight / (height_m ** 2)
        
        # IBW (Devine formula)
        height_in = height / 2.54
        if gender == 'male':
            ibw = 50 + 2.3 * (height_in - 60)
        else:
            ibw = 45.5 + 2.3 * (height_in - 60)
        
        # BMR (Mifflin-St Jeor)
        if gender == 'male':
            bmr = 10*weight + 6.25*height - 5*age + 5
        else:
            bmr = 10*weight + 6.25*height - 5*age - 161
        
        # TDEE
        activity_multipliers = {
            'sedentary': 1.2, 'light': 1.375, 'moderate': 1.55,
            'active': 1.725, 'very_active': 1.9
        }
        tdee = bmr * activity_multipliers[activity]
        
        # Profile adjustments
        goal_calories = tdee
        if profile_type == 'pregnant':
            if trimester == 'second': goal_calories += 350
            elif trimester == 'third': goal_calories += 500
        elif profile_type == 'athlete':
            goal_calories += 300  # Muscle gain
        elif bmi > 25:  # Overweight
            goal_calories -= 400
        
        # Macros (adjusted by profile)
        if profile_type == 'diabetes':
            carb_pct, prot_pct, fat_pct = 40, 30, 30
        elif profile_type == 'athlete':
            carb_pct, prot_pct, fat_pct = 45, 35, 20
        else:
            carb_pct, prot_pct, fat_pct = 50, 25, 25
        
        carb_g = (carb_pct/100 * goal_calories) / 4
        prot_g = (prot_pct/100 * goal_calories) / 4
        fat_g = (fat_pct/100 * goal_calories) / 9
        
        # 3-meal split
        meals_3 = [
            {'name': 'Breakfast', 'cal': goal_calories*0.3, 'carb': carb_g*0.3, 'prot': prot_g*0.3, 'fat': fat_g*0.3},
            {'name': 'Lunch', 'cal': goal_calories*0.4, 'carb': carb_g*0.4, 'prot': prot_g*0.4, 'fat': fat_g*0.4},
            {'name': 'Dinner', 'cal': goal_calories*0.3, 'carb': carb_g*0.3, 'prot': prot_g*0.3, 'fat': fat_g*0.3},
        ]
        
        # 5-meal split
        meals_5 = [
            {'name': 'Breakfast', 'cal': goal_calories*0.25, 'carb': carb_g*0.25, 'prot': prot_g*0.25, 'fat': fat_g*0.25},
            {'name': 'Snack 1', 'cal': goal_calories*0.1, 'carb': carb_g*0.1, 'prot': prot_g*0.1, 'fat': fat_g*0.1},
            {'name': 'Lunch', 'cal': goal_calories*0.3, 'carb': carb_g*0.3, 'prot': prot_g*0.3, 'fat': fat_g*0.3},
            {'name': 'Snack 2', 'cal': goal_calories*0.1, 'carb': carb_g*0.1, 'prot': prot_g*0.1, 'fat': fat_g*0.1},
            {'name': 'Dinner', 'cal': goal_calories*0.25, 'carb': carb_g*0.25, 'prot': prot_g*0.25, 'fat': fat_g*0.25},
        ]
        
        context = {
            'bmi': round(bmi, 1), 'ibw': round(ibw, 1), 'bmr': round(bmr, 0),
            'tdee': round(tdee, 0), 'goal_calories': round(goal_calories, 0),
            'carb_g': round(carb_g, 0), 'prot_g': round(prot_g, 0), 'fat_g': round(fat_g, 0),
            'meals_3': meals_3, 'meals_5': meals_5,
            'profile_type': profile_type
        }
        return render(request, 'result.html', context)
    
    return render(request, 'calculator.html')

def register(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = User.objects.create_user(username=username, password=password)
        login(request, user)
        return redirect('calculator')
    return render(request, 'register.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('calculator')
        messages.error(request, 'Invalid credentials')
    return render(request, 'login.html')

@login_required
def logout_view(request):
    logout(request)
    return redirect('register')