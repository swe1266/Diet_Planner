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
        name = request.POST['name']
        gender = request.POST['gender']
        phone = request.POST['phone']
        address = request.POST['address']
        dietary = request.POST['dietary']
        plan_type = request.POST['plan_type']
        age = int(request.POST['age'])
        height_cm = float(request.POST['height'])
        weight = float(request.POST['weight'])
        activity = float(request.POST['activity'])
        
        # Calculate Metrics using the new Engine
        bmi, bmr, tdee, category, target_calories = calculate_metrics(
            weight, height_cm, age, gender, activity
        )
        
        # Calculate Macro Targets
        carbs_target = target_calories * 0.4 / 4
        protein_target = target_calories * 0.3 / 4
        fat_target = target_calories * 0.3 / 9

        patient, created = Patient.objects.get_or_create(
            phone=phone, 
            defaults={'name': name, 'gender': gender, 'address': address}
        )
        
        checkup = Checkup.objects.create(
            patient=patient,
            age=age,
            height=height_cm,
            weight=weight,
            activity=activity,
            dietary=dietary,
            plan_type=plan_type,
            
            # Computed Metrics
            bmi=bmi,
            bmr=bmr,
            tdee=tdee,
            category=category,
            
            # Macro Targets
            protein_target=protein_target,
            carbs_target=carbs_target,
            fat_target=fat_target
        )
        
        return redirect('generate_dynamic_diet_plan', patient_id=patient.id, checkup_id=checkup.id)
    return render(request, 'new_patient.html')

@login_required
def existing_patient(request):
    if request.method == "POST":
        patient_id = request.POST['patient_id']
        patient = get_object_or_404(Patient, id=patient_id)
        
        age = int(request.POST['age'])
        height_cm = float(request.POST['height'])
        weight = float(request.POST['weight'])
        activity = float(request.POST['activity'])
        dietary = request.POST['dietary']
        plan_type = request.POST['plan_type']
        
        # Calculate Metrics
        bmi, bmr, tdee, category, target_calories = calculate_metrics(
            weight, height_cm, age, patient.gender, activity
        )
        
        # Calculate Targets
        carbs_target = target_calories * 0.4 / 4
        protein_target = target_calories * 0.3 / 4
        fat_target = target_calories * 0.3 / 9

        checkup = Checkup.objects.create(
            patient=patient,
            age=age,
            height=height_cm,
            weight=weight,
            activity=activity,
            dietary=dietary,
            plan_type=plan_type,
            
            # Computed
            bmi=bmi,
            bmr=bmr,
            tdee=tdee,
            category=category,
            
            # Targets
            protein_target=protein_target,
            carbs_target=carbs_target,
            fat_target=fat_target
        )
        return redirect('generate_dynamic_diet_plan', patient_id=patient.id, checkup_id=checkup.id)
    return render(request, 'existing_patient.html')


# ==========================================
# 4. CLINICAL ALGORITHM (SAFETY + PRECISION)
# ==========================================

# ==========================================
# 4. CLINICAL ALGORITHM (BODY TYPE & DYNAMIC PORTION)
# ==========================================

def calculate_metrics(weight, height, age, gender, activity):
    """
    ENGINE A: METRIC CALCULATION
    Returns: BMI, BMR, TDEE, Category, TARGET_CALORIES
    """
    # 1. BMI
    height_m = height / 100
    bmi = round(weight / (height_m ** 2), 2)
    
    # 2. BMR (Mifflin-St Jeor)
    if gender.lower() == 'header': # Fallback if typo, but usually 'male'/'female'
        s = 5
    else:
        s = 5 if gender.lower() == 'male' else -161
    
    bmr = (10 * weight) + (6.25 * height) - (5 * age) + s
    bmr = round(bmr, 2)
    
    # 3. TDEE
    tdee = round(bmr * activity, 2)
    
    # 4. Category & Target
    if bmi < 18.5:
        category = "Underweight"
        target = tdee + 300 # Surplus
    elif bmi < 25:
        category = "Normal"
        target = tdee # Maintenance
    elif bmi < 30:
        category = "Overweight"
        target = tdee - 500 # Deficit
    else:
        category = "Obese"
        target = tdee - 500 # Deficit
        
    # Safety Constraint
    if target < 1200: target = 1200
    
    return bmi, bmr, tdee, category, int(target)

