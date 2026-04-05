import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
from datetime import datetime

# ── PDF import (optional) ──────────────────────────────────────────────────
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# ── Constants ──────────────────────────────────────────────────────────────
STATES = {
    "Maharashtra (MSEB)":  {"slabs": [(0,100,3.25),(100,300,7.50),(300,500,9.95),(500,99999,12.00)], "fixed": 40},
    "Delhi (BSES/TPDDL)":  {"slabs": [(0,200,3.00),(200,400,6.50),(400,800,8.00),(800,99999,9.00)],  "fixed": 20},
    "Gujarat (DGVCL)":     {"slabs": [(0,50,2.75),(50,200,4.85),(200,400,7.10),(400,99999,8.50)],    "fixed": 35},
    "Rajasthan (JVVNL)":   {"slabs": [(0,100,3.85),(100,200,6.25),(200,300,8.00),(300,99999,9.50)],  "fixed": 50},
    "UP (DVVNL)":          {"slabs": [(0,100,3.50),(100,150,5.50),(150,300,6.00),(300,99999,7.00)],  "fixed":  0},
    "Karnataka (BESCOM)":  {"slabs": [(0,30,3.15),(30,100,5.45),(100,200,7.20),(200,99999,8.80)],    "fixed": 25},
    "Custom":              {"slabs": [], "fixed": 0},
}
HISTORY_FILE = "bill_history.json"
MONTHS = ["January","February","March","April","May","June",
          "July","August","September","October","November","December"]

# ── Calculation logic ──────────────────────────────────────────────────────
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


# ── PDF Generator ──────────────────────────────────────────────────────────
def generate_pdf(result, state_name, month, year, path):
    doc    = SimpleDocTemplate(path, pagesize=A4,
                               leftMargin=2*cm, rightMargin=2*cm,
                               topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story  = []

    title_style = ParagraphStyle("title", parent=styles["Title"],
                                 fontSize=20, textColor=colors.HexColor("#1a237e"),
                                 spaceAfter=6, alignment=TA_CENTER)
    sub_style   = ParagraphStyle("sub", parent=styles["Normal"],
                                 fontSize=11, textColor=colors.HexColor("#555555"),
                                 alignment=TA_CENTER, spaceAfter=16)
    head_style  = ParagraphStyle("head", parent=styles["Heading2"],
                                 fontSize=13, textColor=colors.HexColor("#1a237e"),
                                 spaceBefore=14, spaceAfter=6)
    bold_right  = ParagraphStyle("boldright", parent=styles["Normal"],
                                 fontSize=11, fontName="Helvetica-Bold", alignment=TA_RIGHT)

    story.append(Paragraph("Electricity Bill", title_style))
    story.append(Paragraph(f"{state_name}  |  {month} {year}", sub_style))

    # ─ Slab table ─
    story.append(Paragraph("Slab Breakdown", head_style))
    slab_data = [["Slab", "Units", "Rate (Rs/unit)", "Charge (Rs)"]]
    for s in result["slabs"]:
        slab_data.append([s["label"], f"{s['units']:.1f}",
                          f"Rs {s['rate']:.2f}", f"Rs {s['charge']:.2f}"])

    slab_table = Table(slab_data, colWidths=[6*cm, 3*cm, 4*cm, 4*cm])
    slab_table.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,0),  colors.HexColor("#1a237e")),
        ("TEXTCOLOR",    (0,0), (-1,0),  colors.white),
        ("FONTNAME",     (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",     (0,0), (-1,-1), 10),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [colors.HexColor("#f5f5f5"), colors.white]),
        ("GRID",         (0,0), (-1,-1), 0.4, colors.HexColor("#cccccc")),
        ("ALIGN",        (1,0), (-1,-1), "RIGHT"),
        ("LEFTPADDING",  (0,0), (-1,-1), 8),
        ("RIGHTPADDING", (0,0), (-1,-1), 8),
        ("TOPPADDING",   (0,0), (-1,-1), 6),
        ("BOTTOMPADDING",(0,0), (-1,-1), 6),
    ]))
    story.append(slab_table)

    # ─ Summary table ─
    story.append(Paragraph("Bill Summary", head_style))
    summary_data = [
        ["Description",               "Amount (Rs)"],
        ["Energy Charges",             f"Rs {result['energy']:.2f}"],
        ["Fixed Charges",              f"Rs {result['fixed']:.2f}"],
        ["Electricity Duty (8%)",      f"Rs {result['tax']:.2f}"],
        ["Surcharge (5%)",             f"Rs {result['surcharge']:.2f}"],
        ["TOTAL BILL",                 f"Rs {result['total']:.2f}"],
    ]
    summary_table = Table(summary_data, colWidths=[10*cm, 7*cm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,0),  colors.HexColor("#1a237e")),
        ("TEXTCOLOR",    (0,0), (-1,0),  colors.white),
        ("FONTNAME",     (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",     (0,0), (-1,-1), 10),
        ("ROWBACKGROUNDS",(0,1),(-1,-2), [colors.HexColor("#f5f5f5"), colors.white]),
        ("BACKGROUND",   (0,-1),(-1,-1), colors.HexColor("#e8f5e9")),
        ("FONTNAME",     (0,-1),(-1,-1), "Helvetica-Bold"),
        ("FONTSIZE",     (0,-1),(-1,-1), 12),
        ("GRID",         (0,0), (-1,-1), 0.4, colors.HexColor("#cccccc")),
        ("ALIGN",        (1,0), (1,-1),  "RIGHT"),
        ("LEFTPADDING",  (0,0), (-1,-1), 10),
        ("RIGHTPADDING", (0,0), (-1,-1), 10),
        ("TOPPADDING",   (0,0), (-1,-1), 7),
        ("BOTTOMPADDING",(0,0), (-1,-1), 7),
    ]))
    story.append(summary_table)

    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(
        f"Generated on {datetime.now().strftime('%d %b %Y, %I:%M %p')}",
        ParagraphStyle("footer", parent=styles["Normal"],
                       fontSize=8, textColor=colors.grey, alignment=TA_CENTER)))
    doc.build(story)


