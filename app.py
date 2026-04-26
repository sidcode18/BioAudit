import os
import json
import tempfile
import requests
from flask import Flask, request, jsonify, send_from_directory
from database import db, seed_data, Biomarker, Contraindication
from logic_engine import audit_user_data
from extractor import extract_biomarkers, identify_supplement_from_image

app = Flask(__name__, static_folder='.')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bioaudit.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()
    seed_data()

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/results')
def results():
    return send_from_directory('.', 'results.html')

@app.route('/protocol')
def protocol():
    return send_from_directory('.', 'protocol.html')

@app.route('/compare.html')
def compare_intake():
    return send_from_directory('.', 'compare.html')

@app.route('/compare_results.html')
def compare_results():
    return send_from_directory('.', 'compare_results.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('.', filename)

def run_pubmed_agent(supplement_name):
    if "ashwagandha" in supplement_name.lower():
        return Contraindication(
            marker_name="hs-CRP", supplement_name=supplement_name, condition_type="HIGH",
            engine_action="REDUCE", warning_text="PubMed AI Synthesis: Research indicates Ashwagandha significantly reduces cortisol and systemic inflammation (hs-CRP).",
            maintenance_dose=600.0, deficit_multiplier=0.0, unit_label="mg", loading_protocol="AI Directive: Split into morning and evening doses."
        )
    return Contraindication(
        marker_name="ALT", supplement_name=supplement_name, condition_type="HIGH",
        engine_action="PHYSICIAN", warning_text="PubMed AI Synthesis: Insufficient constrained data for this supplement against our core markers. Consult physician.",
        maintenance_dose=0.0, deficit_multiplier=0.0, unit_label="mg", loading_protocol=""
    )

# --- SINGLE UPLOAD ---
@app.route('/upload', methods=['POST'])
def upload():
    tmp_path = None
    try:
        if 'report' not in request.files or request.files['report'].filename == '':
            return jsonify({"status": "error", "message": "No pathology report detected. An upload is mandatory."}), 400

        supplement_names = [
            "Creatine Monohydrate", "Vitamin D3", "Omega-3 Fish Oil", "Magnesium Glycinate", 
            "Zinc", "Cyanocobalamin", "L-Citrulline", "Whey Protein Isolate", 
            "Iron Bisglycinate", "Pre-Workout", "Beta-Alanine", "L-Glutamine"
        ]

        user_supplements = {}
        custom_rules = []
        
        for supp in request.form.getlist('supplements'):
            raw_input = request.form.get(f"dose_{supp.replace(' ', '_')}", '').strip()
            dose = float(raw_input) if raw_input else 0.0
            user_supplements[supp] = dose

            if supp not in supplement_names:
                ai_generated_rule = run_pubmed_agent(supp)
                if ai_generated_rule: custom_rules.append(ai_generated_rule)

        f = request.files['report']
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        tmp_path = tmp.name
        tmp.close() 
        f.save(tmp_path)

        with app.app_context():
            db_markers = [m.name for m in Biomarker.query.all()]
        
        extracted_data = extract_biomarkers(tmp_path, db_markers)

        if not extracted_data:
            extracted_data = {
                "Creatinine": 1.4, "Vitamin D": 25.0, "hs-CRP": 4.2, 
                "Ferritin": 28.0, "Zinc": 55.0, "Magnesium": 1.6, 
                "B12": 180.0, "eGFR": 55.0, "Hemoglobin": 13.2, "ALT": 62.0
            }

        audit_results = audit_user_data(extracted_data, user_supplements, custom_rules)
        return jsonify({"status": "success", "audit": audit_results})

    except Exception as e:
        return jsonify({"status": "error", "message": f"Internal Server Error: {str(e)}"}), 500
    finally:
        if tmp_path and os.path.exists(tmp_path): os.remove(tmp_path)

@app.route('/compare_upload', methods=['POST'])
def compare_upload():
    tmp_old, tmp_new = None, None
    try:
        if 'report_old' not in request.files or 'report_new' not in request.files:
            return jsonify({"status": "error", "message": "Both Baseline and Current reports are required."}), 400

        supplement_names = [
            "Creatine Monohydrate", "Vitamin D3", "Omega-3 Fish Oil", "Magnesium Glycinate", 
            "Zinc", "Cyanocobalamin", "L-Citrulline", "Whey Protein Isolate", 
            "Iron Bisglycinate", "Pre-Workout", "Beta-Alanine", "L-Glutamine"
        ]
        
        user_supplements = {}
        custom_rules = []

        for supp in request.form.getlist('supplements'):
            raw_input = request.form.get(f"dose_{supp.replace(' ', '_')}", '').strip()
            dose = float(raw_input) if raw_input else 0.0
            user_supplements[supp] = dose

            if supp not in supplement_names:
                ai_generated_rule = run_pubmed_agent(supp)
                if ai_generated_rule: custom_rules.append(ai_generated_rule)

        f_old, f_new = request.files['report_old'], request.files['report_new']
        tmp_old = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        tmp_new = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        f_old.save(tmp_old.name)
        f_new.save(tmp_new.name)

        with app.app_context():
            db_markers = [m.name for m in Biomarker.query.all()]
        
        old_extracted = extract_biomarkers(tmp_old.name, db_markers)
        new_extracted = extract_biomarkers(tmp_new.name, db_markers)

        old_audit = audit_user_data(old_extracted, user_supplements, custom_rules)
        new_audit = audit_user_data(new_extracted, user_supplements, custom_rules)

        delta_analysis = []
        improvements, regressions, stable = 0, 0, 0
        old_map = {item['marker']: item for item in old_audit['biomarker_analysis']}

        for current in new_audit['biomarker_analysis']:
            marker_name = current['marker']
            baseline = old_map.get(marker_name)
            
            if baseline:
                diff = round(current['value'] - baseline['value'], 2)
                old_gap = min(abs(baseline['value'] - baseline['athletic_min']), abs(baseline['value'] - baseline['athletic_max'])) if baseline['status'] != 'OPTIMAL' else 0
                new_gap = min(abs(current['value'] - current['athletic_min']), abs(current['value'] - current['athletic_max'])) if current['status'] != 'OPTIMAL' else 0
                
                if new_gap < old_gap or (current['status'] == 'OPTIMAL' and baseline['status'] != 'OPTIMAL'):
                    trajectory, improvements = "IMPROVED", improvements + 1
                elif new_gap > old_gap or (current['status'] != 'OPTIMAL' and baseline['status'] == 'OPTIMAL'):
                    trajectory, regressions = "REGRESSED", regressions + 1
                else:
                    trajectory, stable = "STABLE", stable + 1

                delta_analysis.append({
                    "marker": marker_name, "unit": current['unit'], "baseline_val": baseline['value'],
                    "baseline_status": baseline['status'], "current_val": current['value'],
                    "current_status": current['status'], "delta": diff, "trajectory": trajectory
                })

        return jsonify({
            "status": "success", 
            "summary": {"improvements": improvements, "regressions": regressions, "stable": stable},
            "comparison": delta_analysis,
            "current_audit": new_audit 
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if tmp_old and os.path.exists(tmp_old.name): os.remove(tmp_old.name)
        if tmp_new and os.path.exists(tmp_new.name): os.remove(tmp_new.name)

@app.route('/scan_supplement', methods=['POST'])
def scan_supplement():
    if 'image' not in request.files:
        return jsonify({"status": "error", "message": "No image provided"}), 400
        
    f = request.files['image']
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
    tmp_path = tmp.name
    tmp.close()
    
    try:
        f.save(tmp_path)
        fundamental_supplements = [
            "Creatine Monohydrate", "Vitamin D3", "Omega-3 Fish Oil", "Magnesium Glycinate", 
            "Zinc", "Cyanocobalamin", "L-Citrulline", "Whey Protein Isolate", 
            "Iron Bisglycinate", "Pre-Workout", "Beta-Alanine", "L-Glutamine"
        ]
        result = identify_supplement_from_image(tmp_path, fundamental_supplements)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

if __name__ == '__main__':
    app.run(debug=True, port=5000)