def smart_filter(category, meal_type, diet_pref, bmi_category):
    """
    ENGINE B: SMART FILTER
    Filters foods based on Body Type Logic.
    """
    # Base Filter
    items = FoodItem.objects.filter(category=meal_type)
    
    # Diet Pref
    if diet_pref == 'Veg': items = items.filter(diet_type__in=['Veg', 'Vegan'])
    elif diet_pref == 'Vegan': items = items.filter(diet_type='Vegan')
    
    # Body Type Logic
    if bmi_category in ['Obese', 'Overweight']:
        # GOAL: Satiety & Insulin Control
        # Reject High Sugar (> 8g)
        items = items.exclude(sugar__gt=8)
        # Prioritize Fiber > 3g OR Protein > 5g (We filter in memory for complex OR)
        # For simplicity in Django ORM, we can chain or use Q, but let's filter strict for now
        # OR logic: Keep items that have good fiber OR good protein
        items = items.filter(Q(fiber__gte=3) | Q(protein__gte=5))
        
    elif bmi_category == 'Underweight':
        # GOAL: Calorie Density
        # Reject Low Calorie (< 100) to ensure they eat enough
        items = items.filter(calories__gte=100)
        
    # Normal: No restrictions beyond meal type
    
    return list(items)

def dynamic_portion_solver(food, meal_target_cal):
    """
    ENGINE C: DYNAMIC PORTION MATH
    Adjusts portion to meet the meal target.
    """
    base_cal = food.calories
    if base_cal <= 0: return "1 Serving", 0
    
    # Raw Count
    count = meal_target_cal / base_cal
    
    # Constraints
    if count > 3.0: count = 3.0
    if count < 0.5: count = 0.5
    
    # Rounding to nearest 0.5
    final_count = round(count * 2) / 2
    
    # Format
    qty_text = f"{final_count} {food.unit_name}"
    total_cal = int(final_count * base_cal)
    
    return qty_text, total_cal

