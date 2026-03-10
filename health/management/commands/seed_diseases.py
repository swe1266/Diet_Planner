"""
Management command: seed_diseases
Seeds Disease + NutrientLimit tables from the master CSV.
Usage:
    python manage.py seed_diseases
    python manage.py seed_diseases --backfill
"""

import csv
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from health.models import Disease, NutrientLimit, Checkup

NUTRIENT_MAP = {
    'sodium':                        'sodium',
    'salt':                          'sodium',
    'saturated fat':                 'fat',
    'saturated fats':                'fat',
    'trans fat':                     'fat',
    'trans fats':                    'fat',
    'fat':                           'fat',
    'fats':                          'fat',
    'sugar':                         'sugar',
    'sugars':                        'sugar',
    'refined sugars':                'sugar',
    'sugar (refined)':               'sugar',
    'sugar (moderate)':              'sugar',
    'carbohydrates':                 'carbs',
    'carbs':                         'carbs',
    'carbohydrates (refined)':       'carbs',
    'carbohydrates (heavy/refined)': 'carbs',
    'protein':                       'protein',
    'proteins':                      'protein',
    'fiber':                         'fiber',
    'fibre':                         'fiber',
    'calcium':                       'calcium',
    'potassium':                     'potassium',
    'phosphorus':                    'phosphorus',
    'phosphorous':                   'phosphorus',
    'poteins':                       'protein',   # typo in CSV
    'fliuds':                        None,         # ignore — not a food nutrient
}

# Clinically-informed daily upper limits
THRESHOLDS = {
    'sodium':     1500.0,
    'sugar':        25.0,
    'fat':          55.0,
    'carbs':       225.0,
    'protein':      50.0,
    'fiber':        15.0,
    'calcium':    1200.0,
    'potassium':  2000.0,
    'phosphorus':  800.0,
}


class Command(BaseCommand):
    help = 'Seed Disease and NutrientLimit tables from master CSV.'

    def add_arguments(self, parser):
        parser.add_argument('--backfill', action='store_true',
                            help='Link existing Checkup.diseases text to Disease objects.')

    def handle(self, *args, **options):
        # CSV lives in the project root (BASE_DIR)
        csv_path = os.path.join(settings.BASE_DIR, 'Diseases - Sheet1.csv')

        if not os.path.exists(csv_path):
            self.stderr.write(f'[ERROR] CSV not found at: {csv_path}')
            return

        created_d = created_nl = skipped = 0

        with open(csv_path, encoding='utf-8') as f:
            for row in csv.DictReader(f):
                raw_name = (row.get('Diseases') or '').strip()
                raw_nut  = (row.get('Nutrients') or '').strip()

                if not raw_name:
                    continue

                disease_name = raw_name.strip().title()
                disease, d_new = Disease.objects.get_or_create(
                    name=disease_name,
                    defaults={'priority': 5}
                )
                if d_new:
                    created_d += 1

                if not raw_nut or raw_nut.lower() in ('n/a', ''):
                    skipped += 1
                    continue

                for token in raw_nut.split(','):
                    # Strip parenthetical qualifiers: "Sugar(moderate)" → "sugar"
                    clean = token.strip().lower().split('(')[0].strip()
                    canonical = NUTRIENT_MAP.get(clean)
                    if not canonical:
                        continue

                    _, nl_new = NutrientLimit.objects.get_or_create(
                        disease=disease,
                        nutrient=canonical,
                        defaults={
                            'max_daily_g': THRESHOLDS.get(canonical),
                            'is_banned':   False,
                        }
                    )
                    if nl_new:
                        created_nl += 1

        self.stdout.write(
            f'[OK] Seeded {created_d} diseases and {created_nl} nutrient limits. '
            f'({skipped} rows had no nutrient restrictions)'
        )

        if options['backfill']:
            self._backfill_checkups()

    def _backfill_checkups(self):
        linked = 0
        for checkup in Checkup.objects.filter(diseases__gt='').prefetch_related('disease_links'):
            if checkup.disease_links.exists():
                continue
            for raw in checkup.diseases.split(','):
                name = raw.strip().title()
                disease = (
                    Disease.objects.filter(name__iexact=name).first()
                    or Disease.objects.filter(name__icontains=name).first()
                )
                if disease:
                    checkup.disease_links.add(disease)
                    linked += 1

        self.stdout.write(f'[OK] Backfilled {linked} M2M disease links across existing Checkup records.')
