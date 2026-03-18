from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.template.loader import get_template
from django.db.models import Q
from django.contrib import messages
from xhtml2pdf import pisa
from .models import Patient, Checkup, FoodItem, AssignedMeal, Disease, NutrientLimit
import json
import random
import math
from datetime import timedelta

# ==========================================
# 1. DASHBOARD & STATIC PAGES
# ==========================================

@login_required
def home(request):
    from django.db.models import Avg, Count
    from datetime import date
    import calendar

    today = timezone.now().date()
    total_patients = Patient.objects.count()
    today_visits   = Checkup.objects.filter(date=today).count()

    # ------- BMI category counts (latest checkup per patient) -------
    underweight = normal = overweight = obese = 0
    bmi_sum = 0
    bmi_count = 0
    for p in Patient.objects.all():
        last = Checkup.objects.filter(patient=p).order_by('date').last()
        if last:
            bmi_sum += float(last.bmi)
            bmi_count += 1
            cat = last.category
            if 'Underweight' in cat:   underweight += 1
            elif 'Normal'    in cat:   normal      += 1
            elif 'Overweight' in cat:  overweight  += 1
            elif 'Obese'     in cat:   obese       += 1

    avg_bmi = round(bmi_sum / bmi_count, 1) if bmi_count else 0
    high_risk_pct = round((obese / total_patients) * 100) if total_patients else 0

    # ------- 30-day daily trends -------
    days_labels = []
    daily_visits = []
    for i in range(29, -1, -1):
        d = today - timedelta(days=i)
        days_labels.append(d.strftime('%b %d'))
        daily_visits.append(Checkup.objects.filter(date=d).count())

    # ------- Plan-type distribution -------
    plan_counts = {}
    for c in Checkup.objects.values('plan_type').annotate(cnt=Count('id')):
        plan_counts[c['plan_type'] or 'Other'] = c['cnt']

    # ------- Recent activity (last 6 real checkups) -------
    recent_checkups = (
        Checkup.objects
        .select_related('patient')
        .order_by('-date', '-id')[:6]
    )
    recent_activity = []
    for c in recent_checkups:
        # Compute diet_goal inline (not a model field)
        _bmi = float(c.bmi)
        _goal = 'Weight Loss' if _bmi >= 25 else ('Weight Gain' if _bmi < 18.5 else 'Maintenance')
        recent_activity.append({
            'patient_name': c.patient.name,
            'patient_id':   c.patient.id,
            'date':         c.date.strftime('%b %d, %Y'),
            'bmi':          _bmi,
            'category':     c.category,
            'goal':         _goal,
            'plan':         c.plan_type,
            'id':           c.id,
        })

    context = {
        'total_patients':  total_patients,
        'today_visits':    today_visits,
        'avg_bmi':         avg_bmi,
        'high_risk_pct':   high_risk_pct,
        'underweight': underweight, 'normal': normal,
        'overweight':  overweight,  'obese':  obese,
        'days_labels':  json.dumps(days_labels),
        'daily_visits': json.dumps(daily_visits),
        'plan_labels':  json.dumps(list(plan_counts.keys())),
        'plan_values':  json.dumps(list(plan_counts.values())),
        'recent_activity': recent_activity,
    }
    return render(request, 'home.html', context)

# ==========================================
# PROFILE & ACCOUNT
# ==========================================

@login_required
def profile(request):
    from django.db.models import Count, Avg
    user = request.user
    total_patients = Patient.objects.count()
    total_checkups  = Checkup.objects.count()

    today = timezone.now().date()
    today_checkups = Checkup.objects.filter(date=today).count()

    avg_bmi_q = Checkup.objects.aggregate(a=Avg('bmi'))
    avg_bmi   = round(avg_bmi_q['a'], 1) if avg_bmi_q['a'] else 0

    bmi_stats = {'Underweight': 0, 'Normal': 0, 'Overweight': 0, 'Obese': 0}
    for p in Patient.objects.all():
        last = Checkup.objects.filter(patient=p).order_by('date').last()
        if last:
            for key in bmi_stats:
                if key in last.category:
                    bmi_stats[key] += 1
                    break

    recent = (Checkup.objects.select_related('patient')
              .order_by('-date', '-id')[:3])

    context = {
        'user': user,
        'total_patients':  total_patients,
        'total_checkups':  total_checkups,
        'today_checkups':  today_checkups,
        'avg_bmi':         avg_bmi,
        'bmi_stats':       bmi_stats,
        'recent_checkups': recent,
        'date_joined':     user.date_joined,
        'last_login':      user.last_login,
    }
    return render(request, 'profile.html', context)


