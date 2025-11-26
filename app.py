import math
from flask import Flask, request, jsonify
from flask_cors import CORS 

# --- V3.1 PROSCREENING LOGIC: START ---

class SolutionSuggestion:
    """Class for storing structured solution suggestions."""
    def __init__(self, flag_type: str, description: str, target_value: float = None):
        self.flag_type = flag_type
        self.description = description
        self.target_value = target_value

    def __str__(self):
        """Format as requested: [Flag Type] Description (Mål: X kr)"""
        target_str = f" (Mål: {self.target_value:,.0f} kr)" if self.target_value is not None else ""
        return f"[{self.flag_type}] {self.description}{target_str}".replace(',', ' ') 

# --- KONFIGURASJON / BANK POLICY SIMULERING (Basert på norske retningslinjer) ---
RENTE_OEKNING_STRESS_TEST = 0.03 # 3% renteøkning på total gjeld (for 5% margin)
MAX_GJELD_RATIO = 5.0
MAX_LTV = 0.85 # Standard boliglånsforskrift
SPESIALIST_LTV = 0.90 # Spesialistbanker kan akseptere høyere
MIN_LIVSOPPHOLD_MARGIN = 4000 * 12 # Minimum margin etter SIFO og stress test
SIFO_AARLIG = {1: 150000, 2: 250000, 3: 320000, 4: 380000, 5: 430000} # SIFO-kostnader simulert
FORBRUKSLÅN_CAP = 400000

# Bank Policy Settings (Simulated basert på ordinære og spesialistbanker)
BANK_POLICIES = {
    # Ordinære Bank (Strengere, lav risiko)
    "Sparebank1 (Ordinær Bank)": {"gjeld_max": 4.5, "ltv_max": 0.80, "sysselsetting_krav": ["Fast"], "forbrukslan_toleranse": 50000, "base_chance": 50},
    "Nordea (Ordinær Bank)": {"gjeld_max": 4.8, "ltv_max": 0.85, "sysselsetting_krav": ["Fast"], "forbrukslan_toleranse": 100000, "base_chance": 55},
    # Digital Bank / Enklere Kriterier
    "Sbanken (Digital Bank)": {"gjeld_max": 5.0, "ltv_max": 0.85, "sysselsetting_krav": ["Fast", "Pensjon", "Uføretrygd"], "forbrukslan_toleranse": 150000, "base_chance": 65},
    # Spesialist Bank (Høyere risiko, men godtar mer)
    "Bluestep (Spesialist Bank)": {"gjeld_max": 5.5, "ltv_max": 0.90, "sysselsetting_krav": ["Fast", "Selvstendig", "Midlertidig"], "forbrukslan_toleranse": 400000, "base_chance": 75}
}

