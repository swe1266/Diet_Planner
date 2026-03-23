from django.db import models


# ──────────────────────────────────────────────────────────────────────────────
# DISEASE CATALOG
# ──────────────────────────────────────────────────────────────────────────────

class Disease(models.Model):
    """
    Represents one medical condition with its nutrient-restriction metadata.
    Priority (1–10): higher value = this disease's restrictions override
    lower-priority ones when conflicts occur.
    """
    name     = models.CharField(max_length=200, unique=True)
    priority = models.IntegerField(
        default=5,
        help_text="1 = low priority, 10 = highest (overrides conflicts)"
    )
    restricted_nutrients = models.JSONField(
        default=dict,
        help_text='Format: {"sodium": {"banned": false, "max": 1500}, "sugar": {"banned": true}}'
    )

    def __str__(self):
        return self.name


# NutrientLimit is removed in favor of JSONField in Disease


# ──────────────────────────────────────────────────────────────────────────────
# PATIENT + CHECKUP
# ──────────────────────────────────────────────────────────────────────────────

class Patient(models.Model):
    name    = models.CharField(max_length=100)
    gender  = models.CharField(max_length=10)
    phone   = models.CharField(max_length=15, unique=True)
    address = models.TextField()

    def __str__(self):
        return f"{self.name} ({self.phone})"


class Checkup(models.Model):
    patient   = models.ForeignKey(Patient, on_delete=models.CASCADE)
    age       = models.IntegerField()
    height    = models.FloatField(help_text="cm")
    weight    = models.FloatField(help_text="kg")
    activity  = models.FloatField(help_text="Multiplier (1.2 – 1.9)")

    # Preferences
    dietary   = models.CharField(max_length=50, default="Non-Veg")
    plan_type = models.CharField(max_length=20, default="3-Meal")

    # ── Disease links (new, relational) ──────────────────────────────────────
    disease_links = models.ManyToManyField(
        Disease, blank=True,
        verbose_name="Medical Conditions",
        help_text="Select all applicable diseases for this checkup."
    )
    # Legacy plain-text field — kept for backward-compat & search display
    diseases = models.CharField(
        max_length=500, blank=True,
        help_text="Auto-synced comma-separated names from disease_links."
    )

    # Computed Metrics
    bmi      = models.FloatField()
    bmr      = models.FloatField()
    tdee     = models.FloatField()
    category = models.CharField(max_length=20)   # Underweight/Normal/Overweight/Obese
    blood_pressure = models.CharField(max_length=20, default="120/80")

    # Target Macros (Computed)
    protein_target = models.FloatField(default=0)
    carbs_target   = models.FloatField(default=0)
    fat_target     = models.FloatField(default=0)

    date = models.DateField(auto_now_add=True)

    def sync_diseases_text(self):
        """Keep legacy diseases CharField in sync with M2M disease_links."""
        self.diseases = ", ".join(
            self.disease_links.values_list('name', flat=True).order_by('name')
        )
        Checkup.objects.filter(pk=self.pk).update(diseases=self.diseases)

    def __str__(self):
        return f"{self.patient.name} — {self.date}"


# ──────────────────────────────────────────────────────────────────────────────
# FOOD CATALOG
# ──────────────────────────────────────────────────────────────────────────────

class FoodItem(models.Model):
    CATEGORY_CHOICES = [
        ('Breakfast', 'Breakfast'), ('Lunch', 'Lunch'),
        ('Dinner', 'Dinner'),       ('Snack', 'Snack'),
    ]
    DIET_TYPE = [
        ('Veg', 'Veg'), ('Non-Veg', 'Non-Veg'), ('Vegan', 'Vegan'),
    ]

    name     = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    diet_type= models.CharField(max_length=20, choices=DIET_TYPE)

    # Nutrition (Per 100 g serving)
    calories = models.FloatField() # Changed to FloatField for precision
    protein  = models.FloatField()
    carbs    = models.FloatField()
    fat      = models.FloatField()

    # Extended nutrients — used by NutrientLimit threshold checks
    fiber       = models.FloatField(default=0)
    sugar       = models.FloatField(default=0)
    sodium      = models.FloatField(default=0,   help_text="mg per 100 g")
    potassium   = models.FloatField(default=0,   help_text="mg per 100 g")
    calcium     = models.FloatField(default=0,   help_text="mg per 100 g")
    phosphorus  = models.FloatField(default=0,   help_text="mg per 100 g")

    # Portion display
    unit_name    = models.CharField(max_length=20, default="Serving")
    serving_desc = models.CharField(max_length=50, default="1 Serving")

    def save(self, *args, **kwargs):
        # Professional Validation: Prevent negative values
        for field in ['calories', 'protein', 'carbs', 'fat', 'sugar', 'fiber', 'sodium']:
            val = getattr(self, field)
            if val is not None and val < 0:
                raise ValueError(f"{field.capitalize()} cannot be negative.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.calories} kcal)"


# ──────────────────────────────────────────────────────────────────────────────
# ASSIGNED MEAL (generated plan)
# ──────────────────────────────────────────────────────────────────────────────

class AssignedMeal(models.Model):
    checkup   = models.ForeignKey(Checkup, on_delete=models.CASCADE)
    day       = models.CharField(max_length=15)
    meal_type = models.CharField(max_length=20)
    food_item = models.ForeignKey(FoodItem, on_delete=models.CASCADE)

    quantity_text  = models.CharField(max_length=50)   # e.g. "250 g"
    total_calories = models.IntegerField()

    def __str__(self):
        return f"{self.checkup.patient.name} — {self.day} — {self.meal_type}"