@login_required
def change_password(request):
    from django.contrib.auth import update_session_auth_hash
    if request.method == 'POST':
        old_pass  = request.POST.get('old_password', '')
        new_pass1 = request.POST.get('new_password1', '')
        new_pass2 = request.POST.get('new_password2', '')

        if not request.user.check_password(old_pass):
            messages.error(request, 'Current password is incorrect.')
        elif len(new_pass1) < 6:
            messages.error(request, 'New password must be at least 6 characters.')
        elif new_pass1 != new_pass2:
            messages.error(request, 'Passwords do not match.')
        else:
            request.user.set_password(new_pass1)
            request.user.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, 'Password changed successfully!')
        return redirect('profile')
    return redirect('profile')


@login_required
def patients(request):
    from django.db.models import Count
    all_patients = Patient.objects.all().order_by('-id')
    total_visits = Checkup.objects.count()
    male_count   = all_patients.filter(gender='Male').count()
    female_count = all_patients.filter(gender='Female').count()
    return render(request, 'patients.html', {
        'patients':     all_patients,
        'total_visits': total_visits,
        'male_count':   male_count,
        'female_count': female_count,
    })

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
    query      = request.GET.get('q', '').strip()
    bmi_filter = request.GET.get('bmi_filter', '')
    date_range = request.GET.get('date_range', '')

    error_message = None
    patients_data = []

    # View single patient detail
    if request.GET.get('view_id'):
        selected_patient = get_object_or_404(Patient, id=request.GET.get('view_id'))
        history = Checkup.objects.filter(patient=selected_patient).order_by('-date')
        return render(request, 'search_patient.html', {
            'selected_patient': selected_patient,
            'history':   history,
            'query':     query,
            'bmi_filter':  bmi_filter,
            'date_range':  date_range,
        })

    any_filter = query or bmi_filter or date_range

    if any_filter:
        qs = Patient.objects.all()

        if query:
            qs = qs.filter(Q(name__icontains=query) | Q(phone__icontains=query))

        today = timezone.now().date()
        if date_range == 'today':
            since = today
        elif date_range == 'week':
            since = today - timedelta(days=7)
        elif date_range == 'month':
            since = today - timedelta(days=30)
        else:
            since = None

        for p in qs:
            checkup_qs = Checkup.objects.filter(patient=p).order_by('-date')
            if since:
                checkup_qs = checkup_qs.filter(date__gte=since)
            latest = checkup_qs.first()

            if bmi_filter and latest and latest.category != bmi_filter:
                continue
            if since and not latest:
                continue
            if bmi_filter and not latest:
                continue

            patients_data.append({
                'patient':       p,
                'latest':        latest,
                'total_visits':  Checkup.objects.filter(patient=p).count(),
            })

        if not patients_data:
            error_message = "No patients match your search criteria."

    context = {
        'patients_data':  patients_data,
        'query':          query,
        'bmi_filter':     bmi_filter,
        'date_range':     date_range,
        'error_message':  error_message,
        'any_filter':     any_filter,
    }
    return render(request, 'search_patient.html', context)


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
        
        # Get diseases: hidden input sends a single comma-separated string
        diseases_str = request.POST.get('diseases', '').strip()
        
        blood_pressure = request.POST.get('bp', '120/80')
        
        bmi, bmr, tdee, category, target_calories = calculate_metrics(
            weight, height_cm, age, gender, activity
        )
        
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
            bmi=bmi,
            bmr=bmr,
            tdee=tdee,
            category=category,
            blood_pressure=blood_pressure,
            diseases=diseases_str,
            protein_target=protein_target,
            carbs_target=carbs_target,
            fat_target=fat_target
        )
        
        # ── Link diseases (M2M) and sync legacy text field ─────────────────
        _link_diseases_to_checkup(checkup, diseases_str)

        return redirect('generate_dynamic_diet_plan', patient_id=patient.id, checkup_id=checkup.id)

    # Build sorted unique disease name list from DB for the searchable dropdown
    all_diseases = list(Disease.objects.values_list('name', flat=True).order_by('name'))
    return render(request, 'new_patient.html', {
        'all_diseases_json': json.dumps(all_diseases)
    })

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
        
        # Get diseases: hidden input sends a single comma-separated string
        diseases_str = request.POST.get('diseases', '').strip()
        
        bp = request.POST.get('bp', '120/80')
        
        bmi, bmr, tdee, category, target_calories = calculate_metrics(
            weight, height_cm, age, patient.gender, activity
        )
        
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
            bmi=bmi,
            bmr=bmr,
            tdee=tdee,
            category=category,
            blood_pressure=bp,
            diseases=diseases_str,
            protein_target=protein_target,
            carbs_target=carbs_target,
            fat_target=fat_target
        )
        # ── Link diseases (M2M) and sync legacy text field ─────────────────
        _link_diseases_to_checkup(checkup, diseases_str)

        return redirect('generate_dynamic_diet_plan', patient_id=patient.id, checkup_id=checkup.id)

    # ---- GET: advanced search for existing patient ----
    query      = request.GET.get('q', '').strip()
    bmi_filter = request.GET.get('bmi_filter', '').strip()
    date_range = request.GET.get('date_range', '').strip()
    any_filter = bool(query or bmi_filter or date_range)

    patients_data = []
    error_message = None

    if any_filter:
        qs = Patient.objects.all()
        if query:
            qs = qs.filter(Q(name__icontains=query) | Q(phone__icontains=query))

        today = timezone.now().date()
        if date_range == 'today':
            since = today
        elif date_range == 'week':
            since = today - timedelta(days=7)
        elif date_range == 'month':
            since = today - timedelta(days=30)
        else:
            since = None

        for p in qs:
            checkup_qs = Checkup.objects.filter(patient=p).order_by('-date')
            if since:
                checkup_qs = checkup_qs.filter(date__gte=since)
            latest = checkup_qs.first()

            if bmi_filter and latest and latest.category != bmi_filter:
                continue
            if since and not latest:
                continue
            if bmi_filter and not latest:
                continue

            patients_data.append({
                'patient':      p,
                'latest':       latest,
                'total_visits': Checkup.objects.filter(patient=p).count(),
            })

        if not patients_data:
            error_message = "No patients match your search criteria."

    all_diseases = list(Disease.objects.values_list('name', flat=True).order_by('name'))
    context = {
        'patients_data':     patients_data,
        'query':             query,
        'bmi_filter':        bmi_filter,
        'date_range':        date_range,
        'any_filter':        any_filter,
        'error_message':     error_message,
        'all_diseases_json': json.dumps(all_diseases),
    }
    return render(request, 'existing_patient.html', context)


