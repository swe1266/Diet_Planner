from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.template.loader import get_template
from django.db.models import Q
from django.contrib import messages
from xhtml2pdf import pisa
from .models import Patient, Checkup, FoodItem, AssignedMeal
import json
import random
import math

# ==========================================
# 1. DASHBOARD & STATIC PAGES
# ==========================================

@login_required
def home(request):
    total_patients = Patient.objects.count()
    today = timezone.now().date()
    today_visits = Checkup.objects.filter(date=today).count()
    
    underweight = 0; normal = 0; overweight = 0; obese = 0
    patients = Patient.objects.all()
    for p in patients:
        last_report = Checkup.objects.filter(patient=p).last()
        if last_report:
            if 'Underweight' in last_report.category: underweight += 1
            elif 'Normal' in last_report.category: normal += 1
            elif 'Overweight' in last_report.category: overweight += 1
            elif 'Obese' in last_report.category: obese += 1
            
    context = {
        'total_patients': total_patients, 'today_visits': today_visits,
        'underweight': underweight, 'normal': normal, 'overweight': overweight, 'obese': obese
    }
    return render(request, 'home.html', context)

@login_required
def patients(request):
    all_patients = Patient.objects.all().order_by('-id')
    return render(request, 'patients.html', {'patients': all_patients})

def contact(request):
    return render(request, 'contact.html')

# ==========================================
# 2. PATIENT SEARCH
# ==========================================

@login_required
def get_patient_details(request):
    if request.method == 'GET':
        phone = request.GET.get('phone')
        try:
            patient = Patient.objects.get(phone=phone)
            last_checkup = Checkup.objects.filter(patient=patient).last()
            data = {
                'exists': True, 'id': patient.id, 'name': patient.name,
                'gender': patient.gender, 'address': patient.address,
                'age': last_checkup.age if last_checkup else "",
                'last_height': last_checkup.height if last_checkup else "",
                'last_weight': last_checkup.weight if last_checkup else "",
                'last_dietary': last_checkup.dietary if last_checkup else "Non-Veg",
                'last_plan': last_checkup.plan_type if last_checkup else "3-Meal",
            }
            return JsonResponse(data)
        except Patient.DoesNotExist:
            return JsonResponse({'exists': False, 'error': 'Patient ID/Phone not found.'})

@login_required
def search_patient(request):
    query = request.GET.get('q')
    error_message = None
    patients = None
    
    if request.GET.get('view_id'):
        selected_patient = get_object_or_404(Patient, id=request.GET.get('view_id'))
        history = Checkup.objects.filter(patient=selected_patient).order_by('-date')
        return render(request, 'search_patient.html', {'selected_patient': selected_patient, 'history': history, 'patients': patients, 'query': query})

    if query:
        exact_match = Patient.objects.filter(phone=query).first()
        if exact_match:
            last_report = Checkup.objects.filter(patient=exact_match).last()
            if last_report:
                return redirect('generate_dynamic_diet_plan', patient_id=exact_match.id, checkup_id=last_report.id)
            else:
                return redirect(f'/health/patients/search/?view_id={exact_match.id}')
        
        patients = Patient.objects.filter(Q(name__icontains=query) | Q(phone__icontains=query))
        if not patients.exists():
            error_message = f"❌ No records found for '{query}'."

    return render(request, 'search_patient.html', {'patients': patients, 'query': query, 'error_message': error_message})

@login_required
def delete_checkup(request, checkup_id):
    checkup = get_object_or_404(Checkup, id=checkup_id)
    checkup.delete()
    return redirect('search_patient')

# ==========================================
# 3. PATIENT ENTRY
# ==========================================
@login_required
def new_patient(request):
    if request.method == 'POST':
        name = request.POST['name']; gender = request.POST['gender']; phone = request.POST['phone']
        address = request.POST['address']; dietary = request.POST['dietary']; plan_type = request.POST['plan_type']
        age = int(request.POST['age']); height_cm = float(request.POST['height']); weight = float(request.POST['weight'])
        bp = request.POST['bp']; activity = float(request.POST['activity'])

        height_m = height_cm / 100; bmi = round(weight / (height_m ** 2), 2)
        if gender.lower() == 'male': bmr = 88.36 + (13.4 * weight) + (4.8 * height_cm) - (5.7 * age)
        else: bmr = 447.6 + (9.2 * weight) + (3.1 * height_cm) - (4.3 * age)
        bmr = round(bmr, 2); tdee = round(bmr * activity, 2)

        if bmi < 18.5: category = "Underweight"
        elif bmi < 25: category = "Normal"
        elif bmi < 30: category = "Overweight"
        else: category = "Obese"

        carbs = round((tdee * 0.5) / 4, 2); protein = round((tdee * 0.2) / 4, 2); fat = round((tdee * 0.3) / 9, 2)

        patient, created = Patient.objects.get_or_create(phone=phone, defaults={'name': name, 'gender': gender, 'address': address})
        checkup = Checkup.objects.create(patient=patient, age=age, height=height_cm, weight=weight, bp=bp, activity=activity, dietary=dietary, plan_type=plan_type, bmi=bmi, bmr=bmr, tdee=tdee, category=category, carbs=carbs, protein=protein, fat=fat)
        
        return redirect('generate_dynamic_diet_plan', patient_id=patient.id, checkup_id=checkup.id)
    return render(request, 'new_patient.html')

