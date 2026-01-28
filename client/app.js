const API_URL = 'http://localhost:8000';

function getHeaders() {
    const apiKey = document.getElementById('apiKey').value;
    return {
        'Accept': 'application/json',
        'X-API-Key': apiKey
    };
}

function renderTable(data, containerId) {
    const container = document.getElementById(containerId);
    if (!data) {
        container.innerHTML = '<div class="alert alert-warning">No data found</div>';
        return;
    }

    // Unpack data if wrapped in a known property or generic 'data'
    if (!Array.isArray(data)) {
        if (data.data && Array.isArray(data.data)) {
            data = data.data;
        } else if (data.cities && Array.isArray(data.cities)) {
            data = data.cities.map(c => ({ city: c }));
        } else if (data.hemispheres && Array.isArray(data.hemispheres)) {
            data = data.hemispheres;
        } else if (data.years && Array.isArray(data.years)) {
            data = data.years.map(y => ({ year: y }));
        } else if (data.countries && Array.isArray(data.countries)) {
            data = data.countries.map(c => ({ country: c }));
        } else {
            // Check if there is ANY array property that looks like the main data
            const arrayKey = Object.keys(data).find(key => Array.isArray(data[key]) && data[key].length > 0);
            if (arrayKey) {
                data = data[arrayKey];
            } else {
                // Formatting for single Stats object
                let html = '<ul class="list-group">';
                for (const [key, value] of Object.entries(data)) {
                    html += `<li class="list-group-item d-flex justify-content-between align-items-center">
                    ${key}
                    <span class="badge bg-primary rounded-pill">${value}</span>
                    </li>`;
                }
                html += '</ul>';
                container.innerHTML = html;
                return;
            }
        }
    }

    if (!Array.isArray(data) || data.length === 0) {
        container.innerHTML = '<div class="alert alert-warning">No data found</div>';
        return;
    }

    const headers = Object.keys(data[0]);
    
    let html = '<table class="table table-striped table-hover"><thead><tr>';
    headers.forEach(h => html += `<th>${h}</th>`);
    html += '</tr></thead><tbody>';
    
    data.forEach(row => {
        html += '<tr>';
        headers.forEach(h => html += `<td>${row[h]}</td>`);
        html += '</tr>';
    });
    
    html += '</tbody></table>';
    container.innerHTML = html;
}

async function fetchData() {
    const city = document.getElementById('cityInput').value;
    let url = `${API_URL}/data?limit=100`;
    if (city) {
        url += `&city=${encodeURIComponent(city)}`;
    }
    
    try {
        const response = await fetch(url, { headers: getHeaders() });
        if (!response.ok) throw new Error(await response.text());
        const data = await response.json();
        renderTable(data, 'dataResults');
    } catch (err) {
        document.getElementById('dataResults').innerHTML = `<div class="alert alert-danger">${err.message}</div>`;
    }
}

async function fetchDataByCountry() {
    const country = document.getElementById('countryInput').value;
    if (!country) return;
    
    let url = `${API_URL}/data/country/${encodeURIComponent(country)}?limit=100`;
    
    try {
        const response = await fetch(url, { headers: getHeaders() });
        if (!response.ok) throw new Error(await response.text());
        const data = await response.json();
        renderTable(data, 'countryResults');
    } catch (err) {
        document.getElementById('countryResults').innerHTML = `<div class="alert alert-danger">${err.message}</div>`;
    }
}

async function fetchDataByYear() {
    const year = document.getElementById('yearInput').value;
    if (!year) return;
    
    let url = `${API_URL}/data/year/${encodeURIComponent(year)}?limit=100`;
    
    try {
        const response = await fetch(url, { headers: getHeaders() });
        if (!response.ok) throw new Error(await response.text());
        const data = await response.json();
        renderTable(data, 'yearResults');
    } catch (err) {
        document.getElementById('yearResults').innerHTML = `<div class="alert alert-danger">${err.message}</div>`;
    }
}