# ──────────────────────────────────────────────────────────────────────────────
# INTERNAL HELPER — link disease names to a Checkup
# ──────────────────────────────────────────────────────────────────────────────

def _link_diseases_to_checkup(checkup, diseases_str):
    """
    Given a comma-separated disease string from the form, resolve each name
    against the Disease table (exact then partial match), set the M2M, and
    sync the legacy diseases TextField.
    """
    checkup.disease_links.clear()
    names = [d.strip() for d in diseases_str.split(',') if d.strip()]
    for name in names:
        disease = (
            Disease.objects.filter(name__iexact=name).first()
            or Disease.objects.filter(name__icontains=name).first()
        )
        if disease:
            checkup.disease_links.add(disease)
    checkup.sync_diseases_text()


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
    
    # 2. BMR (Mifflin-St Jeor) — fixed gender check
    if gender.lower() == 'female':
        s = -161
    else:
        s = 5  # male or other
    
    bmr = (10 * weight) + (6.25 * height) - (5 * age) + s
    bmr = round(bmr, 2)
    
    # 3. TDEE
    tdee = round(bmr * activity, 2)
    
    # 4. Category & Target (Based on Body Type Logic step 3)
    if bmi < 18.5:
        category = "Underweight"
        target = 2350 # average of 2200-2500
    elif bmi < 25:
        category = "Normal"
        target = 2000
    elif bmi < 30:
        category = "Overweight"
        target = 1800
    else:
        category = "Obese"
        target = 1500
        
    # Safety Constraint
    if target < 1200:
        target = 1200
    
    return bmi, bmr, tdee, category, int(target)

