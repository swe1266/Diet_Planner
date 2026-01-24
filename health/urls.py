from django.urls import path
from . import views

urlpatterns = [
    # Static Pages
    path('', views.home, name='home'),
    path('patients/', views.patients, name='patients'),
    path('contact/', views.contact, name='contact'),

    # Patient Forms
    path('patients/new/', views.new_patient, name='new_patient'),
    path('patients/existing/', views.existing_patient, name='existing_patient'),

    # NEW API for the Pop-up (This was missing)
    path('get_patient_details/', views.get_patient_details, name='get_patient_details'),

    # The Report Page (Renamed from patient_report to generate_dynamic_diet_plan)
    path('report/<int:patient_id>/<int:checkup_id>/', views.generate_dynamic_diet_plan, name='generate_dynamic_diet_plan'),

    # Add this line to your urlpatterns list:
    path('patients/search/', views.search_patient, name='search_patient'),
]