import pandas as pd
import os
import re
import django

# Setup Django Environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dietplanner.settings')
django.setup()

from health.models import FoodItem

# --- HELPER FUNCTIONS ---

def clean_numeric(val):
    """
    Cleans strings like '100g', '50 kcal', '2.5' into float values.
    Returns 0.0 if value is invalid or missing.
    """
    if pd.isna(val) or val == '':
        return 0.0
    val = str(val).lower().strip()
    # Regex to extract the first valid number (integer or float)
    match = re.search(r"(\d+(\.\d+)?)", val)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return 0.0
    return 0.0

def infer_diet_type(name, forced_type=None):
    """Detects Veg/Non-Veg based on food name keywords."""
    if forced_type and pd.notna(forced_type):
        return str(forced_type).strip()
    
    name = str(name).lower()
    nv_keys = [
        'chicken', 'mutton', 'fish', 'egg', 'prawn', 'crab', 'non-veg', 
        'beef', 'pork', 'omelette', 'biryani', 'kebab', 'tandoori'
    ]
    if any(k in name for k in nv_keys):
        return 'Non-Veg'
    if 'vegan' in name:
        return 'Vegan'
    return 'Veg'

def infer_category(name, provided_cat=None):
    """Detects Breakfast/Lunch/Snack based on keywords if not provided."""
    if provided_cat and pd.notna(provided_cat):
        return str(provided_cat).strip().capitalize()

    name = str(name).lower()
    
    breakfast = [
        'idli', 'dosa', 'upma', 'pongal', 'paratha', 'toast', 'sandwich', 
        'pancake', 'oats', 'cereal', 'porridge', 'appam', 'puttu', 'idiyappam', 'puri'
    ]
    snack = [
        'soup', 'salad', 'biscuit', 'cookie', 'cake', 'juice', 'fruit', 'tea', 
        'coffee', 'sundal', 'makhana', 'buttermilk', 'water', 'puff', 'samosa', 
        'cutlet', 'fry', 'tikka', 'kebab', 'pakora', 'bajji', 'bonda', 'nuts', 'dates'
    ]
    
    if any(k in name for k in snack): return 'Snack'
    if any(k in name for k in breakfast): return 'Breakfast'
    
    # Default fallback for heavy items
    return 'Lunch'