@login_required
def existing_patient(request):
    if request.method == "POST":
        patient_id = request.POST['patient_id']
        patient = get_object_or_404(Patient, id=patient_id)
        
        age = int(request.POST['age']); height_cm = float(request.POST['height']); weight = float(request.POST['weight'])
        bp = request.POST['bp']; activity = float(request.POST['activity']); dietary = request.POST['dietary']; plan_type = request.POST['plan_type']
        
        height_m = height_cm / 100; bmi = round(weight / (height_m ** 2), 2)
        if patient.gender.lower() == 'male': bmr = 88.36 + (13.4 * weight) + (4.8 * height_cm) - (5.7 * age)
        else: bmr = 447.6 + (9.2 * weight) + (3.1 * height_cm) - (4.3 * age)
        bmr = round(bmr, 2); tdee = round(bmr * activity, 2)

        if bmi < 18.5: category = "Underweight"
        elif bmi < 25: category = "Normal"
        elif bmi < 30: category = "Overweight"
        else: category = "Obese"
        carbs = round((tdee * 0.5) / 4, 2); protein = round((tdee * 0.2) / 4, 2); fat = round((tdee * 0.3) / 9, 2)

        checkup = Checkup.objects.create(patient=patient, age=age, height=height_cm, weight=weight, bp=bp, activity=activity, dietary=dietary, plan_type=plan_type, bmi=bmi, bmr=bmr, tdee=tdee, category=category, carbs=carbs, protein=protein, fat=fat)
        return redirect('generate_dynamic_diet_plan', patient_id=patient.id, checkup_id=checkup.id)
    return render(request, 'existing_patient.html')


# ==========================================
# 4. CLINICAL ALGORITHM (SAFETY + PRECISION)
# ==========================================

def filter_food_pool(category, diet_pref, patient, is_dia, is_ren, is_card, is_hyp):
    """
    ALGORITHM GATE 1: SAFETY & CLINICAL FILTERS
    Removes dangerous foods based on allergies and diseases.
    """
    items = FoodItem.objects.filter(category=category)
    
    # 1. Diet Preference
    if diet_pref == 'Veg': items = items.filter(diet_type__in=['Veg', 'Vegan'])
    elif diet_pref == 'Vegan': items = items.filter(diet_type='Vegan')

    # 2. Allergy Filter (String Matching)
    # Check if patient has allergies listed in DB
    if hasattr(patient, 'allergies') and patient.allergies and patient.allergies.lower() != 'none':
        allergens = [a.strip().lower() for a in patient.allergies.split(',')]
        for allergen in allergens:
            # Exclude if allergen matches ingredient
            items = items.exclude(ingredients__icontains=allergen)

    # 3. Disease-Specific Nutrient Ceilings (Strict Medical Limits)
    if is_ren: 
        # Renal: Low Protein, Potassium < 200, Phosphorus < 150
        items = items.filter(potassium__lt=200, phosphorus__lt=150)
    
    if is_card or is_hyp:
        # Cardiac/Hypertension: Low Sodium, Low Fat
        items = items.filter(sodium__lt=300)

    if is_dia:
        # Diabetes: Low Sugar
        items = items.filter(sugar__lt=5)

    return list(items)

def calculate_smart_portion(food, target_calories):
    """
    ALGORITHM GATE 2: DYNAMIC PORTIONING
    Adjusts the quantity of ANY safe food to match the target calories.
    """
    base_cal = food.calories
    if base_cal <= 0: return "1 Serving", 0
    
    # Calculate ratio (Target / Base)
    count = target_calories / base_cal
    
    # Rounding Logic based on Unit Type
    if food.unit_name.lower() in ['pcs', 'nos', 'idli', 'egg', 'slice', 'set']:
        # Discrete items: Round to nearest 0.5 or 1
        final_count = round(count * 2) / 2 
        if final_count < 1: final_count = 1
    else:
        # Volume items (Cup/Bowl): Round to nearest 0.5
        final_count = round(count * 2) / 2
        if final_count < 0.5: final_count = 0.5

    # Format output
    qty_text = f"{final_count} {food.unit_name}"
    total_cal = int(final_count * base_cal)
    
    return qty_text, total_cal

