# 🏥 Hospital Diet Planner System

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-5.0-092E20?style=for-the-badge&logo=django&logoColor=white)
![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white)
![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=for-the-badge&logo=css3&logoColor=white)

> **A professional Clinical Nutrition Command Center designed for hospitals.**
> This application automates the calculation of patient nutritional needs (BMI, BMR, TDEE) and generates scientifically accurate diet plans instantly using a modern, secure interface.

---

## 🌟 Key Features

### 🖥️ 1. Professional Command Center
* **Live Dashboard:** Features a real-time clock, date, and system status indicators.
* **Quick Actions:** One-click access to Admit, Update, or View records.
* **Visual Stats:** At-a-glance view of patient activity and system health.

### 🩺 2. Patient Management
* **New Patient Registration:** Captures vitals (Height, Weight, BP, Activity Level) and instantly calculates metabolic rates.
* **Smart Updates (AJAX):** Search existing patients by **Phone Number** using a seamless pop-up modal to update weight/vitals without reloading the page.
* **Medical History:** A timeline view of all previous visits and diet reports.

### 🍎 3. Automated Diet Engine
The system replaces manual calculation with instant, medically accurate results:
* **BMI Categorization:** Auto-detects Underweight, Normal, Overweight, or Obese status.
* **Macro Split:** Automatically divides calories into **50% Carbs, 20% Protein, 30% Fats**.
* **Dynamic Plans:** Generates specific meal calorie targets for Breakfast, Lunch, Snacks, and Dinner.

### 🔒 4. Enterprise-Grade UI/UX
* **Dark Navy Theme:** A professional "Night Mode" aesthetic inspired by modern medical software.
* **Glassmorphism Sidebar:** Collapsible navigation with blur effects.
* **Read-Only Mode:** A dedicated search section for viewing records without risk of accidental edits.

---

## ⚙️ Medical Algorithms Used

The system ensures clinical accuracy using the following standard formulas:

### 1. Basal Metabolic Rate (BMR) - *Mifflin-St Jeor*
This equation is considered the most accurate for estimating BMR in clinical settings.
```math
Men: (10 × weight_kg) + (6.25 × height_cm) - (5 × age_years) + 5
Women: (10 × weight_kg) + (6.25 × height_cm) - (5 × age_years) - 161
