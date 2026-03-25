from django.contrib import admin
from .models import Patient, Checkup, FoodItem, Disease, AssignedMeal


@admin.register(Disease)
class DiseaseAdmin(admin.ModelAdmin):
    list_display  = ('name', 'priority')
    search_fields = ('name',)
    ordering      = ('-priority', 'name')


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display  = ('name', 'phone', 'gender', 'address')
    search_fields = ('name', 'phone')
    ordering      = ('-id',)


@admin.register(Checkup)
class CheckupAdmin(admin.ModelAdmin):
    list_display  = ('patient', 'date', 'bmi', 'category', 'plan_type', 'dietary')
    list_filter   = ('category', 'plan_type', 'dietary', 'date')
    search_fields = ('patient__name', 'patient__phone', 'diseases')
    ordering      = ('-date', '-id')
    filter_horizontal = ('disease_links',)


@admin.register(FoodItem)
class FoodItemAdmin(admin.ModelAdmin):
    list_display  = ('name', 'category', 'diet_type', 'calories', 'protein', 'carbs', 'fat')
    list_filter   = ('category', 'diet_type')
    search_fields = ('name',)
    ordering      = ('category', 'name')


@admin.register(AssignedMeal)
class AssignedMealAdmin(admin.ModelAdmin):
    list_display  = ('checkup', 'day', 'meal_type', 'food_item', 'quantity_text', 'total_calories')
    list_filter   = ('day', 'meal_type')
    search_fields = ('checkup__patient__name', 'food_item__name')
