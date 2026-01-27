from django.contrib import admin
from django.urls import path
from health import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    # Admin & Authentication
    path('admin/', admin.site.urls),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # Dashboard & Static Pages
    path('', views.home, name='home'),
    path('patients/', views.patients, name='patients'),
    path('contact/', views.contact, name='contact'),

    # Patient Forms
    path('patients/new/', views.new_patient, name='new_patient'),
    path('patients/existing/', views.existing_patient, name='existing_patient'),
    path('patients/search/', views.search_patient, name='search_patient'),

    # Reports
    path('report/<int:patient_id>/<int:checkup_id>/', views.generate_dynamic_diet_plan, name='generate_dynamic_diet_plan'),

    # API for Pop-up Search
    path('get_patient_details/', views.get_patient_details, name='get_patient_details'),

    # --- THIS WAS MISSING ---
    path('delete_checkup/<int:checkup_id>/', views.delete_checkup, name='delete_checkup'),
]