@login_required
def generate_dynamic_diet_plan(request, patient_id, checkup_id):
    patient = get_object_or_404(Patient, id=patient_id)
    checkup = get_object_or_404(Checkup, id=checkup_id)
    
    # --- 1. Clinical Targets ---
    tdee = checkup.tdee
    bmi = checkup.bmi
    target_calories = tdee
    diet_goal = "Maintenance"

    if bmi >= 25: 
        target_calories = tdee - 500
        diet_goal = "Weight Loss"
    elif bmi < 18.5: 
        target_calories = tdee + 300
        diet_goal = "Weight Gain"
    
    if target_calories < 1200: target_calories = 1200

    if checkup.plan_type == '3-Meal':
        splits = {'Breakfast': 0.30, 'Lunch': 0.40, 'Dinner': 0.30}
    else:
        splits = {'Breakfast': 0.25, 'Snack': 0.10, 'Lunch': 0.30, 'Dinner': 0.25}

    # Identify Conditions
    med_hist = getattr(patient, 'medical_history', '').lower()
    is_dia = 'diabetes' in med_hist or 'Obese' in checkup.category
    is_ren = 'renal' in med_hist or 'kidney' in med_hist
    is_card = 'cardiac' in med_hist or 'heart' in med_hist
    is_hyp = 'hypertension' in med_hist or 'bp' in med_hist

    # --- 2. PERSISTENCE & GENERATION ---
    existing_meals = AssignedMeal.objects.filter(checkup=checkup)
    
    # Auto-Repair incomplete plans
    if existing_meals.exists() and existing_meals.count() < 7:
        existing_meals.delete()
        existing_meals = AssignedMeal.objects.none()

    if not existing_meals.exists():
        # Step A: Create filtered pools for every meal type
        food_pools = {}
        for meal_name in splits.keys():
            # Get safe foods (Ignore calories for now, we calculate portion later)
            candidates = filter_food_pool(meal_name, checkup.dietary, patient, is_dia, is_ren, is_card, is_hyp)
            
            # Deterministic Shuffle (Seeded by ID + Meal Name)
            random.Random(f"{patient.id}_{meal_name}").shuffle(candidates)
            food_pools[meal_name] = candidates

        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        for day in days:
            for meal_name, pct in splits.items():
                meal_target = target_calories * pct
                pool = food_pools.get(meal_name, [])
                
                if pool:
                    # Step B: Pick Unique Food
                    selected_food = pool.pop(0)
                    
                    # Refill pool if empty to prevent crashes next day
                    if not pool:
                        pool = filter_food_pool(meal_name, checkup.dietary, patient, is_dia, is_ren, is_card, is_hyp)
                        random.Random(f"{patient.id}_{meal_name}").shuffle(pool)
                        food_pools[meal_name] = pool

                    # Step C: Calculate Precise Portion
                    qty_str, final_cal = calculate_smart_portion(selected_food, meal_target)

                    AssignedMeal.objects.create(
                        checkup=checkup, day=day, meal_type=meal_name,
                        food_item=selected_food,
                        quantity_text=qty_str, 
                        total_calories=final_cal
                    )
                else:
                    # Fallback (Only happens if 0 foods match safety criteria)
                    pass 

    # --- 3. RETRIEVAL & DISPLAY ---
    weekly_plan = {}
    db_meals = AssignedMeal.objects.filter(checkup=checkup)
    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    for day in days_order:
        day_meals = db_meals.filter(day=day)
        day_list = []
        for m in day_meals.order_by('id'):
            day_list.append({
                'meal': m.meal_type, 'food': m.food_item.name,
                'qty': m.quantity_text, # Using calculated portion
                'cal': m.total_calories, 
                'p': m.food_item.protein, 'c': m.food_item.carbs, 'f': m.food_item.fat
            })
        weekly_plan[day] = day_list

    # Charts
    history = Checkup.objects.filter(patient=patient).order_by('-id')
    graph_data = Checkup.objects.filter(patient=patient).order_by('id')
    c_labels = [f"#{h.id}" for h in graph_data]
    c_bmis = [float(h.bmi) for h in graph_data]

    context = {
        'patient': patient, 'checkup': checkup, 'history': history,
        'diet_goal': diet_goal, 'target_calories': int(target_calories),
        'weekly_plan': weekly_plan,
        'chart_labels': json.dumps(c_labels), 'chart_bmis': json.dumps(c_bmis),
    }
    return render(request, 'patient_report.html', context)

@login_required
def download_pdf(request, checkup_id):
    checkup = get_object_or_404(Checkup, id=checkup_id)
    patient = checkup.patient
    db_meals = AssignedMeal.objects.filter(checkup=checkup, day='Monday')
    pdf_meals = {}
    for m in db_meals:
        # Use the stored quantity text for PDF too
        pdf_meals[m.meal_type] = {'desc': f"{m.food_item.name} ({m.quantity_text})", 'cal': m.total_calories}
    
    context = {'patient': patient, 'checkup': checkup, 'meals': pdf_meals}
    template_path = 'pdf_report.html'
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Report_{patient.name}_{checkup.id}.pdf"'
    template = get_template(template_path)
    html = template.render(context)
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err: return HttpResponse('Errors <pre>' + html + '</pre>')
    return response

@login_required
def regenerate_plan(request, checkup_id):
    checkup = get_object_or_404(Checkup, id=checkup_id)
    AssignedMeal.objects.filter(checkup=checkup).delete()
    messages.success(request, "Diet plan has been regenerated with new options!")
    return redirect('generate_dynamic_diet_plan', patient_id=checkup.patient.id, checkup_id=checkup.id)