def get_restricted_nutrients(diseases_str):
    """
    ENGINE A2: DISEASE RESTRICTIONS  (DB-backed, priority-aware)
    Queries NutrientLimit from the Disease model for each disease.
    Higher-priority disease wins on conflicts (e.g. Renal Failure > Constipation).
    Returns a dict: { nutrient: {'max': max_daily_g, 'banned': is_banned} }
    """
    if not diseases_str:
        return {}

    names = [d.strip() for d in diseases_str.split(',') if d.strip()]
    if not names:
        return {}

    # Resolve disease names → Disease objects (ordered by priority desc so
    # highest-priority disease is processed last and overwrites lower ones)
    diseases = (
        Disease.objects
        .filter(name__in=names)
        .prefetch_related('nutrient_limits')
        .order_by('priority')          # low priority first → high priority last (overwrites)
    )

    restrictions = {}
    for disease in diseases:
        for limit in disease.nutrient_limits.all():
            restrictions[limit.nutrient] = {
                'max': limit.max_daily_g,
                'banned': limit.is_banned
            }

    return restrictions


def _get_nutrient_list(diseases_str):
    """Returns a flat list of restricted nutrient names (for display in the UI)."""
    return sorted(get_restricted_nutrients(diseases_str).keys())

def smart_filter(category, meal_type, diet_pref, bmi_category, restrictions=None):
    """
    ENGINE B: SMART FILTER  (ORM-level, threshold-aware)
    restrictions = dict returned by get_restricted_nutrients():
        { 'sodium': {'max': 1500.0, 'banned': False}, ... }
    Smart defaults are applied when a restriction has no explicit threshold.
    """
    SMART_DEFAULTS = {
        'sodium':    400,    # mg  per 100 g serving
        'sugar':      8,     # g   per 100 g serving
        'fat':       30,     # g   per 100 g
        'carbs':     50,     # g   per 100 g
        'protein':   None,   # protein restriction — only filter very high-protein foods for renal
        'fiber':     None,   # high fiber is usually good; only restrict in IBD
        'potassium': None,
        'calcium':   None,
        'phosphorus':None,
    }

    items = FoodItem.objects.filter(category=meal_type)

    # ── Dietary preference filter ────────────────────────────────────────────
    if diet_pref == 'Veg':
        items = items.filter(diet_type__in=['Veg', 'Vegan'])
    elif diet_pref == 'Vegan':
        items = items.filter(diet_type='Vegan')

    # ── BMI-based base filters ──────────────────────────────────────────────
    if bmi_category in ['Obese', 'Overweight']:
        items = items.exclude(sugar__gt=8)
        items = items.filter(Q(fiber__gte=3) | Q(protein__gte=5))
    elif bmi_category == 'Underweight':
        items = items.filter(calories__gte=100)

    # ── Disease restriction filters (ORM-level, threshold-aware) ───────────
    if restrictions:
        for nutrient, rule in restrictions.items():
            if rule.get('banned'):
                # Completely exclude any food containing this nutrient (value > 0 is excluded)
                kwargs = {f"{nutrient}__gt": 0}
                items = items.exclude(**kwargs)
                continue

            max_daily = rule.get('max')
            # Fallback to Smart Defaults if no specific DB limit is found
            per_100g_limit = None
            if max_daily is not None:
                # Divide daily limit by ~4 to get a rough per-100g serving threshold
                # e.g., 1500mg daily Sodium -> 375mg per 100g max limit
                per_100g_limit = max_daily / 4.0
            else:
                per_100g_limit = SMART_DEFAULTS.get(nutrient)
                
            if per_100g_limit is None:
                continue   # no threshold to apply — skip

            # Explicitly apply > limit exclusion using ORM kwargs
            kwargs = {f"{nutrient}__gt": per_100g_limit}
            items = items.exclude(**kwargs)

    return list(items)