# ══════════════════════════════════════════════════════════════════════════
#  MAIN GUI APP
# ══════════════════════════════════════════════════════════════════════════
class ElectricityApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("⚡ Electricity Bill Calculator")
        self.geometry("820x640")
        self.resizable(True, True)
        self.configure(bg="#f0f4ff")

        # ─ load history ─
        self.history = []
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE) as f:
                    self.history = json.load(f)
            except Exception:
                self.history = []

        self._build_ui()

    # ── UI Builder ────────────────────────────────────────────────────────
    def _build_ui(self):
        # Header
        hdr = tk.Frame(self, bg="#1a237e", pady=14)
        hdr.pack(fill="x")
        tk.Label(hdr, text="⚡  Electricity Bill Calculator",
                 font=("Segoe UI", 18, "bold"), bg="#1a237e", fg="white").pack()

        # Notebook tabs
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TNotebook",        background="#f0f4ff", borderwidth=0)
        style.configure("TNotebook.Tab",    font=("Segoe UI", 11), padding=[16, 6])
        style.configure("TFrame",           background="#f0f4ff")
        style.configure("TLabel",           background="#f0f4ff", font=("Segoe UI", 10))
        style.configure("TCombobox",        font=("Segoe UI", 10))
        style.configure("TEntry",           font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
        style.configure("Treeview",         font=("Segoe UI", 10), rowheight=26)

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab_calc    = ttk.Frame(nb)
        self.tab_history = ttk.Frame(nb)
        nb.add(self.tab_calc,    text="  Calculate Bill  ")
        nb.add(self.tab_history, text="  Monthly Comparison  ")

        self._build_calc_tab()
        self._build_history_tab()

    # ── CALCULATE TAB ─────────────────────────────────────────────────────
    def _build_calc_tab(self):
        parent = self.tab_calc

        # ─ Left: Inputs ─
        left = tk.Frame(parent, bg="#f0f4ff", padx=20, pady=16)
        left.pack(side="left", fill="y")

        def lbl(text, row, col=0, **kw):
            tk.Label(left, text=text, bg="#f0f4ff",
                     font=("Segoe UI", 10), anchor="w", **kw).grid(
                row=row, column=col, sticky="w", pady=4, padx=(0,8))

        lbl("State / Board", 0)
        self.state_var = tk.StringVar(value="Maharashtra (MSEB)")
        state_cb = ttk.Combobox(left, textvariable=self.state_var,
                                values=list(STATES.keys()), width=26, state="readonly")
        state_cb.grid(row=0, column=1, pady=4, sticky="w")
        state_cb.bind("<<ComboboxSelected>>", self._on_state_change)

        lbl("Month", 1)
        self.month_var = tk.StringVar(value=MONTHS[datetime.now().month - 1])
        ttk.Combobox(left, textvariable=self.month_var, values=MONTHS,
                     width=14, state="readonly").grid(row=1, column=1, pady=4, sticky="w")

        lbl("Year", 2)
        self.year_var = tk.StringVar(value=str(datetime.now().year))
        ttk.Entry(left, textvariable=self.year_var, width=10).grid(
            row=2, column=1, pady=4, sticky="w")

        lbl("Units Consumed (kWh)", 3)
        self.units_var = tk.StringVar()
        ttk.Entry(left, textvariable=self.units_var, width=14).grid(
            row=3, column=1, pady=4, sticky="w")

        # Custom fields (hidden by default)
        self.custom_frame = tk.Frame(left, bg="#f0f4ff")
        tk.Label(self.custom_frame, text="Rate (Rs/unit)",
                 bg="#f0f4ff", font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w", pady=3)
        self.custom_rate = tk.StringVar(value="6.0")
        ttk.Entry(self.custom_frame, textvariable=self.custom_rate, width=10).grid(
            row=0, column=1, padx=8)
        tk.Label(self.custom_frame, text="Fixed (Rs/month)",
                 bg="#f0f4ff", font=("Segoe UI", 10)).grid(row=1, column=0, sticky="w", pady=3)
        self.custom_fixed = tk.StringVar(value="50.0")
        ttk.Entry(self.custom_frame, textvariable=self.custom_fixed, width=10).grid(
            row=1, column=1, padx=8)

        # Buttons
        btn_frame = tk.Frame(left, bg="#f0f4ff")
        btn_frame.grid(row=10, column=0, columnspan=2, pady=16, sticky="w")

        tk.Button(btn_frame, text="  Calculate  ", font=("Segoe UI", 11, "bold"),
                  bg="#1a237e", fg="white", relief="flat", padx=10, pady=6,
                  cursor="hand2", command=self._calculate).pack(side="left", padx=(0,8))

        tk.Button(btn_frame, text="  Save to History  ", font=("Segoe UI", 10),
                  bg="#388e3c", fg="white", relief="flat", padx=10, pady=6,
                  cursor="hand2", command=self._save_to_history).pack(side="left", padx=(0,8))

        self.pdf_btn = tk.Button(btn_frame, text="  Export PDF  ",
                                 font=("Segoe UI", 10),
                                 bg="#f57c00" if PDF_AVAILABLE else "#aaaaaa",
                                 fg="white", relief="flat", padx=10, pady=6,
                                 cursor="hand2" if PDF_AVAILABLE else "arrow",
                                 state="normal" if PDF_AVAILABLE else "disabled",
                                 command=self._export_pdf)
        self.pdf_btn.pack(side="left")

        if not PDF_AVAILABLE:
            tk.Label(left, text="* reportlab not found. Run: pip install reportlab",
                     bg="#f0f4ff", fg="#cc0000", font=("Segoe UI", 8)).grid(
                row=11, column=0, columnspan=2, sticky="w")

        # ─ Right: Result panel ─
        right = tk.Frame(parent, bg="white", padx=20, pady=16,
                         relief="flat", bd=1)
        right.pack(side="left", fill="both", expand=True, padx=(0,12), pady=12)

        tk.Label(right, text="Bill Breakdown", font=("Segoe UI", 13, "bold"),
                 bg="white", fg="#1a237e").pack(anchor="w")

        cols = ("Slab", "Units", "Rate (Rs)", "Charge (Rs)")
        self.slab_tree = ttk.Treeview(right, columns=cols, show="headings", height=5)
        for c in cols:
            self.slab_tree.heading(c, text=c)
            self.slab_tree.column(c, width=110, anchor="e")
        self.slab_tree.column("Slab", anchor="w", width=150)
        self.slab_tree.pack(fill="x", pady=(6,10))

        # Summary labels
        self.summary_frame = tk.Frame(right, bg="white")
        self.summary_frame.pack(fill="x")
        self.sum_labels = {}
        rows_cfg = [
            ("energy",    "Energy Charges",        "#333333"),
            ("fixed",     "Fixed Charges",          "#333333"),
            ("tax",       "Electricity Duty (8%)",  "#555555"),
            ("surcharge", "Surcharge (5%)",          "#555555"),
            ("sep",       "",                        "#dddddd"),
            ("total",     "TOTAL BILL",             "#1a237e"),
        ]
        for i, (key, label, color) in enumerate(rows_cfg):
            if key == "sep":
                tk.Frame(self.summary_frame, bg="#dddddd", height=1).grid(
                    row=i, column=0, columnspan=2, sticky="ew", pady=4)
                continue
            tk.Label(self.summary_frame, text=label, bg="white",
                     font=("Segoe UI", 10 if key != "total" else 12,
                           "normal" if key != "total" else "bold"),
                     fg=color).grid(row=i, column=0, sticky="w", pady=3)
            v = tk.StringVar(value="—")
            self.sum_labels[key] = v
            tk.Label(self.summary_frame, textvariable=v, bg="white",
                     font=("Segoe UI", 10 if key != "total" else 12,
                           "normal" if key != "total" else "bold"),
                     fg=color).grid(row=i, column=1, sticky="e", padx=(40,0))

        # Tips
        self.tips_lbl = tk.Label(right, text="", bg="white", fg="#2e7d32",
                                 font=("Segoe UI", 9), justify="left", wraplength=320)
        self.tips_lbl.pack(anchor="w", pady=(10,0))

        self.last_result = None

    def _on_state_change(self, _=None):
        if self.state_var.get() == "Custom":
            self.custom_frame.grid(row=4, column=0, columnspan=2, sticky="w", pady=4)
        else:
            self.custom_frame.grid_remove()

    def _calculate(self):
        try:
            units = float(self.units_var.get())
            if units < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Sahi units daalo (positive number)!")
            return

        state = self.state_var.get()
        cr    = float(self.custom_rate.get() or 0)  if state == "Custom" else 0
        cf    = float(self.custom_fixed.get() or 0) if state == "Custom" else 0

        result = compute_bill(units, state, cr, cf)
        self.last_result = result

        # Update slab tree
        for row in self.slab_tree.get_children():
            self.slab_tree.delete(row)
        for s in result["slabs"]:
            self.slab_tree.insert("", "end",
                values=(s["label"], f"{s['units']:.1f}",
                        f"Rs {s['rate']:.2f}", f"Rs {s['charge']:.2f}"))

        # Update summary
        self.sum_labels["energy"].set(f"Rs {result['energy']:.2f}")
        self.sum_labels["fixed"].set(f"Rs {result['fixed']:.2f}")
        self.sum_labels["tax"].set(f"Rs {result['tax']:.2f}")
        self.sum_labels["surcharge"].set(f"Rs {result['surcharge']:.2f}")
        self.sum_labels["total"].set(f"Rs {result['total']:.2f}")

        # Tips
        tips = []
        if units > 300: tips.append("⚠ Bahut zyada! AC/geyser check karo.")
        if units > 200: tips.append("• LED bulbs use karo (80% saving)")
        if units > 100: tips.append("• Standby devices band karo")
        tips.append("• Solar subsidy ke baare mein sochna!")
        self.tips_lbl.config(text="\n".join(tips))

    def _save_to_history(self):
        if not self.last_result:
            messagebox.showwarning("Warning", "Pehle calculate karo!")
            return
        entry = {
            "month":    self.month_var.get(),
            "year":     self.year_var.get(),
            "state":    self.state_var.get(),
            "units":    self.last_result["units"],
            "total":    round(self.last_result["total"], 2),
            "energy":   round(self.last_result["energy"], 2),
        }
        self.history.append(entry)
        with open(HISTORY_FILE, "w") as f:
            json.dump(self.history, f, indent=2)
        messagebox.showinfo("Saved!", f"{entry['month']} {entry['year']} ka bill save ho gaya!")
        self._refresh_history()

    def _export_pdf(self):
        if not self.last_result:
            messagebox.showwarning("Warning", "Pehle calculate karo!")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile=f"bill_{self.month_var.get()}_{self.year_var.get()}.pdf")
        if not path:
            return
        try:
            generate_pdf(self.last_result, self.state_var.get(),
                         self.month_var.get(), self.year_var.get(), path)
            messagebox.showinfo("PDF Ready!", f"PDF save ho gayi:\n{path}")
        except Exception as e:
            messagebox.showerror("Error", f"PDF nahi bani: {e}")

    # ── HISTORY / COMPARISON TAB ───────────────────────────────────────────
    def _build_history_tab(self):
        parent = self.tab_history

        # Toolbar
        bar = tk.Frame(parent, bg="#f0f4ff", pady=8)
        bar.pack(fill="x", padx=12)
        tk.Label(bar, text="Monthly Comparison", font=("Segoe UI", 13, "bold"),
                 bg="#f0f4ff", fg="#1a237e").pack(side="left")
        tk.Button(bar, text="Clear History", font=("Segoe UI", 9),
                  bg="#c62828", fg="white", relief="flat", padx=8, pady=4,
                  cursor="hand2", command=self._clear_history).pack(side="right")

        # Treeview
        cols = ("Month", "Year", "State", "Units (kWh)", "Total Bill (Rs)")
        self.hist_tree = ttk.Treeview(parent, columns=cols, show="headings", height=14)
        for c in cols:
            self.hist_tree.heading(c, text=c)
            w = 80 if c in ("Year","Units (kWh)") else 160
            self.hist_tree.column(c, width=w, anchor="center")
        self.hist_tree.pack(fill="both", expand=True, padx=12, pady=(0,6))

        # Stats bar
        self.stats_frame = tk.Frame(parent, bg="white", pady=10, padx=16)
        self.stats_frame.pack(fill="x", padx=12, pady=(0,10))
        self.stats_lbl = tk.Label(self.stats_frame, text="", bg="white",
                                  font=("Segoe UI", 10), fg="#333333", justify="left")
        self.stats_lbl.pack(anchor="w")

        self._refresh_history()

    def _refresh_history(self):
        for row in self.hist_tree.get_children():
            self.hist_tree.delete(row)

        if not self.history:
            self.stats_lbl.config(text="Koi history nahi. Pehle bills calculate karke save karo.")
            return

        totals = []
        units_list = []
        for i, e in enumerate(self.history):
            tag = "even" if i % 2 == 0 else "odd"
            self.hist_tree.insert("", "end", tags=(tag,),
                values=(e["month"], e["year"], e["state"],
                        f"{e['units']:.1f}", f"Rs {e['total']:.2f}"))
            totals.append(e["total"])
            units_list.append(e["units"])

        self.hist_tree.tag_configure("even", background="#f5f5f5")
        self.hist_tree.tag_configure("odd",  background="white")

        avg_bill  = sum(totals) / len(totals)
        max_bill  = max(totals)
        min_bill  = min(totals)
        avg_units = sum(units_list) / len(units_list)

        # Highest month
        hi_idx  = totals.index(max_bill)
        hi_month = f"{self.history[hi_idx]['month']} {self.history[hi_idx]['year']}"

        stats_text = (
            f"Total records: {len(self.history)}     "
            f"Avg bill: Rs {avg_bill:.2f}     "
            f"Highest: Rs {max_bill:.2f} ({hi_month})     "
            f"Lowest: Rs {min_bill:.2f}     "
            f"Avg units/month: {avg_units:.1f} kWh"
        )
        self.stats_lbl.config(text=stats_text)

    def _clear_history(self):
        if not self.history:
            return
        if messagebox.askyesno("Confirm", "Saari history delete karna chahte ho?"):
            self.history = []
            if os.path.exists(HISTORY_FILE):
                os.remove(HISTORY_FILE)
            self._refresh_history()


# ── Entry point ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = ElectricityApp()
    app.mainloop()
