/**
 * PowerBill - Logic and State Management
 */

// --- Constants & Data --- //
const STATES = {
    "Maharashtra (MSEB)":  {"slabs": [[0,100,3.25],[100,300,7.50],[300,500,9.95],[500,99999,12.00]], "fixed": 40},
    "Delhi (BSES/TPDDL)":  {"slabs": [[0,200,3.00],[200,400,6.50],[400,800,8.00],[800,99999,9.00]],  "fixed": 20},
    "Gujarat (DGVCL)":     {"slabs": [[0,50,2.75],[50,200,4.85],[200,400,7.10],[400,99999,8.50]],    "fixed": 35},
    "Rajasthan (JVVNL)":   {"slabs": [[0,100,3.85],[100,200,6.25],[200,300,8.00],[300,99999,9.50]],  "fixed": 50},
    "UP (DVVNL)":          {"slabs": [[0,100,3.50],[100,150,5.50],[150,300,6.00],[300,99999,7.00]],  "fixed":  0},
    "Karnataka (BESCOM)":  {"slabs": [[0,30,3.15],[30,100,5.45],[100,200,7.20],[200,99999,8.80]],    "fixed": 25},
    "Custom":              {"slabs": [], "fixed": 0},
};

const MONTHS = ["January","February","March","April","May","June","July","August","September","October","November","December"];

// --- State Variables --- //
let currentBillResult = null;
let historyData = [];
const API_BASE = window.location.protocol === 'file:' ? 'http://localhost:3000/api' : '/api';

// --- DOM Elements --- //
const stateSelect = document.getElementById('state');
const monthSelect = document.getElementById('month');
const yearSelect = document.getElementById('year');
const customFields = document.getElementById('custom-fields');
const form = document.getElementById('calculator-form');
const totalDisplay = document.getElementById('display-total');
const metaDisplay = document.getElementById('display-meta');
const resultSummary = document.getElementById('result-summary');
const breakdownPills = document.getElementById('breakdown-pills');
const pillEnergy = document.getElementById('pill-energy');
const pillFixed = document.getElementById('pill-fixed');
const pillTax = document.getElementById('pill-tax');
const slabContainer = document.getElementById('slab-container');
const slabBody = document.getElementById('slab-body');
const tipsContainer = document.getElementById('tips-container');
const tipsList = document.getElementById('tips-list');
const saveBtn = document.getElementById('save-btn');
const toast = document.getElementById('toast');

// Navigation
const navCalc = document.getElementById('nav-calculator');
const navHist = document.getElementById('nav-history');
const tabCalc = document.getElementById('tab-calculator');
const tabHist = document.getElementById('tab-history');

// History Elements
const statRecords = document.getElementById('stat-records');
const statAvg = document.getElementById('stat-avg');
const statMax = document.getElementById('stat-max');
const historyTable = document.getElementById('history-table');
const historyBody = document.getElementById('history-body');
const emptyHistoryMsg = document.getElementById('empty-history-msg');
const clearHistoryBtn = document.getElementById('clear-history-btn');

// --- Initialization --- //
function init() {

    // Populate Selects
    Object.keys(STATES).forEach(s => {
        let opt = document.createElement('option');
        opt.value = s;
        opt.textContent = s;
        stateSelect.appendChild(opt);
    });

    const currDate = new Date();
    MONTHS.forEach((m, i) => {
        let opt = document.createElement('option');
        opt.value = m;
        opt.textContent = m;
        if(i === currDate.getMonth()) opt.selected = true;
        monthSelect.appendChild(opt);
    });

    const currYear = currDate.getFullYear();
    for(let y = 2020; y <= 2030; y++) {
        let opt = document.createElement('option');
        opt.value = y;
        opt.textContent = y;
        if(y === currYear) opt.selected = true;
        yearSelect.appendChild(opt);
    }

    // Event Listeners
    stateSelect.addEventListener('change', (e) => {
        if(e.target.value === 'Custom') {
            customFields.classList.remove('hidden');
        } else {
            customFields.classList.add('hidden');
        }
    });

    form.addEventListener('submit', handleCalculate);
    saveBtn.addEventListener('click', saveCurrentBill);
    
    navCalc.addEventListener('click', () => switchTab('calc'));
    navHist.addEventListener('click', () => switchTab('hist'));
    clearHistoryBtn.addEventListener('click', clearHistory);
}

// --- Navigation --- //
function switchTab(tab) {
    if(tab === 'calc') {
        navCalc.classList.add('active');
        navHist.classList.remove('active');
        tabCalc.classList.add('active');
        tabHist.classList.remove('active');
    } else {
        navHist.classList.add('active');
        navCalc.classList.remove('active');
        tabHist.classList.add('active');
        tabCalc.classList.remove('active');
        renderHistory();
    }
}

// --- Logic Calculation --- //
function computeBill(units, stateName, customRate=0, customFixed=0) {
    let slabsInfo = [];
    let energy = 0;
    let fixed = 0;

    if (stateName === "Custom") {
        energy = units * customRate;
        fixed = customFixed;
        slabsInfo.push({ label: "All units", units: units, rate: customRate, charge: energy });
    } else {
        const info = STATES[stateName];
        const slabs = info.slabs;
        fixed = info.fixed;
        let remaining = units;
        
        for (let i=0; i<slabs.length; i++) {
            if (remaining <= 0) break;
            const low = slabs[i][0];
            const high = slabs[i][1];
            const rate = slabs[i][2];
            
            const used = Math.min(remaining, high - low);
            const charge = used * rate;
            energy += charge;
            
            if (used > 0) {
                slabsInfo.push({ label: `${low}–${high} units`, units: used, rate: rate, charge: charge });
            }
            remaining -= used;
        }
    }

    const tax = energy * 0.08;
    const surcharge = energy * 0.05;
    const total = energy + fixed + tax + surcharge;

    return { slabs: slabsInfo, energy, fixed, tax, surcharge, total, units };
}

