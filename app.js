// --- app.js ---
document.getElementById('evaluation-form').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const form = e.target;
    // Collect data from the form
    const data = {
        kunde_ID: form.kunde_ID.value,
        laanetype_ønsket: form.laanetype_ønsket.value,
        inntekt: parseFloat(form.inntekt.value),
        total_gjeld: parseFloat(form.total_gjeld.value),
        laan_oensket: parseFloat(form.laan_oensket.value),
        bolig_verdi: parseFloat(form.bolig_verdi.value),
        husholdning_størrelse: parseInt(form.husholdning_størrelse.value),
        
        // Hidden/Default values 
        utgifter: parseFloat(form.utgifter.value), 
        inntekt_mnd: parseInt(form.inntekt_mnd.value),
        anmerkning: form.anmerkning.value === 'True',
    };

    // NOTE: Jab aapka Backend deploy ho jaye, toh yeh URL badalna hoga!
    const API_ENDPOINT = 'http://localhost:5000/api/evaluate_case'; 

    const resultsDiv = document.getElementById('results');
    const flagsDiv = document.getElementById('risk-flags');
    const suggestionsList = document.getElementById('suggestions-list');
    
    flagsDiv.innerHTML = '<p>Analyserer data... (Simulert Sjekk)</p>';
    suggestionsList.innerHTML = '';
    resultsDiv.style.display = 'block';

    try {
        // --- SIMULATED RESPONSE for Netlify Deployment ---
        // Hum abhi nakli nateeja dikha rahe hain taake aapka Netlify form kaam karta hua dikhe.
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
        flagsDiv.innerHTML = `<p class="error">Nettverksfeil: Kunne ikke koble til API. Abhi aapka backend deploy nahi hua hai.</p>`;
    }
});