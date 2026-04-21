from database import Biomarker, Contraindication

def audit_user_data(extracted_data: dict, user_supplements: dict) -> dict:
    results = {
        "summary": {"total_analyzed": 0, "critical": 0, "sub_optimal": 0, "optimal": 0},
        "biomarker_analysis": [],
        "supplement_directives": [],
        "physician_referrals": []
    }
    has_critical = False

    for marker_name, value in extracted_data.items():
        bm = Biomarker.query.filter_by(name=marker_name).first()
        if not bm: continue

        results["summary"]["total_analyzed"] += 1
        status, tier, direction = "OPTIMAL", 0, None

        if value > bm.clinical_max * 1.2: status, tier, direction = "CRITICAL", 3, "HIGH"
        elif value > bm.clinical_max: status, tier, direction = "HIGH_CLINICAL", 2, "HIGH"
        elif value > bm.athletic_max: status, tier, direction = "HIGH_ATHLETIC", 1, "HIGH"
        elif value < bm.clinical_min * 0.8: status, tier, direction = "CRITICAL", 3, "LOW"
        elif value < bm.clinical_min: status, tier, direction = "LOW_CLINICAL", 2, "LOW"
        elif value < bm.athletic_min: status, tier, direction = "LOW_ATHLETIC", 1, "LOW"

        if status == "CRITICAL":
            results["summary"]["critical"] += 1
            has_critical = True
        elif status != "OPTIMAL": results["summary"]["sub_optimal"] += 1
        else: results["summary"]["optimal"] += 1

        biomarker_entry = {
            "marker": marker_name, "value": value, "unit": bm.unit,
            "status": status, "tier": tier, "direction": direction,
            "clinical_min": bm.clinical_min, "clinical_max": bm.clinical_max,
            "athletic_min": bm.athletic_min, "athletic_max": bm.athletic_max,
            "supplement_actions": []
        }

        if direction:
            contraindications = Contraindication.query.filter_by(marker_name=marker_name, condition_type=direction).all()

            for contra in contraindications:
                is_taking = contra.supplement_name in user_supplements
                user_dose = user_supplements.get(contra.supplement_name, 0.0)
                directive_output, action_type = "", ""

                if contra.engine_action == "REDUCE":
                    if not is_taking or user_dose <= 0: continue 
                    if tier == 3:
                        directive_output, action_type = f"0 {contra.unit_label} (Cease Immediately)", "ELIMINATE"
                    else:
                        modifier = 0.25 if tier == 2 else 0.50
                        target = round(user_dose * modifier, 2)
                        directive_output, action_type = f"Target Dosage: {target} {contra.unit_label}", "REDUCE"

                elif contra.engine_action == "INCREASE":
                    if tier == 3 and direction == "LOW":
                        directive_output, action_type = "Medical Admin Required", "PHYSICIAN"
                    else:
                        gap = abs(bm.athletic_min - value) if direction == "LOW" else abs(value - bm.athletic_max)
                        multiplier = contra.deficit_multiplier or 1.0
                        base = contra.maintenance_dose or 0.0
                        addition = gap * multiplier
                        if tier >= 2: addition *= 1.5 
                        
                        calc_target = base + addition
                        target = min(round(calc_target, 1), base * 3) if base > 0 else round(calc_target, 1)

                        if is_taking and user_dose >= target: 
                            overload_target = round(user_dose * 1.2, 1)
                            # TOXIC BYPASS PROTECTION
                            if base > 0 and overload_target > (base * 3):
                                target = base * 3
                                action_type = "PHYSICIAN"
                                directive_output = f"Max safe limit reached: {target} {contra.unit_label}. Consult Physician."
                            else:
                                target = overload_target
                                directive_output, action_type = f"Target Dosage: {target} {contra.unit_label}", "INCREASE"
                        else:
                            directive_output, action_type = f"Target Dosage: {target} {contra.unit_label}", "INCREASE"

                        if contra.loading_protocol: directive_output += f" | {contra.loading_protocol}"

                biomarker_entry["supplement_actions"].append({
                    "supplement": contra.supplement_name, "action_type": action_type,
                    "output": directive_output, "warning_text": contra.warning_text
                })
                results["supplement_directives"].append({
                    "supplement": contra.supplement_name, "action_type": action_type,
                    "output": directive_output, "marker": marker_name, "status": status
                })

        results["biomarker_analysis"].append(biomarker_entry)

    if has_critical:
        for b in [x for x in results["biomarker_analysis"] if x["status"] == "CRITICAL"]:
            results["physician_referrals"].append({
                "marker": b["marker"],
                "message": f"PHYSICIAN REFERRAL REQUIRED: {b['marker']} is critically aberrant."
            })

    return results