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


# ---------- API FOR POP-UP (Search) ----------
@login_required
def get_patient_details(request):
    if request.method == 'GET':
        phone = request.GET.get('phone')
        try:
            patient = Patient.objects.get(phone=phone)
            last_checkup = Checkup.objects.filter(patient=patient).last()
            
            data = {
                'exists': True,
                'id': patient.id,
                'name': patient.name,
                'gender': patient.gender,
                'address': patient.address,
                'age': last_checkup.age if last_checkup else "",
                'last_height': last_checkup.height if last_checkup else "",
                'last_weight': last_checkup.weight if last_checkup else "",
                # Send back previous dietary preference (defaulting to Non-Veg)
                'last_dietary': last_checkup.dietary if last_checkup else "Non-Veg",
                # Send back previous plan type (defaulting to 3-Meal)
                'last_plan': last_checkup.plan_type if last_checkup else "3-Meal",
            }
            return JsonResponse(data)
        except Patient.DoesNotExist:
            return JsonResponse({'exists': False, 'error': 'Patient ID/Phone not found.'})


# ---------- NEW PATIENT ----------
@login_required
def new_patient(request):
    if request.method == 'POST':
        name = request.POST['name']
        gender = request.POST['gender']
        phone = request.POST['phone']
        address = request.POST['address']
        dietary = request.POST['dietary']
        
        # --- NEW INPUT: Meal Plan ---
        plan_type = request.POST['plan_type']
        # ----------------------------

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

        patient, created = Patient.objects.get_or_create(
            phone=phone,
            defaults={'name': name, 'gender': gender, 'address': address}
        )

        checkup = Checkup.objects.create(
            patient=patient,
            age=age,
            height=height_cm,
            weight=weight,
            bp=bp,
            activity=activity,
            dietary=dietary,
            plan_type=plan_type,  # Saving Plan Choice
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


# ---------- EXISTING PATIENT ----------
@login_required
def existing_patient(request):
    if request.method == "POST":
        patient_id = request.POST['patient_id']
        patient = get_object_or_404(Patient, id=patient_id)

        # New Inputs
        age = int(request.POST['age'])
        height_cm = float(request.POST['height'])
        weight = float(request.POST['weight'])
        bp = request.POST['bp']
        activity = float(request.POST['activity'])
        dietary = request.POST['dietary']
        
        # --- NEW INPUT: Meal Plan ---
        plan_type = request.POST['plan_type']
        # ----------------------------

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
            dietary=dietary,
            plan_type=plan_type,  # Saving Plan Choice
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


# ---------- GENERATE PLAN (With 3-Meal vs 5-Meal Logic) ----------
@login_required
def generate_dynamic_diet_plan(request, patient_id, checkup_id):
    patient = get_object_or_404(Patient, id=patient_id)
    current_checkup = get_object_or_404(Checkup, id=checkup_id)
    
    # History & Graph Data
    history = Checkup.objects.filter(patient=patient).order_by('-id')
    graph_data = Checkup.objects.filter(patient=patient).order_by('id')
    
    c_labels = [f"Report #{h.id}" for h in graph_data]
    c_weights = [float(h.weight) for h in graph_data]
    c_bmis = [float(h.bmi) for h in graph_data]

    tdee = current_checkup.tdee
    plan_type = current_checkup.plan_type
    
    meals = {}

    # --- DYNAMIC MEAL SPLIT LOGIC ---
    if plan_type == '3-Meal':
        # 3 Meals: Breakfast (30%), Lunch (40%), Dinner (30%)
        meals = {
            'Breakfast': {'cal': round(tdee * 0.30), 'icon': 'fa-sun', 'desc': 'Oats, Eggs, or Toast'},
            'Lunch':     {'cal': round(tdee * 0.40), 'icon': 'fa-hamburger', 'desc': 'Rice, Chicken/Lentils, Veggies'},
            'Dinner':    {'cal': round(tdee * 0.30), 'icon': 'fa-moon', 'desc': 'Soup, Salad, Grilled Fish/Tofu'}
        }
    else:
        # 5 Meals: Breakfast (25%), AM Snack (10%), Lunch (30%), PM Snack (10%), Dinner (25%)
        meals = {
            'Breakfast':     {'cal': round(tdee * 0.25), 'icon': 'fa-sun', 'desc': 'Oats, Eggs, or Toast'},
            'Morning Snack': {'cal': round(tdee * 0.10), 'icon': 'fa-apple-alt', 'desc': 'Fruit or Nuts'},
            'Lunch':         {'cal': round(tdee * 0.30), 'icon': 'fa-hamburger', 'desc': 'Rice, Chicken/Lentils, Veggies'},
            'Evening Snack': {'cal': round(tdee * 0.10), 'icon': 'fa-cookie-bite', 'desc': 'Yogurt or Green Tea'},
            'Dinner':        {'cal': round(tdee * 0.25), 'icon': 'fa-moon', 'desc': 'Soup, Salad, Grilled Fish/Tofu'}
        }
    # --------------------------------

    context = {
        'patient': patient,
        'checkup': current_checkup,
        'history': history,
        'meals': meals,
        'chart_labels': json.dumps(c_labels),
        'chart_weights': json.dumps(c_weights),
        'chart_bmis': json.dumps(c_bmis),
    }

    return render(request, 'patient_report.html', context)


# ---------- SEARCH PATIENT ----------
@login_required
def search_patient(request):
    if request.method == 'POST':
        phone = request.POST['phone']
        try:
            patient = Patient.objects.get(phone=phone)
            last_checkup = Checkup.objects.filter(patient=patient).last()
            
            if last_checkup:
                return redirect('generate_dynamic_diet_plan', patient_id=patient.id, checkup_id=last_checkup.id)
            else:
                return render(request, 'search_patient.html', {'error': 'Patient exists but has no reports yet.'})

        except Patient.DoesNotExist:
            return render(request, 'search_patient.html', {'error': 'No patient found with this number.'})

    return render(request, 'search_patient.html')


# ---------- DELETE RECORD ----------
@login_required
def delete_checkup(request, checkup_id):
    report_to_delete = get_object_or_404(Checkup, id=checkup_id)
    patient = report_to_delete.patient
    report_to_delete.delete()
    
    last_report = Checkup.objects.filter(patient=patient).last()
    
    if last_report:
        return redirect('generate_dynamic_diet_plan', patient_id=patient.id, checkup_id=last_report.id)
    else:
        return redirect('home')