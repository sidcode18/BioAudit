from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Biomarker(db.Model):
    __tablename__ = 'biomarkers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    clinical_min = db.Column(db.Float, nullable=False)
    clinical_max = db.Column(db.Float, nullable=False)
    athletic_min = db.Column(db.Float, nullable=False)
    athletic_max = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(30), nullable=False)

class Contraindication(db.Model):
    __tablename__ = 'contraindications'
    id = db.Column(db.Integer, primary_key=True)
    marker_name = db.Column(db.String(100), nullable=False)
    supplement_name = db.Column(db.String(100), nullable=False)
    condition_type = db.Column(db.String(10), nullable=False)  # Trigger Condition (HIGH/LOW)
    engine_action = db.Column(db.String(20), nullable=False)   # Pharmacokinetic Action (REDUCE/INCREASE)
    warning_text = db.Column(db.Text, nullable=True)
    maintenance_dose = db.Column(db.Float, nullable=True)
    deficit_multiplier = db.Column(db.Float, nullable=True)
    unit_label = db.Column(db.String(30), nullable=True)
    loading_protocol = db.Column(db.Text, nullable=True)

def seed_data():
    db.session.query(Biomarker).delete()
    db.session.query(Contraindication).delete()

    biomarkers = [
        Biomarker(name="Creatinine", clinical_min=0.6, clinical_max=1.2, athletic_min=0.8, athletic_max=1.1, unit="mg/dL"),
        Biomarker(name="Vitamin D", clinical_min=20.0, clinical_max=100.0, athletic_min=40.0, athletic_max=80.0, unit="ng/mL"),
        Biomarker(name="hs-CRP", clinical_min=0.0, clinical_max=3.0, athletic_min=0.0, athletic_max=1.0, unit="mg/L"),
        Biomarker(name="Ferritin", clinical_min=12.0, clinical_max=300.0, athletic_min=50.0, athletic_max=200.0, unit="ng/mL"),
        Biomarker(name="Zinc", clinical_min=60.0, clinical_max=120.0, athletic_min=80.0, athletic_max=110.0, unit="mcg/dL"),
        Biomarker(name="Magnesium", clinical_min=1.5, clinical_max=2.5, athletic_min=1.9, athletic_max=2.4, unit="mg/dL"),
        Biomarker(name="B12", clinical_min=200.0, clinical_max=900.0, athletic_min=400.0, athletic_max=800.0, unit="pg/mL"),
        Biomarker(name="eGFR", clinical_min=60.0, clinical_max=120.0, athletic_min=90.0, athletic_max=120.0, unit="mL/min/1.73m²"),
        Biomarker(name="Hemoglobin", clinical_min=12.0, clinical_max=17.5, athletic_min=14.0, athletic_max=17.0, unit="g/dL"),
        Biomarker(name="ALT", clinical_min=7.0, clinical_max=56.0, athletic_min=7.0, athletic_max=40.0, unit="U/L"),
    ]
    db.session.bulk_save_objects(biomarkers)

    contraindications = [
        Contraindication(marker_name="Creatinine", supplement_name="Creatine Monohydrate", condition_type="HIGH", engine_action="REDUCE", warning_text="Elevated creatinine indicates potential renal stress. Exogenous creatine elevates serum creatinine artifactually.", maintenance_dose=0.0, deficit_multiplier=0.0, unit_label="g", loading_protocol=None),
        Contraindication(marker_name="Vitamin D", supplement_name="Vitamin D3", condition_type="LOW", engine_action="INCREASE", warning_text="Vitamin D deficiency impairs calcium absorption and testosterone biosynthesis.", maintenance_dose=5000.0, deficit_multiplier=100.0, unit_label="IU", loading_protocol="Loading phase: 10,000 IU/day for 8 weeks."),
        Contraindication(marker_name="hs-CRP", supplement_name="Omega-3 Fish Oil", condition_type="HIGH", engine_action="INCREASE", warning_text="Elevated hs-CRP signals inflammation. Omega-3 directly suppresses NF-κB pathways.", maintenance_dose=3.0, deficit_multiplier=0.5, unit_label="g", loading_protocol=None),
        Contraindication(marker_name="Magnesium", supplement_name="Magnesium Glycinate", condition_type="LOW", engine_action="INCREASE", warning_text="Hypomagnesemia disrupts ATP synthesis and neuromuscular function.", maintenance_dose=400.0, deficit_multiplier=50.0, unit_label="mg", loading_protocol=None),
        Contraindication(marker_name="Zinc", supplement_name="Zinc", condition_type="LOW", engine_action="INCREASE", warning_text="Zinc deficiency impairs immune function and protein metabolism.", maintenance_dose=30.0, deficit_multiplier=0.5, unit_label="mg", loading_protocol=None),
        Contraindication(marker_name="B12", supplement_name="Cyanocobalamin", condition_type="LOW", engine_action="INCREASE", warning_text="Suboptimal B12 causes fatigue and impairs myelin synthesis.", maintenance_dose=1000.0, deficit_multiplier=2.0, unit_label="mcg", loading_protocol="Consider IM injections if oral repletion fails."),
        Contraindication(marker_name="eGFR", supplement_name="L-Citrulline", condition_type="LOW", engine_action="REDUCE", warning_text="Reduced eGFR contraindicates high-dose citrulline due to metabolite accumulation.", maintenance_dose=0.0, deficit_multiplier=0.0, unit_label="g", loading_protocol=None),
        Contraindication(marker_name="Creatinine", supplement_name="Whey Protein Isolate", condition_type="HIGH", engine_action="REDUCE", warning_text="High renal filtration load can compound existing creatinine elevation.", maintenance_dose=0.0, deficit_multiplier=0.0, unit_label="g", loading_protocol=None),
        Contraindication(marker_name="Ferritin", supplement_name="Iron Bisglycinate", condition_type="LOW", engine_action="INCREASE", warning_text="Low ferritin severely impairs VO2max and hemoglobin synthesis.", maintenance_dose=36.0, deficit_multiplier=1.2, unit_label="mg", loading_protocol="Split into two daily doses with Vitamin C."),
        Contraindication(marker_name="hs-CRP", supplement_name="Pre-Workout", condition_type="HIGH", engine_action="REDUCE", warning_text="High-stimulant pre-workouts spike cortisol and worsen inflammatory cascades.", maintenance_dose=0.0, deficit_multiplier=0.0, unit_label="serving", loading_protocol=None),
        Contraindication(marker_name="hs-CRP", supplement_name="Beta-Alanine", condition_type="HIGH", engine_action="REDUCE", warning_text="Beta-alanine may exacerbate oxidative stress in systemic inflammation.", maintenance_dose=0.0, deficit_multiplier=0.0, unit_label="g", loading_protocol=None),
        Contraindication(marker_name="eGFR", supplement_name="L-Glutamine", condition_type="LOW", engine_action="REDUCE", warning_text="Excessive glutamine metabolism increases urea production and renal burden.", maintenance_dose=0.0, deficit_multiplier=0.0, unit_label="g", loading_protocol=None),
    ]
    db.session.bulk_save_objects(contraindications)
    db.session.commit()
    print("✓ BioAudit database seeded successfully.")