class ProScreeningTool:
    def __init__(self, case_data: dict):
        self.data = case_data
        self.flags = []
        self.suggestions = []
        
        # Samlet data
        self.total_inntekt = sum(s['inntekt'] for s in self.data.get('sokere', []))
        self.total_gjeld_uten_laan = (
            self.data.get("studielån", 0) + 
            self.data.get("forbrukslån", 0) + 
            self.data.get("kredittkort_ramme", 0) + 
            self.data.get("bil_laan", 0)
        )
        self.total_gjeld_med_laan = self.total_gjeld_uten_laan + self.data.get("laan_oensket", 0)

    def check_gjeld_ratio(self):
        """Sjekker total gjeldsgrad mot 5.0x inntekt (MAKS grense)."""
        if self.total_inntekt == 0:
            self.flags.append("Feil: Total inntekt er null, kan ikke beregne gjeldsgrad.")
            return

        ratio = self.total_gjeld_med_laan / self.total_inntekt
        if ratio > MAX_GJELD_RATIO:
            self.flags.append(f"Alvorlig: For høy gjeldsgrad ({ratio:,.2f}x) – over {MAX_GJELD_RATIO}x inntekt.")
            max_gjeld = MAX_GJELD_RATIO * self.total_inntekt
            reduction_needed = self.total_gjeld_med_laan - max_gjeld
            
            self.suggestions.append(SolutionSuggestion(
                flag_type="Gjeldsgrad",
                description=f"Reduser total gjeld (inkl. nytt lån) med {reduction_needed:,.0f} kr, eller øk inntekten.",
                target_value=max_gjeld
            ))
    
    def check_ltv(self):
        """Sjekker LTV mot 85% grensen."""
        value = self.data.get("bolig_verdi", 0)
        loan = self.data.get("laan_oensket", 0)
        equity = self.data.get("egenkapital", 0)
        
        # Sjekk om egenkapital + lån overstiger verdien
        if (loan + self.total_gjeld_uten_laan) > value * 1.5: 
             # Sjekk LTV på nytt lån mot boligverdi
             if value > 0:
                ltv = loan / value
                if ltv > MAX_LTV:
                    ltv_pct = ltv * 100
                    self.flags.append(f"Alvorlig: LTV over {MAX_LTV*100:.0f}% ({ltv_pct:.2f}%) – krever ekstra egenkapital eller spesialistbank.")
                    
                    max_loan_allowed = MAX_LTV * value
                    equity_needed = loan - max_loan_allowed
                    
                    self.suggestions.append(SolutionSuggestion(
                        flag_type="LTV",
                        description=f"Kunden mangler {equity_needed:,.0f} kr i egenkapital for ordinær bankfinansiering (85% krav).",
                        target_value=max_loan_allowed
                    ))

    def check_betjeningsevne(self):
        """Simulert stresstest mot SIFO-satsene."""
        husholdning = self.data.get("barn_under_18", 0) + len(self.data.get('sokere', [])) # Personer i husholdning
        husholdning = min(husholdning, 5) # Maks 5 for SIFO simulering
        
        if husholdning not in SIFO_AARLIG:
            # Fallback for større husholdninger
            standard_sifo_cost = SIFO_AARLIG[5] + ((husholdning - 5) * 50000) 
        else:
            standard_sifo_cost = SIFO_AARLIG[husholdning] 
        
        # Beregn stressrenteøkning på all gjeld inkludert nytt lån
        stressed_annual_interest_increase = self.total_gjeld_med_laan * RENTE_OEKNING_STRESS_TEST
        
        # Forenklet betjeningsevne: Inntekt - SIFO - Stressrente > Minimum Margin
        total_annual_expenses_stressed = standard_sifo_cost + stressed_annual_interest_increase
        solvency_margin = self.total_inntekt - total_annual_expenses_stressed
        
        if solvency_margin < MIN_LIVSOPPHOLD_MARGIN:
            self.flags.append(f"Betjeningsevne: Lav margin ({solvency_margin:,.0f} kr/år) etter stresstest. Under min. krav.")
            shortfall = MIN_LIVSOPPHOLD_MARGIN - solvency_margin
            self.suggestions.append(SolutionSuggestion(
                flag_type="Betjeningsevne",
                description=f"Må øke årlig margin med {shortfall:,.0f} kr (før skatt). Reduser gjeld eller øk inntekt.",
                target_value=MIN_LIVSOPPHOLD_MARGIN
            ))

    def check_usikker_gjeld_og_kilder(self):
        """Sjekker forbrukslån, kredittkortramme og egenkapital kilde."""
        forbrukslån = self.data.get("forbrukslån", 0)
        kredittkort_ramme = self.data.get("kredittkort_ramme", 0)
        
        if kredittkort_ramme > 100000:
            self.flags.append(f"Gjeld: Høy ubrukt kredittramme ({kredittkort_ramme:,.0f} kr) reduserer lånekapasitet.")
            
        if forbrukslån > FORBRUKSLÅN_CAP:
             self.flags.append(f"Gjeld: Ekstremt høyt forbrukslån ({forbrukslån:,.0f} kr). Krever refinansiering.")
        
        kilde = self.data.get("egenkapital_kilde", "").lower()
        if "lån" in kilde or "foreldre" in kilde:
            self.flags.append(f"Egenkapital: Kilde ('{kilde}') kan kreve dokumentasjon og påvirker bankens risikovurdering.")
            self.suggestions.append(SolutionSuggestion(flag_type="Egenkapital", description="Dokumenter kilden til egenkapital tydelig."))


    def bank_comparison(self):
        """Sammenligner kundens profil med simulerte bankkrav."""
        chances = []
        
        for bank_navn, policy in BANK_POLICIES.items():
            current_chance = policy['base_chance']
            
            # Gjeldsgrad sjekk
            ratio = self.total_gjeld_med_laan / self.total_inntekt if self.total_inntekt > 0 else 99
            if ratio > policy['gjeld_max']:
                current_chance -= 30 # Stort avvik
            elif ratio > MAX_GJELD_RATIO:
                current_chance -= 15 # Mindre avvik

            # LTV sjekk
            value = self.data.get("bolig_verdi", 1)
            ltv = self.data.get("laan_oensket", 0) / value
            if ltv > policy['ltv_max']:
                current_chance -= 20 # Ikke innenfor grensen
            
            # Sysselsetting sjekk (Hovedsøker)
            hoved_sysselsetting = self.data['sokere'][0]['sysselsetting']
            if hoved_sysselsetting not in policy['sysselsetting_krav']:
                current_chance -= 25
                
            # Forbrukslån sjekk
            if self.data.get("forbrukslån", 0) > policy['forbrukslan_toleranse']:
                current_chance -= 15
                
            # Tidligere søkt
            for bank_sokt in self.data.get("bank_sokt", []):
                if bank_sokt.upper() in bank_navn.upper():
                    current_chance -= 10 # Tidligere søknad (antatt avslag)

            
            chances.append({"navn": bank_navn, "chance": max(0, min(100, current_chance))})

        return chances

    def evaluate(self):
        self.flags = []
        self.suggestions = []
        
        # Kjør alle sjekker
        self.check_gjeld_ratio()
        self.check_ltv()
        self.check_betjeningsevne()
        self.check_usikker_gjeld_og_kilder()
        
        # Bankmatch
        bank_results = self.bank_comparison()

        return {
            "risk_flags": self.flags,
            "løsningsforslag": [str(s) for s in self.suggestions],
            "bank_chances": bank_results
        }

# --- V3.1 PROSCREENING LOGIC: END ---


# --- FLASK API SETUP ---
app = Flask(__name__)
# Aktiver CORS for å tillate Netlify (alle domener for enkelhet) å koble til
CORS(app) 

@app.route('/api/evaluate_case', methods=['POST'])
def evaluate_case():
    """Handle POST request for case evaluation."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "No input data provided"}), 400

        # Run the core logic
        evaluator = ProScreeningTool(data)
        results = evaluator.evaluate()
        
        return jsonify({
            "success": True,
            "case_ID": data.get("kunde_ID", "N/A"),
            "risk_flags": results["risk_flags"],
            "løsningsforslag": results["løsningsforslag"],
            "bank_chances": results["bank_chances"] # Nytt felt for bankresultater
        })

    except Exception as e:
        # Hvis noe feiler i Python-koden, send feilmelding til frontend
        return jsonify({"success": False, "message": f"Serverfeil i analyse: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
