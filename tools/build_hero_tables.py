"""Build 4 hero tables for the Bermuda manual using great_tables.
Output: self-contained HTML fragments saved to chapters/assets/shared/tables/
Each fragment is then spliced into the chapter draft replacing the existing markdown table.
"""
from pathlib import Path
import pandas as pd
from great_tables import GT, md, loc, style

OUT = Path("C:/bermuda-manual/chapters/assets/shared/tables")
OUT.mkdir(parents=True, exist_ok=True)


def base_options(gt: GT) -> GT:
    return gt.tab_options(
        table_font_names="Georgia, 'Times New Roman', serif",
        table_font_size="11px",
        heading_title_font_size="14px",
        heading_subtitle_font_size="11px",
        column_labels_font_weight="bold",
        column_labels_background_color="#F1ECDC",
        column_labels_border_top_color="#444",
        column_labels_border_top_width="1.2px",
        column_labels_border_bottom_color="#444",
        column_labels_border_bottom_width="1px",
        table_border_top_color="#444",
        table_border_top_width="1.2px",
        table_border_bottom_color="#444",
        table_border_bottom_width="1.2px",
        table_body_border_bottom_color="#444",
        table_body_hlines_color="#e5e5e5",
        table_body_hlines_width="0.5px",
        source_notes_font_size="9px",
        source_notes_padding="6px",
        data_row_padding="5px",
        column_labels_padding="6px",
        table_background_color="white",
    )


# ---- ch-06: single-adult monthly budget ----
def single_adult_budget():
    df = pd.DataFrame({
        "category": [
            "Rent, 1-bedroom outside Hamilton",
            "Groceries (Numbeo, net of restaurants)",
            "Restaurant meals (4 inexpensive tier)",
            "Utilities, mobile, broadband",
            "Monthly transit pass",
            "Health insurance, employee share",
            "Personal, clothing, leisure",
        ],
        "amount": [2450, 700, 220, 554, 69, 500, 400],
        "share": [0.501, 0.143, 0.045, 0.113, 0.014, 0.102, 0.082],
    })
    total = df["amount"].sum()
    max_idx = [int(df["amount"].idxmax())]
    gt = (
        GT(df, rowname_col="category")
        .tab_header(
            title="A single adult's monthly budget",
            subtitle="Underwriter renting outside Hamilton, BMD pegged at parity with USD.",
        )
        .fmt_currency(columns="amount", currency="USD", decimals=0, sep_mark=",")
        .fmt_percent(columns="share", decimals=1)
        .cols_label(amount="Monthly cost (BMD)", share="Share")
        .tab_source_note(source_note=md(f"_Total: **${total:,}** per month._ Figures rounded; based on Numbeo March 2026 with editor's notes."))
        .tab_style(
            style=style.fill(color="#FAF6E9"),
            locations=loc.body(rows=max_idx),
        )
        .cols_align(align="right", columns=["amount", "share"])
    )
    gt = base_options(gt)
    return gt


# ---- ch-06: family-of-four monthly budget ----
def family_budget():
    df = pd.DataFrame({
        "category": [
            "Rent, 3-bedroom outside Hamilton",
            "Groceries (Numbeo, net of restaurants)",
            "Restaurant meals (6 mid-tier)",
            "Utilities, mobile, broadband",
            "Car: gasoline, insurance, amortised purchase",
            "Health insurance (2 adults + 2 children)",
            "One preschool place",
        ],
        "amount": [7577, 2300, 700, 750, 900, 1400, 1342],
    })
    total = df["amount"].sum()
    df["share"] = df["amount"] / total
    max_idx = [int(df["amount"].idxmax())]
    gt = (
        GT(df, rowname_col="category")
        .tab_header(
            title="A family of four's monthly budget",
            subtitle="Two working adults, two children, one car, one preschool place.",
        )
        .fmt_currency(columns="amount", currency="USD", decimals=0, sep_mark=",")
        .fmt_percent(columns="share", decimals=1)
        .cols_label(amount="Monthly cost (BMD)", share="Share")
        .tab_source_note(source_note=md(f"_Total: **${total:,}** per month — roughly three times the single-adult budget for less than three times the consumption._"))
        .tab_style(
            style=style.fill(color="#FAF6E9"),
            locations=loc.body(rows=max_idx),
        )
        .cols_align(align="right", columns=["amount", "share"])
    )
    gt = base_options(gt)
    return gt


