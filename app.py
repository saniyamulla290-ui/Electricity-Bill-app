import streamlit as st
import json
import os
from datetime import datetime

# ── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="⚡ Electricity Bill Calculator",
    page_icon="⚡",
    layout="wide"
)

# ── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1a237e, #283593);
        padding: 20px;
        border-radius: 12px;
        text-align: center;
        color: white;
        margin-bottom: 24px;
    }
    .result-card {
        background: white;
        padding: 20px;
        border-radius: 12px;
        border-left: 5px solid #1a237e;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .total-amount {
        font-size: 2rem;
        font-weight: bold;
        color: #1a237e;
    }
    .tip-box {
        background: #e8f5e9;
        padding: 12px;
        border-radius: 8px;
        border-left: 4px solid #2e7d32;
    }
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
STATES = {
    "Maharashtra (MSEB)":  {"slabs": [(0,100,3.25),(100,300,7.50),(300,500,9.95),(500,99999,12.00)], "fixed": 40},
    "Delhi (BSES/TPDDL)":  {"slabs": [(0,200,3.00),(200,400,6.50),(400,800,8.00),(800,99999,9.00)],  "fixed": 20},
    "Gujarat (DGVCL)":     {"slabs": [(0,50,2.75),(50,200,4.85),(200,400,7.10),(400,99999,8.50)],    "fixed": 35},
    "Rajasthan (JVVNL)":   {"slabs": [(0,100,3.85),(100,200,6.25),(200,300,8.00),(300,99999,9.50)],  "fixed": 50},
    "UP (DVVNL)":          {"slabs": [(0,100,3.50),(100,150,5.50),(150,300,6.00),(300,99999,7.00)],  "fixed":  0},
    "Karnataka (BESCOM)":  {"slabs": [(0,30,3.15),(30,100,5.45),(100,200,7.20),(200,99999,8.80)],    "fixed": 25},
    "Custom":              {"slabs": [], "fixed": 0},
}
MONTHS = ["January","February","March","April","May","June",
          "July","August","September","October","November","December"]
HISTORY_FILE = "bill_history.json"

# ── Load/Save History ─────────────────────────────────────────────────────────
def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE) as f:
                return json.load(f)
        except:
            return []
    return []

def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

# ── Calculation Logic ─────────────────────────────────────────────────────────
def compute_bill(units, state_name, custom_rate=0.0, custom_fixed=0.0):
    if state_name == "Custom":
        slabs_info = [{"label": "All units", "units": units, "rate": custom_rate,
                       "charge": units * custom_rate}]
        energy = units * custom_rate
        fixed  = custom_fixed
    else:
        info   = STATES[state_name]
        slabs  = info["slabs"]
        fixed  = info["fixed"]
        energy = 0
        slabs_info = []
        remaining  = units
        for (low, high, rate) in slabs:
            if remaining <= 0:
                break
            used   = min(remaining, high - low)
            charge = used * rate
            energy += charge
            if used > 0:
                slabs_info.append({"label": f"{low}–{high} units",
                                   "units": used, "rate": rate, "charge": charge})
            remaining -= used

    tax       = energy * 0.08
    surcharge = energy * 0.05
    total     = energy + fixed + tax + surcharge
    return {"slabs": slabs_info, "energy": energy, "fixed": fixed,
            "tax": tax, "surcharge": surcharge, "total": total, "units": units}

# ── Session State ─────────────────────────────────────────────────────────────
if "history" not in st.session_state:
    st.session_state.history = load_history()
if "result" not in st.session_state:
    st.session_state.result = None

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown('<div class="main-header"><h1>⚡ Electricity Bill Calculator</h1><p>India ke sabhi major states ke liye</p></div>', unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["🧮 Bill Calculator", "📊 History & Comparison"])