def import_csv():
    print("🔄 Reading and Merging Datasets...")

    # 1. Define File Paths (Must match uploaded filenames)
    files = {
        'snack': 'diet_plan_snack.csv',
        'dataset': 'Dataset - Sheet1.csv',
        'nonveg': 'diet_pan_nonveg.csv',
        'hospital': 'hospital_food_data.csv'
    }

    dfs = []

    # 2. Read and Standardize 'Snack' Data
    if os.path.exists(files['snack']):
        df_s = pd.read_csv(files['snack'])
        df_s = df_s.rename(columns={
            'Food_items': 'name', 'Seving_desc': 'serving_desc', 
            'Calories_kcal': 'calories', 'Carbohydrate_g': 'carbs', 
            'Protien_g': 'protein', 'Fat_g': 'fat'
        })
        df_s['category'] = 'Snack'
        dfs.append(df_s)
        print(f"   -> Loaded {len(df_s)} items from Snacks.")

    # 3. Read and Standardize 'General Dataset'
    if os.path.exists(files['dataset']):
        df_d = pd.read_csv(files['dataset'])
        df_d = df_d.rename(columns={
            'Food_items': 'name', 'calorie_cal': 'calories', 
            'Protein_g': 'protein', 'carbohydrates_g': 'carbs', 
            'Fat_g': 'fat', 'serving_desc': 'serving_desc'
        })
        dfs.append(df_d)
        print(f"   -> Loaded {len(df_d)} items from General Dataset.")

    # 4. Read and Standardize 'Non-Veg' Data
    if os.path.exists(files['nonveg']):
        df_n = pd.read_csv(files['nonveg'])
        df_n = df_n.rename(columns={
            'Dish Name (Tamil Style)': 'name', 'Protein (g)': 'protein', 
            'Carbs (g)': 'carbs', 'Calories': 'calories', 
            'Quantity per Serving': 'serving_desc'
        })
        df_n['diet_type'] = 'Non-Veg'
        dfs.append(df_n)
        print(f"   -> Loaded {len(df_n)} items from Non-Veg.")

    # 5. Read and Standardize 'Hospital' Data (Priority Data)
    if os.path.exists(files['hospital']):
        df_h = pd.read_csv(files['hospital'])
        # Columns are likely already correct, but just in case
        dfs.append(df_h)
        print(f"   -> Loaded {len(df_h)} items from Hospital Data.")

    if not dfs:
        print("❌ No CSV files found! Please check file names.")
        return

    # 6. Merge All Dataframes
    combined_df = pd.concat(dfs, ignore_index=True)
    
    # 7. Ensure All Columns Exist with Defaults
    required_cols = ['name', 'category', 'diet_type', 'calories', 'protein', 
                     'carbs', 'fat', 'sodium', 'sugar', 'potassium', 
                     'phosphorus', 'ingredients', 'serving_desc']
    
    for col in required_cols:
        if col not in combined_df.columns:
            combined_df[col] = 0 if col in ['sodium', 'sugar', 'potassium', 'phosphorus', 'fat'] else ''

    # 8. Clean, Calculate & Deduplicate
    print("🧹 Cleaning data and calculating clinical flags...")
    
    clean_objects = []
    seen_names = set()

    # Process row by row to apply logic
    # We iterate reversed to keep the LAST occurrence (Hospital data was added last)
    # This ensures high-quality data overwrites generic data if duplicates exist.
    for i in range(len(combined_df) - 1, -1, -1):
        row = combined_df.iloc[i]
        
        raw_name = str(row['name']).strip()
        norm_name = raw_name.lower()
        
        if not raw_name or norm_name == 'nan' or norm_name in seen_names:
            continue
        
        seen_names.add(norm_name)

        # Value Cleaning
        cal = int(clean_numeric(row['calories']))
        prot = float(clean_numeric(row['protein']))
        carb = float(clean_numeric(row['carbs']))
        fat = float(clean_numeric(row['fat']))
        sod = float(clean_numeric(row['sodium']))
        sug = float(clean_numeric(row['sugar']))
        pot = float(clean_numeric(row['potassium']))
        phos = float(clean_numeric(row['phosphorus']))
        
        # Text Inference
        cat = infer_category(raw_name, row['category'])
        diet = infer_diet_type(raw_name, row['diet_type'])
        ing = str(row['ingredients']) if pd.notna(row['ingredients']) and row['ingredients'] != '' else raw_name.lower().replace(' ', ', ')
        unit = str(row['serving_desc']).split(' ')[-1] if pd.notna(row['serving_desc']) else 'Serving'
        desc = str(row['serving_desc']) if pd.notna(row['serving_desc']) else '1 Serving'

        # Clinical Safety Flags
        # Note: If Pot/Phos is 0 (missing data), we assume safe for now, 
        # but Hospital Data (with real values) takes precedence via deduplication.
        
        # Diabetes: < 50g Carbs AND < 5g Sugar
        is_dia = (carb < 50) and (sug < 10) # Slightly relaxed sugar for generic items
        
        # Renal: Low Prot (<15), Low Pot (<200), Low Phos (<150), Low Sod (<200)
        # Only strict if we actually have potassium data (pot > 0) OR if it's hospital data
        if pot > 0:
            is_ren = (prot < 15 and pot < 250 and phos < 200 and sod < 250)
        else:
            # If data missing, fallback to generic safe logic (Low Prot + Low Sod)
            is_ren = (prot < 10 and sod < 100) 

        # Cardiac: Low Fat (<10), Low Sod (<300)
        is_card = (fat < 12 and sod < 300)
        
        # Hypertension: Low Sod (<250)
        is_hyp = (sod < 250)

        # Create Model Object
        clean_objects.append(FoodItem(
            name=raw_name,
            category=cat,
            diet_type=diet,
            calories=cal, protein=prot, carbs=carb, fat=fat,
            sodium=sod, sugar=sug, potassium=pot, phosphorus=phos,
            ingredients=ing,
            unit_name=unit,
            serving_desc=desc,
            is_diabetes_safe=is_dia,
            is_renal_safe=is_ren,
            is_cardiac_safe=is_card,
            is_hypertension_safe=is_hyp
        ))

    # 9. Bulk Save
    print(f"💾 Saving {len(clean_objects)} unique items to database...")
    FoodItem.objects.all().delete()
    FoodItem.objects.bulk_create(clean_objects)
    print("✅ Success! Database successfully upgraded.")

if __name__ == "__main__":
    import_csv()