def dynamic_portion_solver(food, meal_target_cal):
    """
    ENGINE C: DYNAMIC PORTION MATH (Step 7)
    Adjusts portion to meet the meal target in Grams.
    """
    base_cal_per_100g = food.calories
    if base_cal_per_100g <= 0:
        return "100 g", 0
    
    # Required grams = (target calories / calories per 100g) * 100
    required_grams = (meal_target_cal / base_cal_per_100g) * 100
    
    # Sanity checks so we don't prescribe absurd amounts
    if required_grams > 500:
        required_grams = 500
    if required_grams < 20:
        required_grams = 20
        
    final_grams = round(required_grams / 10) * 10 # round to nearest 10g for cleaner UI
    
    qty_text = f"{final_grams} g"
    total_cal = int((final_grams / 100.0) * base_cal_per_100g)
    
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
    
    # Define Macro Split (40/30/30 generic for now)
    checkup.carbs_target = target_calories * 0.4 / 4
    checkup.protein_target = target_calories * 0.3 / 4
    checkup.fat_target = target_calories * 0.3 / 9
    checkup.save()

    # Determine Diet Goal based on BMI
    diet_goal = "Maintenance"
    if bmi >= 25:
        diet_goal = "Weight Loss"
    elif bmi < 18.5:
        diet_goal = "Weight Gain"

    if checkup.plan_type == '3-Meal':
        splits = {'Breakfast': 0.30, 'Lunch': 0.40, 'Dinner': 0.30}
    else:
        # 5-Meal Split
        splits = {
            'Breakfast': 0.25, 
            'Mid-Morning': 0.10, 
            'Lunch': 0.25, 
            'Evening Snack': 0.10, 
            'Dinner': 0.30
        }

    # --- 3. GENERATION LOOP ---
    existing_meals = AssignedMeal.objects.filter(checkup=checkup)
    
    if existing_meals.exists() and existing_meals.count() != 7 * len(splits):
        existing_meals.delete()
    
    if not AssignedMeal.objects.filter(checkup=checkup).exists():
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        # Determine disease restrictions from DB (returns dict {nutrient: threshold})
        restricted = get_restricted_nutrients(checkup.diseases)
        
        pools = {}
        for meal in splits.keys():
            pools[meal] = smart_filter(meal, meal, checkup.dietary, category, restricted)
            random.Random(f"{patient.id}_{meal}").shuffle(pools[meal])
            
        for day in days:
            for meal_name, pct in splits.items():
                meal_target = target_calories * pct
                pool = pools[meal_name]
                
                if pool:
                    selected_food = pool.pop(0)
                    pools[meal_name].append(selected_food)
                    
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

    # Charts History & Analytics
    history = Checkup.objects.filter(patient=patient).order_by('-id')
    
    analytics_data = Checkup.objects.filter(patient=patient).order_by('date')
    
    a_dates = [h.date.strftime("%b %d") for h in analytics_data]
    a_weights = [float(h.weight) for h in analytics_data]
    a_bmis = [float(h.bmi) for h in analytics_data]
    
    start_weight = a_weights[0] if a_weights else 0
    current_w = a_weights[-1] if a_weights else 0
    total_weight_change = round(current_w - start_weight, 2)
    
    start_bmi = a_bmis[0] if a_bmis else 0
    current_b = a_bmis[-1] if a_bmis else 0
    total_bmi_change = round(current_b - start_bmi, 2)

    # --- 5. AGGREGATES & SHOPPING LIST ---
    weekly_totals = {'cal': 0, 'p': 0, 'c': 0, 'f': 0, 'fiber': 0, 'sugar': 0}
    shopping_list = {}
    
    for m in db_meals:
        weekly_totals['cal'] += m.total_calories
        weekly_totals['p'] += m.food_item.protein
        weekly_totals['c'] += m.food_item.carbs
        weekly_totals['f'] += m.food_item.fat
        weekly_totals['fiber'] += getattr(m.food_item, 'fiber', 0)
        weekly_totals['sugar'] += getattr(m.food_item, 'sugar', 0)
        
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
    
    # Weight Projection (7700 kcal ≈ 1 kg; multiply by 8 to get 8-week total)
    weekly_cal_diff = (tdee - daily_avg['cal']) * 7
    projected_weight_change = round((weekly_cal_diff / 7700) * 8, 2)  # 8-week total

    # Prepare WhatsApp Share Text
    whatsapp_text = f"Hello {patient.name}, here is your personalized diet plan for this week:\n\n"
    for day, meals in weekly_plan.items():
        whatsapp_text += f"📅 *{day}*\n"
        for m in meals:
            whatsapp_text += f"- {m['meal']}: {m['food']} ({m['cal']} kcal)\n"
        whatsapp_text += "\n"
    
    whatsapp_text += "Stay healthy!\n- LifeCare Clinic"
    
    import urllib.parse
    whatsapp_link = f"https://wa.me/{patient.phone.replace(' ', '').replace('-', '')}?text={urllib.parse.quote(whatsapp_text)}"

    # Restricted nutrients for display (list of names)
    restricted_nutrients = _get_nutrient_list(checkup.diseases)

    # Pre-split diseases list so template doesn't need to call .split()
    diseases_list = [d.strip() for d in checkup.diseases.split(',') if d.strip()] if checkup.diseases else []

    context = {
        'patient': patient, 'checkup': checkup, 'history': history,
        'diet_goal': diet_goal, 'target_calories': int(target_calories),
        'weekly_plan': weekly_plan,
        'daily_avg': daily_avg,
        'shopping_list': shopping_list,
        'projected_change': projected_weight_change,
        'restricted_nutrients': restricted_nutrients,
        'diseases_list': diseases_list,
        # Analytics Data
        'a_dates': json.dumps(a_dates),
        'a_weights': json.dumps(a_weights),
        'a_bmis': json.dumps(a_bmis),
        'total_weight_change': total_weight_change,
        'total_bmi_change': total_bmi_change,
        'start_weight': start_weight,
        'whatsapp_link': whatsapp_link,
    }
    return render(request, 'patient_report.html', context)

