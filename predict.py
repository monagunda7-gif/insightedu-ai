def predict_risk(s, sgpa_records=None):
    """Transparent demo heuristic using current CIE average and historical SGPA."""
    cie_average = (float(s["cie1"]) + float(s["cie2"])) / 2
    records = sgpa_records or []
    sgpa_average = (sum(float(x["sgpa"]) for x in records) / len(records)) if records else None
    if sgpa_average is None:
        academic_index = cie_average
        basis = "Current CIE average only; add past semester SGPA for a combined trend."
        drivers = [
            ("Current CIE average", f"{cie_average:.1f}/100", "Average of CIE-1 and CIE-2."),
            ("Past semester SGPA", "Not added", "Historical SGPA is not available yet.")
        ]
    else:
        academic_index = 0.5 * cie_average + 0.5 * (sgpa_average * 10)
        basis = "50% current CIE average + 50% average historical SGPA converted to a 100-point scale."
        drivers = [
            ("Current CIE average", f"{cie_average:.1f}/100", "Average of CIE-1 and CIE-2."),
            ("Historical SGPA average", f"{sgpa_average:.2f}/10", f"Based on {len(records)} recorded semester(s).")
        ]
    risk_score = max(0, min(100, round(100 - academic_index)))
    risk = "High" if risk_score >= 60 else "Moderate" if risk_score >= 35 else "Low"
    explanation = f"{basis} Combined academic index: {academic_index:.1f}/100."
    return {"risk": risk, "score": risk_score, "academic_index": round(academic_index,1),
            "cie_average": round(cie_average,1), "sgpa_average": round(sgpa_average,2) if sgpa_average is not None else None,
            "drivers": drivers, "explanation": explanation}
