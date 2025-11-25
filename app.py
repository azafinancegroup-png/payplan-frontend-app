import math
from flask import Flask, request, jsonify

# --- V3.0 CORE LOGIC: START ---
class SolutionSuggestion:
    def __init__(self, flag_type: str, description: str, target_value: float = None):
        self.flag_type = flag_type
        self.description = description
        self.target_value = target_value

    def __str__(self):
        target_str = f" (Mål: {self.target_value:,.0f} kr)" if self.target_value is not None else ""
        return f"[{self.flag_type}] {self.description}{target_str}".replace(',', ' ') 

# --- KONFIGURASJON ---
RENTE_OEKNING_STRESS_TEST = 0.03 
MIN_LIVSOPPHOLD_MARGIN = 4000 * 12 
MAX_GJELD_RATIO = 5.0
MAX_LTV = 0.85
SIFO_AARLIG = {
    1: 150000, 
    2: 250000, 
    3: 320000, 
    4: 380000, 
}

class CaseEvaluatorV3:
    def __init__(self, case_data: dict):
        self.data = case_data
        self.flags = []
        self.suggestions = []

    def check_gjeld_ratio(self):
        gjeld = self.data.get("total_gjeld", 0)
        inntekt = self.data.get("inntekt", 1)
        ratio = gjeld / inntekt

        if ratio > MAX_GJELD_RATIO:
            self.flags.append(f"For høy gjeldsgrad ({ratio:,.2f}x) – over {MAX_GJELD_RATIO}x inntekt")
            max_gjeld = MAX_GJELD_RATIO * inntekt
            reduction_needed = gjeld - max_gjeld
            
            self.suggestions.append(SolutionSuggestion(
                flag_type="Gjeldsgrad",
                description=f"Reduser total gjeld med {reduction_needed:,.0f} kr.",
                target_value=max_gjeld
            ))

    def check_ltv(self):
        value = self.data.get("bolig_verdi", 0)
        loan = self.data.get("laan_oensket", 0)

        if value > 0 and (loan / value) > MAX_LTV:
            ltv = loan / value
            self.flags.append(f"LTV over {MAX_LTV*100:.0f}% ({ltv*100:.2f}%) – krever egenkapital")
            max_loan_allowed = MAX_LTV * value
            equity_needed = loan - max_loan_allowed
            
            self.suggestions.append(SolutionSuggestion(
                flag_type="LTV",
                description=f"Kunden må stille med ekstra egenkapital på {equity_needed:,.0f} kr.",
                target_value=max_loan_allowed
            ))

    def check_betjeningsevne_dynamisk(self):
        inntekt = self.data.get("inntekt", 0)
        utgifter = self.data.get("utgifter", 0)
        gjeld_total = self.data.get("total_gjeld", 0) + self.data.get("laan_oensket", 0)
        husholdning = self.data.get("husholdning_størrelse", 1)

        try:
            standard_sifo_cost = SIFO_AARLIG[husholdning]
        except KeyError:
            self.flags.append("Feil: Husholdningsstørrelse er ugyldig for SIFO-sjekk.")
            return

        stressed_annual_interest_increase = gjeld_total * RENTE_OEKNING_STRESS_TEST
        total_annual_expenses_stressed = utgifter + standard_sifo_cost + stressed_annual_interest_increase
        solvency_margin = inntekt - total_annual_expenses_stressed

        if solvency_margin < MIN_LIVSOPPHOLD_MARGIN:
            self.flags.append(f"Lav Betjeningsevne etter stresstest. Margin: {solvency_margin:,.0f} kr/år.")
            shortfall = MIN_LIVSOPPHOLD_MARGIN - solvency_margin
            self.suggestions.append(SolutionSuggestion(
                flag_type="Betjeningsevne",
                description=f"Må øke årlig margin med {shortfall:,.0f} kr (før skatt) for å klare stresstesten.",
                target_value=MIN_LIVSOPPHOLD_MARGIN
            ))
            
    # Naering/Mellomfinansiering checks are omitted for brevity but should be added here later

    def evaluate(self):
        self.flags = []
        self.suggestions = []
        self.check_gjeld_ratio()
        self.check_ltv()
        self.check_betjeningsevne_dynamisk() 
        return {
            "risk_flags": self.flags,
            "løsningsforslag": [str(s) for s in self.suggestions]
        }

# --- V3.0 CORE LOGIC: END ---


# --- FLASK API SETUP ---
app = Flask(__name__)

# NOTE: CORS is needed in production to allow Netlify to connect to the API. 
# We assume deployment platform handles it or we can add flask-cors later.

@app.route('/api/evaluate_case', methods=['POST'])
def evaluate_case():
    """Handle POST request for case evaluation."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "No input data provided"}), 400

        # Run the core logic
        evaluator = CaseEvaluatorV3(data)
        results = evaluator.evaluate()
        
        return jsonify({
            "success": True,
            "case_ID": data.get("kunde_ID", "N/A"),
            "risk_flags": results["risk_flags"],
            "løsningsforslag": results["løsningsforslag"]
        })

    except Exception as e:
        return jsonify({"success": False, "message": f"Internal Server Error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