@login_required
def download_pdf(request, checkup_id):
    checkup = get_object_or_404(Checkup, id=checkup_id)
    patient = checkup.patient
    
    # Use the same calculate_metrics engine for consistency
    bmi, bmr, tdee, category, target_calories = calculate_metrics(
        checkup.weight, checkup.height, checkup.age, patient.gender, checkup.activity
    )
    
    diet_goal = "Maintenance"
    if bmi >= 25:
        diet_goal = "Weight Loss"
    elif bmi < 18.5:
        diet_goal = "Weight Gain"
    
    # Macro Targets (g)
    protein_g  = round(target_calories * 0.30 / 4, 1)
    carbs_g    = round(target_calories * 0.40 / 4, 1)
    fat_g      = round(target_calories * 0.30 / 9, 1)

    # Activity label map
    activity_map = {
        1.2: "Sedentary", 1.375: "Lightly Active",
        1.55: "Moderately Active", 1.725: "Very Active", 1.9: "Super Active"
    }
    activity_label = activity_map.get(round(checkup.activity, 3), f"{checkup.activity}×")

    # Weekly aggregates
    db_meals = AssignedMeal.objects.filter(checkup=checkup)
    weekly_total_cal = sum(m.total_calories for m in db_meals)
    daily_avg_cal    = round(weekly_total_cal / 7) if weekly_total_cal else 0

    # Full weekly plan
    weekly_plan = {}
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

    bmi_color_map = {
        'Underweight': '#3b82f6',
        'Normal':      '#10b981',
        'Overweight':  '#f59e0b',
        'Obese':       '#ef4444',
    }
    bmi_color = bmi_color_map.get(checkup.category, '#0891b2')

    dietitian_name = request.user.get_full_name() or request.user.username.title()

    context = {
        'patient': patient, 
        'checkup': checkup, 
        'weekly_plan': weekly_plan,
        'target_calories': int(target_calories),
        'diet_goal': diet_goal,
        'protein_g': protein_g,
        'carbs_g': carbs_g,
        'fat_g': fat_g,
        'activity_label': activity_label,
        'daily_avg_cal': daily_avg_cal,
        'bmi_color': bmi_color,
        'dietitian_name': dietitian_name,
    }
    
    template_path = 'pdf_report.html'
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Report_{patient.name}_{checkup.id}.pdf"'
    template = get_template(template_path)
    html = template.render(context)
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('Errors <pre>' + html + '</pre>')
    return response

@login_required
def regenerate_plan(request, checkup_id):
    checkup = get_object_or_404(Checkup, id=checkup_id)
    AssignedMeal.objects.filter(checkup=checkup).delete()
    messages.success(request, "Diet plan has been regenerated with new options!")
    return redirect('generate_dynamic_diet_plan', patient_id=checkup.patient.id, checkup_id=checkup.id)