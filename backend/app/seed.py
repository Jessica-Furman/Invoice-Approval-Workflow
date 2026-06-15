"""Reset the database and load demo data.

Run:  python -m app.seed
Mirrors the Figma detail screen (Avasoft invoice, 6/7 lines matching) plus extra invoices so the
dashboard's Flagged / Matched / All columns are all populated for the M1 demo.
"""
from __future__ import annotations

import re
from datetime import date

from app import models
from app.db.base import Base, SessionLocal, engine


def normalize_name(name: str | None) -> str | None:
    if not name:
        return None
    n = name.lower().strip()
    n = re.sub(r"[^a-z0-9\s]", "", n)
    n = re.sub(r"\s+", " ", n)
    return n


def _line(contractor, hours, rate, amount, status, diff=None):
    return models.InvoiceLineItem(
        contractor_name=contractor,
        contractor_name_normalized=normalize_name(contractor),
        hours=hours,
        rate=rate,
        amount=amount,
        line_status=status,
        diff=diff or {},
    )


def _ts(contractor, hours, rate, project_id):
    return models.ClarityTimesheet(
        contractor_name=contractor,
        contractor_name_normalized=normalize_name(contractor),
        hours=hours,
        rate=rate,
        period_start=date(2026, 4, 26),
        period_end=date(2026, 5, 30),
        project_id=project_id,
        source_row_hash=f"seed-{normalize_name(contractor)}-{hours}-{rate}-{project_id}",
    )


