from django.shortcuts import render, redirect, get_object_or_404
from .models import Patient, Checkup

# 1. IMPORT THIS SECURITY TOOL
from django.contrib.auth.decorators import login_required

# ---------- Static Pages ----------

# 2. ADD THE LOCK HERE
@login_required
def home(request):
    return render(request, 'home.html')

@login_required
def patients(request):
    return render(request, 'patients.html')

# (You can leave 'contact' open if you want, or lock it too)
def contact(request):
    return render(request, 'contact.html')


# ---------- NEW PATIENT (Locked) ----------
@login_required
def new_patient(request):
    if request.method == 'POST':
        # ... (Your existing code) ...
        name = request.POST['name']
        gender = request.POST['gender']
        phone = request.POST['phone']
        address = request.POST['address']

        age = int(request.POST['age'])
        height_cm = float(request.POST['height'])
        weight = float(request.POST['weight'])
        bp = request.POST['bp']
        activity = float(request.POST['activity'])

        height_m = height_cm / 100
        bmi = round(weight / (height_m ** 2), 2)

        if gender.lower() == 'male':
            bmr = 88.36 + (13.4 * weight) + (4.8 * height_cm) - (5.7 * age)
        else:
            bmr = 447.6 + (9.2 * weight) + (3.1 * height_cm) - (4.3 * age)
        
        bmr = round(bmr, 2)
        tdee = round(bmr * activity, 2)

        if bmi < 18.5: category = "Underweight"
        elif bmi < 25: category = "Normal"
        elif bmi < 30: category = "Overweight"
        else: category = "Obese"

        carbs = round((tdee * 0.5) / 4, 2)
        protein = round((tdee * 0.2) / 4, 2)
        fat = round((tdee * 0.3) / 9, 2)

        patient, created = Patient.objects.get_or_create(
            phone=phone,
            defaults={
                'name': name,
                'gender': gender,
                'address': address
            }
        )

        checkup = Checkup.objects.create(
            patient=patient,
            age=age,
            height=height_cm,
            weight=weight,
            bp=bp,
            activity=activity,
            bmi=bmi,
            bmr=bmr,
            tdee=tdee,
            category=category,
            carbs=carbs,
            protein=protein,
            fat=fat
        )

        return redirect('generate_dynamic_diet_plan', patient_id=patient.id, checkup_id=checkup.id)

    return render(request, 'new_patient.html')


# ---------- EXISTING PATIENT (Locked) ----------
@login_required
def existing_patient(request):
    if request.method == "POST":
        # ... (Your existing code) ...
        phone = request.POST['phone']
        
        try:
            patient = Patient.objects.get(phone=phone)
        except Patient.DoesNotExist:
            return render(request, 'existing_patient.html', {'error': 'Patient not found'})

        age = int(request.POST['age'])
        height_cm = float(request.POST['height'])
        weight = float(request.POST['weight'])
        bp = request.POST['bp']
        activity = float(request.POST['activity'])

        height_m = height_cm / 100
        bmi = round(weight / (height_m ** 2), 2)

        if patient.gender.lower() == 'male':
            bmr = 88.36 + (13.4 * weight) + (4.8 * height_cm) - (5.7 * age)
        else:
            bmr = 447.6 + (9.2 * weight) + (3.1 * height_cm) - (4.3 * age)

        bmr = round(bmr, 2)
        tdee = round(bmr * activity, 2)

        if bmi < 18.5: category = "Underweight"
        elif bmi < 25: category = "Normal"
        elif bmi < 30: category = "Overweight"
        else: category = "Obese"

        carbs = round((tdee * 0.5) / 4, 2)
        protein = round((tdee * 0.2) / 4, 2)
        fat = round((tdee * 0.3) / 9, 2)

        checkup = Checkup.objects.create(
            patient=patient,
            age=age,
            height=height_cm,
            weight=weight,
            bp=bp,
            activity=activity,
            bmi=bmi,
            bmr=bmr,
            tdee=tdee,
            category=category,
            carbs=carbs,
            protein=protein,
            fat=fat
        )

        return redirect('generate_dynamic_diet_plan', patient_id=patient.id, checkup_id=checkup.id)

    return render(request, 'existing_patient.html')


# ---------- GENERATE PLAN (Locked) ----------
@login_required
def generate_dynamic_diet_plan(request, patient_id, checkup_id):
    patient = get_object_or_404(Patient, id=patient_id)
    checkup = get_object_or_404(Checkup, id=checkup_id)
    
    tdee = checkup.tdee
    
    meals = {
        'breakfast': { 'cal': tdee * 0.25 },
        'lunch':     { 'cal': tdee * 0.35 },
        'snacks':    { 'cal': tdee * 0.10 },
        'dinner':    { 'cal': tdee * 0.30 }
    }

    context = {
        'patient': patient,
        'checkup': checkup,
        'meals': meals,
    }

    return render(request, 'patient_report.html', context)

# Old report view (can be removed or kept)
def patient_report(request):
    return render(request, 'patients.html')