# ════════════════════════════════════════════════════════════
# TAB 1 — CALCULATOR
# ════════════════════════════════════════════════════════════
with tab1:
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("📝 Bill Details")

        state = st.selectbox("State / Utility", list(STATES.keys()))
        units = st.number_input("Units Consumed (kWh)", min_value=0.0, step=1.0, value=0.0)

        col_m, col_y = st.columns(2)
        with col_m:
            month = st.selectbox("Month", MONTHS, index=datetime.now().month - 1)
        with col_y:
            year = st.selectbox("Year", [str(y) for y in range(2020, 2031)], index=5)

        # Custom fields
        custom_rate = 0.0
        custom_fixed = 0.0
        if state == "Custom":
            st.markdown("**Custom Rate Settings**")
            custom_rate  = st.number_input("Rate per unit (Rs)", min_value=0.0, step=0.1)
            custom_fixed = st.number_input("Fixed Charge (Rs)", min_value=0.0, step=1.0)

        calc_btn = st.button("⚡ Calculate Bill", type="primary", use_container_width=True)

        if calc_btn:
            if units <= 0:
                st.error("Sahi units daalo (positive number)!")
            else:
                st.session_state.result = compute_bill(units, state, custom_rate, custom_fixed)
                st.session_state.calc_state = state
                st.session_state.calc_month = month
                st.session_state.calc_year = year

    with col2:
        st.subheader("📋 Bill Summary")

        if st.session_state.result:
            r = st.session_state.result

            # Total amount
            st.markdown(f"""
            <div class="result-card">
                <p style="color:#555; margin:0">Total Bill Amount</p>
                <p class="total-amount">Rs {r['total']:.2f}</p>
                <p style="color:#888; font-size:0.9rem">{st.session_state.calc_month} {st.session_state.calc_year} | {st.session_state.calc_state}</p>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("")

            # Summary table
            summary_data = {
                "Description": ["Energy Charges", "Fixed Charges", "Electricity Duty (8%)", "Surcharge (5%)", "**TOTAL**"],
                "Amount (Rs)": [
                    f"Rs {r['energy']:.2f}",
                    f"Rs {r['fixed']:.2f}",
                    f"Rs {r['tax']:.2f}",
                    f"Rs {r['surcharge']:.2f}",
                    f"**Rs {r['total']:.2f}**"
                ]
            }
            st.table(summary_data)

            # Slab breakdown
            st.subheader("📊 Slab Breakdown")
            slab_data = []
            for s in r["slabs"]:
                slab_data.append({
                    "Slab": s["label"],
                    "Units": f"{s['units']:.1f}",
                    "Rate (Rs/unit)": f"Rs {s['rate']:.2f}",
                    "Charge (Rs)": f"Rs {s['charge']:.2f}"
                })
            if slab_data:
                st.table(slab_data)

            # Tips
            tips = []
            if r["units"] > 300: tips.append("⚠️ Bahut zyada! AC/geyser check karo.")
            if r["units"] > 200: tips.append("💡 LED bulbs use karo (80% saving)")
            if r["units"] > 100: tips.append("🔌 Standby devices band karo")
            tips.append("☀️ Solar subsidy ke baare mein sochna!")

            st.markdown(f"""
            <div class="tip-box">
                <b>💡 Tips:</b><br>
                {"<br>".join(tips)}
            </div>
            """, unsafe_allow_html=True)

            st.markdown("")

            # Save to history
            if st.button("💾 Save to History", use_container_width=True):
                entry = {
                    "month": st.session_state.calc_month,
                    "year":  st.session_state.calc_year,
                    "state": st.session_state.calc_state,
                    "units": r["units"],
                    "total": round(r["total"], 2),
                    "energy": round(r["energy"], 2),
                }
                st.session_state.history.append(entry)
                save_history(st.session_state.history)
                st.success(f"✅ {entry['month']} {entry['year']} ka bill save ho gaya!")
        else:
            st.info("👈 Units daalo aur Calculate dabao!")

# ════════════════════════════════════════════════════════════
# TAB 2 — HISTORY
# ════════════════════════════════════════════════════════════
with tab2:
    st.subheader("📊 Monthly Comparison")

    history = st.session_state.history

    if not history:
        st.info("Koi history nahi. Pehle bills calculate karke save karo.")
    else:
        # Stats
        totals = [e["total"] for e in history]
        units_list = [e["units"] for e in history]
        avg_bill  = sum(totals) / len(totals)
        max_bill  = max(totals)
        min_bill  = min(totals)
        avg_units = sum(units_list) / len(units_list)
        hi_idx    = totals.index(max_bill)
        hi_month  = f"{history[hi_idx]['month']} {history[hi_idx]['year']}"

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📝 Total Records", len(history))
        c2.metric("📈 Avg Bill", f"Rs {avg_bill:.2f}")
        c3.metric("🔺 Highest", f"Rs {max_bill:.2f}", hi_month)
        c4.metric("🔻 Lowest", f"Rs {min_bill:.2f}")

        st.markdown("")

        # History table
        table_data = []
        for e in history:
            table_data.append({
                "Month": e["month"],
                "Year": e["year"],
                "State": e["state"],
                "Units (kWh)": f"{e['units']:.1f}",
                "Total Bill (Rs)": f"Rs {e['total']:.2f}"
            })
        st.table(table_data)

        # Chart
        st.subheader("📈 Bill Trend")
        chart_data = {f"{e['month'][:3]} {e['year']}": e["total"] for e in history}
        st.bar_chart(chart_data)

        # Clear history
        if st.button("🗑️ Clear All History", type="secondary"):
            st.session_state.history = []
            if os.path.exists(HISTORY_FILE):
                os.remove(HISTORY_FILE)
            st.success("History clear ho gayi!")
            st.rerun()

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    f"<p style='text-align:center; color:#888; font-size:0.85rem'>Generated on {datetime.now().strftime('%d %b %Y, %I:%M %p')} | ⚡ Electricity Bill Calculator</p>",
    unsafe_allow_html=True
)