# ---- ch-07: ARV brackets vs permit eligibility ----
def arv_brackets():
    df = pd.DataFrame({
        "buyer": [
            "Bermudian / status holder",
            "Permanent Resident",
            "Non-Bermudian buyer",
        ],
        "arv": ["None", "Restricted", "Above floor"],
        "house_fee": ["—", "Per policy", "8%"],
        "condo_fee": ["—", "Per policy", "6%"],
        "inventory": [
            "Full stock",
            "Defined subset",
            "Upper tier only",
        ],
    })
    gt = (
        GT(df, rowname_col="buyer")
        .tab_header(
            title="Who can buy what, and at what cost",
            subtitle="Bermuda residential-property purchase rules by buyer category.",
        )
        .tab_spanner(label="Licence fee", columns=["house_fee", "condo_fee"])
        .cols_label(
            arv="ARV threshold",
            house_fee="House",
            condo_fee="Condo",
            inventory="Inventory accessible",
        )
        .tab_source_note(source_note=md("_ARV: Annual Rental Value. Licence fees are one-off, paid on completion. Source: Ministry of Home Affairs guidance, 2025 Work Permit Policy._"))
        .tab_style(
            style=style.fill(color="#FAF6E9"),
            locations=loc.body(rows=[0]),
        )
        .cols_align(align="center", columns=["house_fee", "condo_fee"])
    )
    gt = base_options(gt)
    return gt


# ---- ch-09: insurance products ----
def insurance_products():
    df = pd.DataFrame({
        "plan": ["HIP", "FutureCare", "GEHI", "Private comprehensive"],
        "operator": [
            "Health Insurance Department",
            "Health Insurance Department",
            "Government Employees Health Insurance",
            "Approved private insurers",
        ],
        "premium": [
            "Means-tested, subsidised",
            "Capped seniors rate",
            "Civil-service payroll deduction",
            "$700–$1,500 per person",
        ],
        "coverage": [
            "Low-income residents; Standard Hospital Benefit plus limited supplement",
            "Residents aged 65+; SHB plus drug, vision, overseas-referral cover",
            "Active and retired civil servants and their dependants",
            "SHB floor plus physician, drugs, dental, vision, overseas referrals",
        ],
    })
    gt = (
        GT(df, rowname_col="plan")
        .tab_header(
            title="Bermuda's four health-insurance products",
            subtitle="Premium and coverage at a glance.",
        )
        .cols_label(
            operator="Operator",
            premium="Monthly premium",
            coverage="Coverage notes",
        )
        .tab_source_note(source_note=md("_SHB: Standard Hospital Benefit, the mandatory floor every Bermuda plan must include. Source: Bermuda Health Council annual report._"))
        .tab_style(
            style=style.fill(color="#FAF6E9"),
            locations=loc.body(rows=[1]),
        )
    )
    gt = base_options(gt)
    return gt


TABLES = {
    "ch-06-single-budget": single_adult_budget,
    "ch-06-family-budget": family_budget,
    "ch-07-arv-brackets": arv_brackets,
    "ch-09-insurance-products": insurance_products,
}

if __name__ == "__main__":
    for name, fn in TABLES.items():
        gt = fn()
        html_str = gt.as_raw_html(inline_css=True)
        # Wrap with a div for layout control + page-break-inside avoid
        wrapped = f'<div class="hero-table" style="break-inside: avoid; page-break-inside: avoid; margin: 1.1em 0;">\n{html_str}\n</div>'
        (OUT / f"{name}.html").write_text(wrapped, encoding="utf-8")
        print(f"wrote {OUT / name}.html ({len(wrapped):,} bytes)")