@login_required
def generate_dynamic_diet_plan(request, patient_id, checkup_id):
    patient = get_object_or_404(Patient, id=patient_id)
    checkup = get_object_or_404(Checkup, id=checkup_id)
    
    # --- 1. RE-CALCULATE METRICS (Ensure fresh logic) ---
    bmi, bmr, tdee, category, target_calories = calculate_metrics(
        checkup.weight, checkup.height, checkup.age, patient.gender, checkup.activity
    )
    
    # Update Checkup Model with new calculations
    checkup.bmi = bmi
    checkup.bmr = bmr
    checkup.tdee = tdee
    checkup.category = category
    # (We could save target here if model had a field, using loose vars for now)
    
    # Define Macro Split (40/30/30 generic for now, can be tweaked)
    checkup.carbs_target = target_calories * 0.4 / 4
    checkup.protein_target = target_calories * 0.3 / 4
    checkup.fat_target = target_calories * 0.3 / 9
    checkup.save()

    # Determine Diet Goal based on BMI (Consistent with Metric Engine)
    diet_goal = "Maintenance"
    if bmi >= 25: diet_goal = "Weight Loss"
    elif bmi < 18.5: diet_goal = "Weight Gain"
    if checkup.plan_type == '3-Meal':
        splits = {'Breakfast': 0.30, 'Lunch': 0.40, 'Dinner': 0.30}
    else:
        splits = {'Breakfast': 0.25, 'Snack': 0.10, 'Lunch': 0.30, 'Dinner': 0.25}

    # --- 3. GENERATION LOOP ---
    existing_meals = AssignedMeal.objects.filter(checkup=checkup)
    
    # If incomplete, reset
    if existing_meals.exists() and existing_meals.count() < 7 * len(splits):
        existing_meals.delete() # Full reset for new logic
    
    if not AssignedMeal.objects.filter(checkup=checkup).exists():
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        # Pre-fetch pools to optimize
        pools = {}
        for meal in splits.keys():
            pools[meal] = smart_filter(meal, meal, checkup.dietary, category)
            # Shuffle deterministically
            random.Random(f"{patient.id}_{meal}").shuffle(pools[meal])
            
        for day in days:
            for meal_name, pct in splits.items():
                meal_target = target_calories * pct
                pool = pools[meal_name]
                
                if pool:
                    # Pick unique (rotate)
                    selected_food = pool.pop(0)
                    pools[meal_name].append(selected_food) # Rotate back to end
                    
                    # Solve Portion
                    qty_str, final_cal = dynamic_portion_solver(selected_food, meal_target)
                    
                    AssignedMeal.objects.create(
                        checkup=checkup, day=day, meal_type=meal_name,
                        food_item=selected_food,
                        quantity_text=qty_str,
                        total_calories=final_cal
                    )

    # --- 4. RETRIEVAL & DISPLAY ---
    weekly_plan = {}
    db_meals = AssignedMeal.objects.filter(checkup=checkup)
    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    for day in days_order:
        day_meals = db_meals.filter(day=day)
        day_list = []
        for m in day_meals.order_by('id'):
            day_list.append({
                'meal': m.meal_type, 'food': m.food_item.name,
                'qty': m.quantity_text,
                'cal': m.total_calories, 
                'p': m.food_item.protein, 'c': m.food_item.carbs, 'f': m.food_item.fat
            })
        weekly_plan[day] = day_list

    # Charts History
    history = Checkup.objects.filter(patient=patient).order_by('-id')
    graph_data = Checkup.objects.filter(patient=patient).order_by('id')
    c_labels = [f"#{h.id}" for h in graph_data]
    c_bmis = [float(h.bmi) for h in graph_data]

    # --- 5. AGGREGATES & SHOPPING LIST ---
    weekly_totals = {'cal':0, 'p':0, 'c':0, 'f':0, 'fiber':0, 'sugar':0}
    shopping_list = {}
    
    for m in db_meals:
        weekly_totals['cal'] += m.total_calories
        weekly_totals['p'] += m.food_item.protein
        weekly_totals['c'] += m.food_item.carbs
        weekly_totals['f'] += m.food_item.fat
        # Default 0 if missing in DB
        weekly_totals['fiber'] += getattr(m.food_item, 'fiber', 0)
        weekly_totals['sugar'] += getattr(m.food_item, 'sugar', 0)
        
        # Shopping List Logic
        fname = m.food_item.name
        if fname in shopping_list:
            shopping_list[fname]['qty'] += 1
        else:
            shopping_list[fname] = {
                'qty': 1, 
                'unit': m.food_item.unit_name,
                'cat': m.food_item.category
            }
            
    # Daily Averages
    daily_avg = {k: round(v / 7, 1) for k, v in weekly_totals.items()}
    
    # Weight Projection (Simplistic: 7700kcal = 1kg)
    # Weekly Deficit/Surplus = (TDEE - DailyAvg) * 7
    weekly_cal_diff = (tdee - daily_avg['cal']) * 7
    projected_weight_change = round(weekly_cal_diff / 7700, 2) # Negative = Loss

    context = {
        'patient': patient, 'checkup': checkup, 'history': history,
        'diet_goal': diet_goal, 'target_calories': int(target_calories),
        'weekly_plan': weekly_plan,
        'daily_avg': daily_avg,
        'shopping_list': shopping_list,
        'projected_change': projected_weight_change,
        'c_labels': c_labels, 'c_bmis': c_bmis
    }
    return render(request, 'patient_report.html', context)

@login_required
def download_pdf(request, checkup_id):
    checkup = get_object_or_404(Checkup, id=checkup_id)
    patient = checkup.patient
    
    # Re-calculate clinical targets (Ensure consistency with dashboard)
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

    # Retrieve full weekly plan
    weekly_plan = {}
    db_meals = AssignedMeal.objects.filter(checkup=checkup)
    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    for day in days_order:
        day_meals = db_meals.filter(day=day)
        day_list = []
        for m in day_meals.order_by('id'):
            day_list.append({
                'meal': m.meal_type, 'food': m.food_item.name,
                'qty': m.quantity_text,
                'cal': m.total_calories, 
                'p': m.food_item.protein, 'c': m.food_item.carbs, 'f': m.food_item.fat
            })
        weekly_plan[day] = day_list
    
    context = {
        'patient': patient, 
        'checkup': checkup, 
        'weekly_plan': weekly_plan,
        'target_calories': int(target_calories),
        'diet_goal': diet_goal
    }
    
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