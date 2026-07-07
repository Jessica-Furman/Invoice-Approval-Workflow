# InVoicee — Architecture & Process Overview

**Automated contractor invoice processing for Upbound Group Accounts Payable.**

InVoicee ingests contractor invoices, validates the billed hours against **Clarity** timekeeping,
separates clean invoices from exceptions, and prepares them for payment in **Coupa** — replacing a
manual, line-by-line review.

> An executive-ready one-page version is in **`InVoicee_Architecture.html`** — open it in any browser
> and use *Print → Save as PDF* to email it.

---

## How an invoice flows through the system

```mermaid
flowchart TB
    subgraph IN["1 · INPUTS — what the system reads"]
        direction LR
        A1["📄 Contractor Invoices<br/><small>PDFs from the AP mailbox — any vendor, typed or scanned</small>"]
        A2["🕒 Clarity Timekeeping<br/><small>System of record for contractor hours</small>"]
        A3["🗂️ Company & Supplier Reference<br/><small>Project→company, cost centers, supplier list</small>"]
    end

    subgraph ENG["2 · THE INVOICEE ENGINE — automated pipeline, no manual keying"]
        direction LR
        S1["1. Read & Extract<br/><small>vendor, invoice #, contractor,<br/>hours, rate, work period</small>"]
        S2["2. Validate vs. Clarity<br/><small>compare invoiced hours to<br/>approved time for the exact dates</small>"]
        S3["3. Sort the Result<br/><small>reconciles → Matched<br/>discrepancy → Flagged</small>"]
        S4["4. Prepare for Coupa<br/><small>apply company, cost center<br/>& account coding</small>"]
        S1 --> S2 --> S3 --> S4
    end

    IN --> ENG

    ENG --> M["✅ MATCHED — ready to pay<br/><small>Generate Coupa CSV → Import to Coupa → Payment</small>"]
    ENG --> F["⚠️ FLAGGED — needs review<br/><small>Reviewer corrects → re-checked → moves to Matched</small>"]

    F -. "corrected & re-run" .-> ENG

    classDef green fill:#ecfdf5,stroke:#10b981,color:#065f46;
    classDef amber fill:#fffbeb,stroke:#f59e0b,color:#92400e;
    classDef ink fill:#1d1c26,stroke:#1d1c26,color:#ffffff;
    class M green;
    class F amber;
    class S1,S2,S3,S4 ink;
```

---

## What the operator sees

A single dashboard with three columns — **Flagged · Matched · All** — so every invoice is visible and
verifiable at a glance:

| Outcome | Meaning | Next step |
|---|---|---|
| 🟢 **Matched** | Billed hours reconcile to Clarity for the dates worked | One-click **Approve & Create CSV** → import to Coupa → payment |
| 🟡 **Flagged** | A name, hours, or amount doesn't match | The exact discrepancy is shown side-by-side with Clarity; reviewer corrects and re-runs |

---

## Why it matters

| | |
|---|---|
| **Faster** | Minutes of automated checking replace hours of manual reconciliation. |
| **Accurate** | Every billed hour is verified against the timekeeping system of record. |
| **Auditable** | Each invoice carries a full record of what was parsed, matched, and routed. |
| **Secure** | Runs entirely on internal data — **no third-party AI services**, and no data leaves the company. |

*Built local-first today (secure sandbox) and designed to connect directly to the mailbox, document
storage, and Coupa as it moves to production.*
