from django.shortcuts import render, redirect

from .models import Patient, Checkup



# ---------- Static Pages ----------
def home(request):
    return render(request, 'home.html')

def patients(request):
    return render(request, 'patients.html')

def contact(request):
    return render(request, 'contact.html')


# ---------- NEW PATIENT ----------
def new_patient(request):
    if request.method == 'POST':
        # ---- Patient info ----
        name = request.POST['name']
        gender = request.POST['gender']
        phone = request.POST['phone']
        address = request.POST['address']

        # ---- Checkup info ----
        age = int(request.POST['age'])
        height_cm = float(request.POST['height'])
        weight = float(request.POST['weight'])
        bp = request.POST['bp']
        activity = float(request.POST['activity'])

        height_m = height_cm / 100

        # ---- Calculations ----
        bmi = round(weight / (height_m ** 2), 2)

        if gender == 'male':
            bmr = 88.36 + (13.4 * weight) + (4.8 * height_cm) - (5.7 * age)
        else:
            bmr = 447.6 + (9.2 * weight) + (3.1 * height_cm) - (4.3 * age)

        bmr = round(bmr, 2)
        tdee = round(bmr * activity, 2)

        # ---- BMI Category ----
        if bmi < 18.5:
            category = "Underweight"
        elif bmi < 25:
            category = "Normal"
        elif bmi < 30:
            category = "Overweight"
        else:
            category = "Obese"

        # ---- Macronutrients ----
        carbs = round((tdee * 0.5) / 4, 2)
        protein = round((tdee * 0.2) / 4, 2)
        fat = round((tdee * 0.3) / 9, 2)

        # ---- Meal Calories (example split) ----
        breakfast_cal = tdee * 0.25   # 25%
        lunch_cal     = tdee * 0.35   # 35%
        snacks_cal    = tdee * 0.10   # 10%
        dinner_cal    = tdee * 0.30   # 30%

        # ---- Save Patient ----
        patient, created = Patient.objects.get_or_create(
            phone=phone,
            defaults={
                'name': name,
                'gender': gender,
                'address': address
            }
        )

        # ---- Save First Checkup ----
        Checkup.objects.create(
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

        # ---- Save report session ----
        request.session['report'] = {
            'patient_id': patient.id,
            'bmi': bmi,
            'bmi_status': category,
            'bmr': bmr,
            'tdee': tdee,
            'carbs': carbs,
            'protein': protein,
            'fat': fat,
            'breakfast_cal': breakfast_cal,
            'lunch_cal': lunch_cal,
            'snacks_cal': snacks_cal,
            'dinner_cal': dinner_cal
        }

        return redirect('generate_dynamic_diet_plan', patient_id=patient.id, checkup_id=Checkup.objects.latest('id').id)


    return render(request, 'new_patient.html')


# ---------- EXISTING PATIENT ----------
def existing_patient(request):
    if request.method == "POST":
        phone = request.POST['phone']

        try:
            patient = Patient.objects.get(phone=phone)
        except Patient.DoesNotExist:
            return render(request, 'existing_patient.html', {
                'error': 'Patient not found. Please register as new patient.'
            })

        age = int(request.POST['age'])
        height_cm = float(request.POST['height'])
        weight = float(request.POST['weight'])
        bp = request.POST['bp']
        activity = float(request.POST['activity'])

        height_m = height_cm / 100

        bmi = round(weight / (height_m ** 2), 2)

        if patient.gender == 'male':
            bmr = 88.36 + (13.4 * weight) + (4.8 * height_cm) - (5.7 * age)
        else:
            bmr = 447.6 + (9.2 * weight) + (3.1 * height_cm) - (4.3 * age)

        bmr = round(bmr, 2)
        tdee = round(bmr * activity, 2)

        # ---- BMI Category ----
        if bmi < 18.5:
            category = "Underweight"
        elif bmi < 25:
            category = "Normal"
        elif bmi < 30:
            category = "Overweight"
        else:
            category = "Obese"

        # ---- Macronutrients ----
        carbs = round((tdee * 0.5) / 4, 2)
        protein = round((tdee * 0.2) / 4, 2)
        fat = round((tdee * 0.3) / 9, 2)

        # ---- Meal Calories ----
        breakfast_cal = tdee * 0.25
        lunch_cal     = tdee * 0.35
        snacks_cal    = tdee * 0.10
        dinner_cal    = tdee * 0.30

        # ---- Save new checkup ----
        Checkup.objects.create(
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

        # ---- Save report session ----
        request.session['report'] = {
            'patient_id': patient.id,
            'bmi': bmi,
            'bmi_status': category,
            'bmr': bmr,
            'tdee': tdee,
            'carbs': carbs,
            'protein': protein,
            'fat': fat,
            'breakfast_cal': breakfast_cal,
            'lunch_cal': lunch_cal,
            'snacks_cal': snacks_cal,
            'dinner_cal': dinner_cal
        }

        return redirect('patient_report')

    return render(request, 'existing_patient.html')


# ---------- PATIENT REPORT ----------
def patient_report(request):
    data = request.session.get('report')
    if not data:
        return redirect('new_patient')

    patient = Patient.objects.get(id=data['patient_id'])
    checkup = Checkup.objects.filter(patient=patient).latest('id')

    context = {
        'patient': patient,
        'bmi': round(data['bmi'], 1),
        'bmi_status': data['bmi_status'],
        'bmr': round(data['bmr'], 2),
        'tdee': round(data['tdee'], 2),
        'carbs': round(data['carbs'], 2),
        'protein': round(data['protein'], 2),
        'fat': round(data['fat'], 2),
        'age': checkup.age,
        'height': checkup.height,
        'weight': checkup.weight,
    }

    return render(request, 'patient_report.html', context)


