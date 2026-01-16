from django.urls import path 
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('patients/', views.patients, name='patients'),
    path('contact/', views.contact, name='contact'),
    path('patients/new/', views.new_patient, name='new_patient'),
    path('patients/existing/', views.existing_patient, name='existing_patient'),
    path('patients/report/', views.patient_report, name='patient_report'),

]