function handleCalculate(e) {
    e.preventDefault();
    const units = parseFloat(document.getElementById('units').value);
    const stateName = stateSelect.value;
    
    let customRate = parseFloat(document.getElementById('custom-rate').value) || 0;
    let customFixed = parseFloat(document.getElementById('custom-fixed').value) || 0;

    if(units < 0) return alert("Please enter valid positive units!");

    // Animate recalculation
    resultSummary.style.transform = 'scale(0.98)';
    setTimeout(() => resultSummary.style.transform = 'scale(1)', 150);

    const result = computeBill(units, stateName, customRate, customFixed);
    currentBillResult = {
        ...result,
        state: stateName,
        month: monthSelect.value,
        year: yearSelect.value
    };

    renderResult(currentBillResult);
}

function renderResult(r) {
    // Total display
    animateValue(totalDisplay, parseFloat(totalDisplay.innerText) || 0, r.total, 800);
    metaDisplay.innerHTML = `<strong>${r.month} ${r.year}</strong> | ${r.state}`;
    
    // Pills
    breakdownPills.classList.remove('hidden');
    pillEnergy.innerText = `₹${r.energy.toFixed(2)}`;
    pillFixed.innerText = `₹${r.fixed.toFixed(2)}`;
    pillTax.innerText = `₹${(r.tax + r.surcharge).toFixed(2)}`;

    // Slab Table
    slabContainer.classList.remove('hidden');
    slabBody.innerHTML = '';
    r.slabs.forEach(s => {
        let tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${s.label}</td>
            <td>${s.units.toFixed(1)}</td>
            <td>₹${s.rate.toFixed(2)}</td>
            <td>₹${s.charge.toFixed(2)}</td>
        `;
        slabBody.appendChild(tr);
    });

    // Tips Table
    tipsContainer.classList.remove('hidden');
    tipsList.innerHTML = '';
    const tips = [];
    if (r.units > 300) tips.push({text: "Unusually high usage! Check heavy appliances like ACs/Geysers.", icon: "alert-circle-outline"});
    if (r.units > 200) tips.push({text: "Switching to LED bulbs can save up to 80% on lighting.", icon: "bulb-outline"});
    if (r.units > 100) tips.push({text: "Unplug devices on standby mode to reduce phantom power.", icon: "power-outline"});
    tips.push({text: "Consider solar energy subsidies available in your state.", icon: "sunny-outline"});

    tips.forEach(t => {
        let li = document.createElement('li');
        li.innerHTML = `<ion-icon name="${t.icon}"></ion-icon> <span>${t.text}</span>`;
        tipsList.appendChild(li);
    });
}

function animateValue(obj, start, end, duration) {
    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        // ease out cubic
        const p = 1 - Math.pow(1 - progress, 3);
        obj.innerText = (start + (end - start) * p).toFixed(2);
        if (progress < 1) {
            window.requestAnimationFrame(step);
        }
    };
    window.requestAnimationFrame(step);
}

function showToast(msg) {
    document.getElementById('toast-message').innerText = msg;
    toast.classList.add('show');
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

// --- History Logic --- //
async function saveCurrentBill() {
    if(!currentBillResult) return;
    
    try {
        const response = await fetch(`${API_BASE}/bills`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(currentBillResult)
        });
        if (response.ok) {
            showToast(`Bill for ${currentBillResult.month} saved successfully!`);
        } else {
            const data = await response.json();
            showToast(`Error saving bill: ${data.error}`);
        }
    } catch (e) {
        showToast(`Network Error: ${e.message}`);
    }
}

async function renderHistory() {
    try {
        const response = await fetch(`${API_BASE}/bills`);
        const result = await response.json();
        historyData = result.data || [];
    } catch (e) {
        console.error("Fetch error:", e);
        historyData = [];
    }

    if(historyData.length === 0) {
        emptyHistoryMsg.classList.remove('hidden');
        historyTable.classList.add('hidden');
        statRecords.innerText = '0';
        statAvg.innerText = '₹0.00';
        statMax.innerText = '₹0.00';
        return;
    }

    emptyHistoryMsg.classList.add('hidden');
    historyTable.classList.remove('hidden');

    let totalAmount = 0;
    let maxAmt = 0;

    historyBody.innerHTML = '';
    // Sort array latest first by year conceptually (or just reverse)
    const reversed = [...historyData].reverse();
    
    reversed.forEach(h => {
        totalAmount += h.total;
        if(h.total > maxAmt) maxAmt = h.total;

        let tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${h.month} ${h.year}</td>
            <td>${h.state}</td>
            <td>${h.units.toFixed(1)}</td>
            <td>₹${h.total.toFixed(2)}</td>
        `;
        historyBody.appendChild(tr);
    });

    const avgAmt = totalAmount / historyData.length;
    
    statRecords.innerText = historyData.length;
    animateValue(statAvg, 0, avgAmt, 800);
    animateValue(statMax, 0, maxAmt, 800);
}

async function clearHistory() {
    if(confirm("Are you sure you want to delete all saved bills?")) {
        try {
            const response = await fetch(`${API_BASE}/bills`, { method: 'DELETE' });
            if (response.ok) {
                historyData = [];
                renderHistory();
                showToast("History cleared!");
            } else {
                showToast("Error clearing history.");
            }
        } catch (e) {
            showToast(`Network Error: ${e.message}`);
        }
    }
}

// Start
document.addEventListener('DOMContentLoaded', init);
