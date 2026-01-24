from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import Patient, Checkup
import json

# ---------- STATIC PAGES ----------

@login_required
def home(request):
    return render(request, 'home.html')

@login_required
def patients(request):
    return render(request, 'patients.html')

def contact(request):
    return render(request, 'contact.html')


# ---------- API FOR POP-UP (New) ----------
@login_required
def get_patient_details(request):
    """
    This function searches for a patient by phone number
    and returns their details as JSON to the existing_patient.html page.
    """
    if request.method == 'GET':
        phone = request.GET.get('phone')
        
        try:
            # Find patient by phone
            patient = Patient.objects.get(phone=phone)
            
            # Try to get the most recent checkup to show history
            last_checkup = Checkup.objects.filter(patient=patient).last()
            
            data = {
                'exists': True,
                'id': patient.id,
                'name': patient.name,
                'gender': patient.gender,
                'address': patient.address,
                # If they have a previous checkup, show that age/height/weight, else empty
                'age': last_checkup.age if last_checkup else "",
                'last_height': last_checkup.height if last_checkup else "",
                'last_weight': last_checkup.weight if last_checkup else "",
            }
            return JsonResponse(data)
            
        except Patient.DoesNotExist:
            return JsonResponse({'exists': False, 'error': 'Patient ID/Phone not found.'})


# ---------- NEW PATIENT (Locked) ----------
@login_required
def new_patient(request):
    if request.method == 'POST':
        name = request.POST['name']
        gender = request.POST['gender']
        phone = request.POST['phone']
        address = request.POST['address']

        age = int(request.POST['age'])
        height_cm = float(request.POST['height'])
        weight = float(request.POST['weight'])
        bp = request.POST['bp']
        activity = float(request.POST['activity'])

        # Calculations
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

        # Create Patient or Get existing
        patient, created = Patient.objects.get_or_create(
            phone=phone,
            defaults={
                'name': name,
                'gender': gender,
                'address': address
            }
        )

        # Create New Checkup Record
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


# ---------- EXISTING PATIENT (Updated) ----------
@login_required
def existing_patient(request):
    if request.method == "POST":
        # 1. Get the Hidden Patient ID from the Modal
        patient_id = request.POST['patient_id']
        patient = get_object_or_404(Patient, id=patient_id)

        # 2. Get the NEW vitals from the form
        age = int(request.POST['age'])
        height_cm = float(request.POST['height'])
        weight = float(request.POST['weight'])
        bp = request.POST['bp']
        activity = float(request.POST['activity'])

        # 3. Perform Calculations (Same as New Patient)
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

        # 4. Save the NEW Checkup
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
# ---------- GENERATE PLAN (With History) ----------
# In health/views.py

@login_required
def generate_dynamic_diet_plan(request, patient_id, checkup_id):
    patient = get_object_or_404(Patient, id=patient_id)
    current_checkup = get_object_or_404(Checkup, id=checkup_id)
    history = Checkup.objects.filter(patient=patient).order_by('-id')
    
    tdee = current_checkup.tdee
    
    # --- CHANGE START ---
    # We use round() here to remove decimals in Python
    meals = {
        'breakfast': { 'cal': round(tdee * 0.25) },
        'lunch':     { 'cal': round(tdee * 0.35) },
        'snacks':    { 'cal': round(tdee * 0.10) },
        'dinner':    { 'cal': round(tdee * 0.30) }
    }
    # --- CHANGE END ---

    context = {
        'patient': patient,
        'checkup': current_checkup,
        'history': history,
        'meals': meals,
    }

    return render(request, 'patient_report.html', context)


# ---------- VIEW ONLY (Search & Redirect) ----------
@login_required
def search_patient(request):
    if request.method == 'POST':
        phone = request.POST['phone']
        
        try:
            # 1. Find the Patient
            patient = Patient.objects.get(phone=phone)
            
            # 2. Find their most recent checkup (to show as default)
            last_checkup = Checkup.objects.filter(patient=patient).last()
            
            if last_checkup:
                # 3. Redirect to the report page we already built
                # This page already has the history sidebar!
                return redirect('generate_dynamic_diet_plan', patient_id=patient.id, checkup_id=last_checkup.id)
            else:
                return render(request, 'search_patient.html', {'error': 'Patient exists but has no reports yet.'})

        except Patient.DoesNotExist:
            return render(request, 'search_patient.html', {'error': 'No patient found with this number.'})

    return render(request, 'search_patient.html')