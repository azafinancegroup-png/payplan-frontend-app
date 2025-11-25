// --- app.js ---
document.getElementById('evaluation-form').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const form = e.target;
    // Hent data fra skjemaet (Collect data from the form)
    const data = {
        kunde_ID: form.kunde_ID.value,
        laanetype_ønsket: form.laanetype_ønsket.value,
        inntekt: parseFloat(form.inntekt.value),
        total_gjeld: parseFloat(form.total_gjeld.value),
        laan_oensket: parseFloat(form.laan_oensket.value),
        bolig_verdi: parseFloat(form.bolig_verdi.value),
        husholdning_størrelse: parseInt(form.husholdning_størrelse.value),
        
        // Skjulte/Standardverdier for V3.0 analyse (Hidden/Default values for V3.0 analysis)
        utgifter: parseFloat(form.utgifter.value), 
        inntekt_mnd: parseInt(form.inntekt_mnd.value),
        anmerkning: form.anmerkning.value === 'True',
    };

    // MERK: Når backend er deployert, må denne URL-en endres!
    const API_ENDPOINT = 'https://payplan-frontend-app.onrender.com/api/evaluate_case';    
    const resultsDiv = document.getElementById('results');
    const flagsDiv = document.getElementById('risk-flags');
    const suggestionsList = document.getElementById('suggestions-list');
    
    flagsDiv.innerHTML = '<p>Analyserer data... (Simulert Sjekk)</p>';
    suggestionsList.innerHTML = '';
    resultsDiv.style.display = 'block';

    try {
        // --- SIMULERT RESPONDS FOR NETLIFY DEPLOYERING ---
        // (Vi viser et falskt resultat nå for å bekrefte at frontend fungerer)
        const simulatedResponse = {
            success: true,
            risk_flags: [
                "For høy gjeldsgrad (5.83x) – over 5.0x inntekt",
                "LTV over 85% (87.50%) – krever egenkapital"
            ],
            løsningsforslag: [
                "[Gjeldsgrad] Reduser total gjeld med 500,000 kr. (Mål: 3,000,000 kr)",
                "[LTV] Kunden må stille med ekstra egenkapital på 500,000 kr. (Mål: 3,400,000 kr)"
            ]
        };
        
        const result = simulatedResponse; 

        if (result.success) {
            flagsDiv.innerHTML = '<h3>Risiko Flagg funnet:</h3>';
            result.risk_flags.forEach(flag => {
                flagsDiv.innerHTML += `<p class="error">${flag}</p>`;
            });

            suggestionsList.innerHTML = '';
            result.løsningsforslag.forEach(suggestion => {
                suggestionsList.innerHTML += `<li>${suggestion}</li>`;
            });
        } else {
            flagsDiv.innerHTML = `<p class="error">Analyse Feil: ${result.message || 'Ukjent feil'}</p>`;
        }

    } catch (error) {
        flagsDiv.innerHTML = `<p class="error">Nettverksfeil: Klarte ikke koble til API. Backend er ikke deployert enda.</p>`;
    }
});