def seed() -> None:
    # Fresh demo every run.
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # ---- Clarity projects (from Figma "Clarity Project Details") ----
        projects = [
            models.ClarityProject(project_id="PR00346", project_name="Corporate Systems",
                                  budget_id="BUD-AC220", capex_opex="CAPEX", cost_center="CostCenterAC220",
                                  vendor="Avasoft", lob="ACIMA", spend=450.0),
            models.ClarityProject(project_id="PR00769", project_name="Q2 Corp Initiative",
                                  budget_id="BUD-AC220", capex_opex="CAPEX", cost_center="CostCenterAC220",
                                  vendor="Avasoft", lob="ACIMA", spend=7230.0),
            models.ClarityProject(project_id="PR00533", project_name="Account Platform",
                                  budget_id="BUD-UP110", capex_opex="CAPEX", cost_center="CostCenterAC220",
                                  vendor="Avasoft", lob="Upbound", spend=2500.0),
            models.ClarityProject(project_id="PR00333", project_name="Q2 Corp OpEx",
                                  budget_id="BUD-OP500", capex_opex="OPEX", cost_center="CostCenterAC220",
                                  vendor="Avasoft", lob="OPEX", spend=4500.0),
            models.ClarityProject(project_id="PR01001", project_name="Data Platform Build",
                                  budget_id="BUD-DP900", capex_opex="CAPEX", cost_center="CostCenterDP900",
                                  vendor="Terraform Architects", lob="Upbound", spend=22000.0),
            models.ClarityProject(project_id="PR02002", project_name="Network Refresh",
                                  budget_id="BUD-NW700", capex_opex="OPEX", cost_center="CostCenterNW700",
                                  vendor="Horizon Networks", lob="Infra", spend=6740.0),
        ]
        db.add_all(projects)

        # ---- Clarity timesheets ----
        # Avasoft contractors. Note Paramaguru's Clarity amount = 80*35 = 2800? Figma shows Clarity 2400
        # (rate shown 35 but amount 2400) -> the invoice line will mismatch on amount.
        db.add_all([
            _ts("Noorul Sarfaraz", 80, 30, "PR00346"),
            _ts("Promodini Narayanan", 120, 30, "PR00769"),
            _ts("Suhail Hameed", 120, 35, "PR00533"),
            _ts("Paramaguru Pandiyarajan", 80, 30, "PR00333"),  # Clarity rate 30 -> amount 2400
            _ts("Lakshman Srinivasan", 200, 35, "PR00346"),
            _ts("Lakshman Srinivasan", 200, 26, "PR00769"),
            _ts("Parvesh Mohamed", 200, 26, "PR00533"),
            # Terraform Architects (fully matched invoice below)
            _ts("Alice Chen", 160, 95, "PR01001"),
            _ts("Marcus Webb", 160, 90, "PR01001"),
        ])

        # ---- Invoice 1: Avasoft — FLAGGED (6/7 lines match; Paramaguru amount mismatch) ----
        avasoft = models.Invoice(
            vendor_name="Avasoft",
            invoice_number="REN0609202621882",
            date_received=date(2026, 6, 1),
            payment_period_start=date(2026, 4, 26),
            payment_period_end=date(2026, 5, 30),
            total_invoice_cost=30400.0,
            status=models.STATUS_FLAGGED,
            pdf_storage_key="AVASOFT_REN0609202621882.pdf",
            parse_confidence=0.98,
            mismatch_reasons=[{
                "field": "amount",
                "reason": "Invoice amount for Paramaguru Pandiyarajan does not match Clarity (rate differs).",
                "invoice_value": "$2,800.00",
                "clarity_value": "$2,400.00",
            }],
            line_items=[
                _line("Noorul Sarfaraz", 80, 30, 2400, models.STATUS_MATCHED),
                _line("Promodini Narayanan", 120, 30, 3600, models.STATUS_MATCHED),
                _line("Suhail Hameed", 120, 35, 4200, models.STATUS_MATCHED),
                _line("Paramaguru Pandiyarajan", 80, 35, 2800, models.STATUS_FLAGGED,
                      diff={"amount_delta": 400.0, "rate_delta": 5.0}),
                _line("Lakshman Srinivasan", 200, 35, 7000, models.STATUS_MATCHED),
                _line("Lakshman Srinivasan", 200, 26, 5200, models.STATUS_MATCHED),
                _line("Parvesh Mohamed", 200, 26, 5200, models.STATUS_MATCHED),
            ],
        )

        # ---- Invoice 2: Terraform Architects — MATCHED ----
        terraform = models.Invoice(
            vendor_name="Terraform Architects",
            invoice_number="INV-8802",
            date_received=date(2026, 5, 28),
            payment_period_start=date(2026, 4, 26),
            payment_period_end=date(2026, 5, 30),
            total_invoice_cost=29600.0,
            status=models.STATUS_MATCHED,
            pdf_storage_key="TERRAFORM_INV-8802.pdf",
            parse_confidence=0.99,
            mismatch_reasons=[],
            line_items=[
                _line("Alice Chen", 160, 95, 15200, models.STATUS_MATCHED),
                _line("Marcus Webb", 160, 90, 14400, models.STATUS_MATCHED),
            ],
        )

        # ---- Invoice 3: Horizon Networks — NEEDS REVIEW (missing rate on a line) ----
        horizon = models.Invoice(
            vendor_name="Horizon Networks",
            invoice_number="INV-8833",
            date_received=date(2026, 6, 5),
            payment_period_start=date(2026, 5, 1),
            payment_period_end=date(2026, 5, 31),
            total_invoice_cost=6740.0,
            status=models.STATUS_NEEDS_REVIEW,
            pdf_storage_key="HORIZON_INV-8833.pdf",
            parse_confidence=0.71,
            mismatch_reasons=[{
                "field": "rate",
                "reason": "Hourly rate could not be parsed from the invoice for Dana Lin.",
                "invoice_value": None,
                "clarity_value": "$80.00",
            }],
            line_items=[
                _line("Dana Lin", 84, None, None, models.STATUS_NEEDS_REVIEW),
            ],
        )

        # ---- Invoice 4: Velocity Dev Corp — MATCHED ----
        velocity = models.Invoice(
            vendor_name="Velocity Dev Corp",
            invoice_number="INV-8839",
            date_received=date(2026, 6, 8),
            payment_period_start=date(2026, 5, 1),
            payment_period_end=date(2026, 5, 31),
            total_invoice_cost=3200.0,
            status=models.STATUS_MATCHED,
            pdf_storage_key="VELOCITY_INV-8839.pdf",
            parse_confidence=0.97,
            mismatch_reasons=[],
            line_items=[
                _line("Priya Raman", 40, 80, 3200, models.STATUS_MATCHED),
            ],
        )

        db.add_all([avasoft, terraform, horizon, velocity])
        db.commit()
        print(f"Seeded {db.query(models.Invoice).count()} invoices, "
              f"{db.query(models.ClarityTimesheet).count()} timesheets, "
              f"{db.query(models.ClarityProject).count()} projects.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
