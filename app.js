// Event listener for å vise/skjule medsøkerfelt
document.getElementById('medsoker_ja_nei').addEventListener('change', function() {
    const medsokerFields = document.getElementById('medsoker-fields');
    if (this.value === 'Ja') {
        medsokerFields.style.display = 'block';
        // Sett required for medsøker inntekt
        document.getElementById('inntekt_medsoker').required = true;
    } else {
        medsokerFields.style.display = 'none';
        document.getElementById('inntekt_medsoker').required = false;
        document.getElementById('inntekt_medsoker').value = '0'; // Nullstill ved skjuling
    }
});

// Hoved logikk for skjema innsending
document.getElementById('evaluation-form').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const form = e.target;
    const isMedsoker = form.medsoker_ja_nei.value === 'Ja';

    // Vis spinner, skjul innhold
    const resultsDiv = document.getElementById('results');
    const loadingSpinner = document.getElementById('loading-spinner');
    const analysisContent = document.getElementById('analysis-content');

    resultsDiv.style.display = 'block';
    analysisContent.style.display = 'none';
    loadingSpinner.style.display = 'block';

    // Samle data for API-kall (Inkluderer alle nye felt)
    const data = {
        kunde_ID: form.kunde_ID.value,
        laanetype_ønsket: form.laanetype_ønsket.value,
        laan_oensket: parseFloat(form.laan_oensket.value),
        bolig_verdi: parseFloat(form.bolig_verdi.value),
        egenkapital: parseFloat(form.egenkapital.value),
        egenkapital_kilde: form.egenkapital_kilde.value,
        
        // Gjeldsoversikt
        studielån: parseFloat(form.studielån.value),
        forbrukslån: parseFloat(form.forbrukslån.value),
        kredittkort_ramme: parseFloat(form.kredittkort_ramme.value), // Ramme regnes som gjeld i analyse
        bil_laan: parseFloat(form.bil_laan.value),
        bank_sokt: form.bank_sokt.value.split(',').map(b => b.trim().toUpperCase()).filter(b => b.length > 0),

        // Søker Data (Hoved og Medsøker)
        sokere: [
            {
                rolle: 'Hovedsøker',
                inntekt: parseFloat(form.inntekt_hoved.value),
                sysselsetting: form.sysselsetting_hoved.value,
            }
        ],
        barn_under_18: parseInt(form.barn_under_18.value),
    };

    if (isMedsoker) {
        data.sokere.push({
            rolle: 'Medsøker',
            inntekt: parseFloat(form.inntekt_medsoker.value),
            sysselsetting: form.sysselsetting_medsoker.value,
        });
    }

    // --- VIKTIG: API ENDPOINT TIL RENDER BACKEND (Dette må peke til din Render-tjeneste) ---
    const API_ENDPOINT = 'https://payplan-frontend-app.onrender.com/api/evaluate_case'; 

    const flagsDiv = document.getElementById('risk-flags');
    const suggestionsList = document.getElementById('suggestions-list');
    const bankChancesDiv = document.getElementById('bank-chances');

    try {
        // Live API kall til Render-backend
        const response = await fetch(API_ENDPOINT, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });

        const result = await response.json(); 
        
        // Skjul spinner og vis innhold
        loadingSpinner.style.display = 'none';
        analysisContent.style.display = 'block';
        
        if (result.success) {
            
            // 1. Risiko Flagg
            flagsDiv.innerHTML = result.risk_flags.length > 0 
                ? result.risk_flags.map(flag => `<p>${flag}</p>`).join('')
                : '<p style="color: green;">Ingen alvorlige risikoflagg funnet.</p>';

            // 2. Løsningsforslag
            suggestionsList.innerHTML = result.løsningsforslag.length > 0
                ? result.løsningsforslag.map(suggestion => `<li>${suggestion}</li>`).join('')
                : '<li>Ingen umiddelbare forbedringsforslag nødvendig.</li>';

            // 3. Bank Match
            bankChancesDiv.innerHTML = `<div class="bank-match-container">
                ${result.bank_chances.map(bank => `
                    <div class="bank-card ${bank.chance > 60 ? 'high-chance' : ''}">
                        <h4>${bank.navn}</h4>
                        <p>${bank.chance}%</p>
                    </div>
                `).join('')}
            </div>`;

        } else {
            // Håndter feil fra API-serveren
            flagsDiv.innerHTML = `<p class="error">Analyse Feil: ${result.message || 'Ukjent feil i API-tilkobling.'}</p>`;
            suggestionsList.innerHTML = '<li>Klarte ikke fullføre analysen. Sjekk input og serverstatus.</li>';
            bankChancesDiv.innerHTML = '';
        }

    } catch (error) {
        // Håndter nettverksfeil
        loadingSpinner.style.display = 'none';
        analysisContent.style.display = 'block';
        flagsDiv.innerHTML = `<p class="error">Nettverksfeil: Klarte ikke koble til Render API. (${error.message})</p>`;
        suggestionsList.innerHTML = '<li>Vennligst bekreft at Render-serveren er aktiv og at API-URL-en er riktig i app.js.</li>';
        bankChancesDiv.innerHTML = '';
    }
});
