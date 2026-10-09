# Maxwell Accounting — Critical Review & Improvement Spec

**App reviewed:** `calculator.rovark.in` (Maxwell Accounting)
**Scope:** Accounting correctness, software/data design, and UX
**Evidence:** 7 screenshots (Home, Parties, Party detail/ledger, Receipts, Journal Entry, Purchases → Add Vendor, Record Payment party picker). Anything I could not see is marked *"not visible"* rather than assumed missing.
**Date:** 9 Oct 2026

> Tax/compliance points (GST, Sec. 269ST, 40A(3)) are flagged as *things to verify with your CA*, not as legal advice.

---

## 1. Executive Summary

**Verdict:** Right now this is a **party-ledger / receivables tracker**, not an accounting system. It does that one job reasonably well (the running balance in the party ledger foots correctly), but it lacks the structures that make books *auditable*: double-entry, a chart of accounts, returns/credit notes, real journal vouchers, and period reports.

**The five biggest problems**

| # | Problem | Why it matters |
|---|---------|----------------|
| 1 | **No Sales Return (Credit Note) and no Purchase Return (Debit Note)** | Returns/rate differences/short-supply claims are routine in textile trading. Today they can only be hacked in as a "journal" with no GST or stock effect. |
| 2 | **"Journal Entry" is a single-sided party adjustment**, not a journal | One party + one signed number. The other side of the entry is invisible, so books cannot balance or be audited. |
| 3 | **Numbers on screen don't reconcile** | Party card: Invoiced − Paid ≠ Due; "Unallocated" ≠ "On Account"; Home says 161 parties, Parties page says 74. Users will stop trusting the app. |
| 4 | **Purchases module is empty and isolated** (0 vendors, ₹0) | With no purchases/stock there is no COGS, no gross profit, no P&L. The app only knows the sales half of the business. |
| 5 | **Destructive actions & no audit trail visible** (red delete icon on every party card; no "created by / edited by"; raw `BUSY:…hash` IDs as narration) | Accounting records should be cancelled/reversed, never deleted. |

**What's good (keep it):** Indian number formatting (lakh/crore), clean visual style, running-balance ledger with correct arithmetic, per-party Export (Balance / Bills / Payments / PDF), outstanding statement, "On Account" badges on receipts, FY-based invoice numbering (`26-27-596`).

---

## 2. Scorecard

| Area | Score /10 | Note |
|------|-----------|------|
| Receivables tracking | 7 | Solid ledger; allocation is manual |
| Double-entry integrity | 2 | Not visible / likely absent |
| Returns & adjustments | 1 | No credit/debit notes; journal is one-sided |
| Purchases / payables | 1 | Empty shell |
| Inventory | 0 | Not visible |
| Reports (TB, P&L, BS, Day Book) | 0–1 | Not visible; only analytics bars |
| Compliance (GST, TDS) | 1 | Not visible (no GSTIN field anywhere) |
| Audit & controls | 2 | Delete buttons; no maker-checker; no period lock visible |
| Data consistency | 3 | Several mismatches (see §3) |
| UX polish | 6 | Pretty, but vocabulary and navigation are confusing |

---

## 3. Accounting Critique

### 3.1 Numbers that don't reconcile (fix first — trust issue)

| Where | What's shown | Problem |
|-------|--------------|---------|
| Home vs Parties | Home: **Parties 161**. Parties page: **74 customers / suppliers** | Two different party counts. One probably counts inactive/zero-balance or imported parties. Define it once (Active / Total) and label it. |
| Party card (Deepakbhai) | Invoiced ₹5,92,50,480 · Paid ₹3,82,26,439 · Due ₹2,04,40,729 | 5,92,50,480 − 3,82,26,439 = **₹2,10,24,041**, not ₹2,04,40,729. Gap ≈ **₹5,83,312** is unexplained (opening balance? journal adjustment? advance netting?). |
| Same party | "On Account ₹3,74,24,614" (header) vs "Unallocated Balance ₹2,38,88,864" (banner) | Two different "advance" figures for the same party. A user can't tell which is true. |
| Same party | Unpaid Bills ₹5,78,65,343 vs Invoiced ₹5,92,50,480 | OK in principle (some bills settled), but nothing explains the ₹13.85 L difference. |
| Home | Total Outstanding ₹11,60,41,663.75 vs Invoiced − Collected = ₹13,13,18,803.50 | ₹1.52 Cr gap — presumably advances/on-account netting, but not stated. |
| Home | **Overdue = 0** with ₹11.6 Cr outstanding and 2,763 invoices | Implausible unless there are no due dates. See §3.7. |

**Fix:** Every KPI needs a one-line formula in its "ⓘ" tooltip, and every party header must satisfy:

```
Closing Balance = Opening + Σ Debits − Σ Credits
Net Outstanding = Open Bills − Unallocated Advances
Open Bills + Settled Bills = Total Invoiced − Credit Notes
```

Add an automated **reconciliation check** (nightly job + a "Data health" page) that flags any party where header ≠ ledger.

### 3.2 Not a double-entry system (as far as visible)

Every screen is party-centric. There is no visible **Chart of Accounts**, **General Ledger**, **Trial Balance**, **Day Book**, **Cash Book** or **Bank Book**. "Accounts" appears as a Home quick action but I couldn't see what it opens — if it *is* the chart of accounts, it needs promoting and linking to the journal form.

**Why it matters:** Without double-entry, you can't prove books are balanced, you can't produce P&L/Balance Sheet, and any "adjustment" silently changes only one side.

**Target:** every transaction (invoice, receipt, payment, return, journal) posts to a `voucher` with ≥ 2 lines where `Σ Dr = Σ Cr`, enforced in the database.

### 3.3 Journal Entry is not a journal

Current form: `Party · Signed Amount · Date · Impact ("Increase receivable") · Description`.

| Issue | Detail |
|-------|--------|
| One-sided | Only the party ledger is affected. Where does the other leg go — Sales? Discount? Bad debts? Unknown. |
| "Signed amount" | Positive/negative is ambiguous and error-prone; accountants think in **Dr/Cr**. |
| No account selection | Cannot post Discount Allowed, Bad Debt Write-off, Round-off, Interest, Rate Difference, Commission, Freight etc. |
| No voucher number | No `JV-26-27-0001` series, so no reference for audit or reversal. |
| No preview | Doesn't show "Balance before → after". |
| No confirmation / reversal | "Post Journal Entry" is final; no draft, approval, or reverse-entry. |
| No list screen | Sidebar "Journals" opens straight into a *new entry* form — you can't see past journals. |
| Test data left in form | Amount field shows `22` pre-filled; reason field is a free-text placeholder. |
| Date format | `10/09/2026` (mm/dd/yyyy browser default) — ambiguous for Indian users (9 Oct or 10 Sep?). |

### 3.4 Missing: Sales Return / Credit Note

Currently there is no way to record goods returned by a customer, a post-sale rate/discount correction, or short-supply deductions. Today those probably go in as a negative journal or an adjusted receipt — wrong for stock, GST and reporting.

*(Full spec in §5.2.)*

### 3.5 Missing: Purchase Return / Debit Note

Same gap on the supplier/job-worker side: defective material returned to the supplier, short material found at job-work return, rate differences. *(Spec in §5.3.)*

### 3.6 Purchases module is an empty shell

* Vendors: 0 · Total Purchased ₹0 · Payable ₹0 → purchases aren't being recorded at all.
* Add Vendor has only Name/Phone/City/Notes/Type (default **KARIGAR**). Missing: GSTIN, PAN, address/state, bank details, opening balance, credit days, TDS applicability.
* Karigar (job worker) and supplier company are the same entity type here, but your own BRD treats them differently (job-worker ledger tied to the *originating supplier company*). The current form can't express that.
* No inventory/stock linkage — so no COGS and no gross margin.

### 3.7 Receivables logic: due dates, aging, allocation

* **No due date / credit days** visible → "Overdue 0" is meaningless. Add `credit_days` per party and `due_date` per invoice; show 0–30 / 31–60 / 61–90 / 90+ aging.
* **Allocation is manual** ("Settle Bills" button). Many receipts are "ON ACCT". Add: auto-allocate (FIFO by invoice date, or by specific invoice) at receipt time, with an editable allocation grid.
* **Advance vs due netting:** the party list shows one net red number. Advances are a *liability to the customer*; show gross Due and gross Advance separately, with net as a third figure.

### 3.8 Receipts / payment-mode & compliance

* Every receipt visible is **CASH**, several ≥ ₹2 L (₹4,00,000; ₹3,99,500; ₹2,00,000×2; ₹2,45,635). Either the mode isn't being captured correctly during import, or the business is receiving large cash.
* **Worth verifying with your CA:** Sec. 269ST (cash receipt ≥ ₹2 L per day/transaction/event, penalty Sec. 271DA) and Sec. 40A(3) (cash payments > ₹10,000 disallowed as expense).
* **Product fix:** capture Mode (Cash / Bank transfer / UPI / Cheque / Adjustment), bank account, UTR/cheque no., cheque date; show a soft warning when cash for one party/day reaches ₹2 L; add a bank-reconciliation screen.

### 3.9 Audit trail & controls

* **Delete** (red trash) on every party card — in an accounting system, parties with transactions must be **Archived**, never deleted.
* No "Created by / Modified by / When" shown; no immutable log.
* No **period/FY lock** visible (post-dated or back-dated edits into closed months).
* No roles beyond "Manage Users" — no maker-checker for journals, write-offs, returns.
* Ledger narration shows technical IDs: `BUSY:busy 26-27...DAT:Sale:ff9a43febf2fd1270331f04e`. That's good for traceability, bad for humans. See §4.5.
* If Maxwell is a company, the Companies (Accounts) Rules require accounting software to keep an **edit log that cannot be disabled** — verify applicability.

### 3.10 GST / TDS

Not visible anywhere: GSTIN on parties, place of supply, HSN, tax split (CGST/SGST/IGST), e-invoice/e-way bill, GSTR-1/3B export, TDS/TCS. Credit/debit notes in GST must reference the original invoice and be reported in returns (Sec. 34 CGST Act has a time limit — confirm with CA), so returns **must** be built with GST fields from day one.

### 3.11 Two sources of truth: BUSY vs this app

Ledger rows are tagged `BUSY:…` — the data is synced from BUSY. Unknown (not visible):

* Is sync one-way? If someone edits an invoice in BUSY after it's imported, what happens here?
* If a user posts a journal here, does it ever go back to BUSY?
* Are deletions in BUSY reflected?

**Decide the system of record per object** (e.g. BUSY = invoices; this app = receipts/returns/journals) and document it, otherwise the two books will drift.

---

## 4. UX Critique (screen by screen)

### 4.1 Vocabulary is inconsistent

| Place | Label | Problem |
|-------|-------|---------|
| Home | "Recent payments → Payment #112223" | These are **receipts** (money in). |
| Sidebar | "Receipts" → URL `/payments` | Same object, two names. |
| Sidebar | "New Receipt" and "New Payment" | Receipt = money in; Payment = money out — but the "Record Payment" screen opened for customers. |
| Sidebar + Home | "New Bill" (button) and "New Invoice" (quick action) | Bill vs Invoice used interchangeably. |
| Party page | "General A/C" | Unclear — rename "Journal / Adjustment". |
| Purchases | "Payments" tab | Payments to vendors, again same word as Home's "payments". |

**Rename to:** *Sales Invoice, Receipt (money in), Payment (money out), Purchase Bill, Credit Note (Sales Return), Debit Note (Purchase Return), Journal Voucher.* Match URLs to labels.

### 4.2 Home

* KPI cards show 9–10 digits (`₹11,60,41,663.75`). Use `₹11.60 Cr` with exact value on hover; drop paise on large totals.
* "0 overdue" green-safe feeling contradicts reality (see §3.7).
* **Trend chart:** no y-axis, no values, no legend (what's yellow vs green?), no tooltip; October is blank without explanation. Add Invoiced vs Collected legend, labels, and "Oct (MTD)".
* Greeting shows `raju` lowercase; use a display name.
* Dashboard is all receivables. Add: Cash/Bank balance, Payables, Stock value, This-month sales/purchase/gross profit, "Needs attention" (unallocated receipts, unposted drafts, data-health errors).
* Quick-action row repeats sidebar items; replace with context-sensitive actions (e.g. "Allocate 8 on-account receipts").

### 4.3 Parties

* **Cards are the wrong pattern** for 74–161 parties that people compare by amount. Provide a **table view** with sortable columns: Party · City · Agent · Due · Advance · Net · Last receipt · Oldest unpaid (days).
* City/market is **embedded in the name** — `(SURAT)`, `( SURAT )`, `-BARODA`, `-RICHA`, `(SAFAL-04)`, `(BHAVNAGAR)` — with inconsistent spacing/punctuation. This will create duplicates (`RAJA BHAI(SURAT)` vs `RAJU BHAI (KHOKHRA)`). Add structured **City**, **Market/Shop code**, **Agent** fields and clean names.
* "No contact info" on every card → capture phone/WhatsApp/GSTIN; enable WhatsApp statement/reminder.
* Trash icon visible on every card → replace with Archive inside the party detail, with a confirmation and a "has transactions" block.
* The floating **+** FAB overlaps the pagination area; "Page 1 of 4" is hard to see.
* Filter "All Agents" is tiny; add filters for *Has dues / Has advance / Inactive / City*.

### 4.4 Party detail

* Header card holds **six numbers** with overlapping meanings (Outstanding, Unpaid Bills, On Account, Invoiced, Paid, Due, Unallocated). Reduce to: **Gross Due · Advance · Net Outstanding** and show the rest in a collapsible "How is this calculated?".
* Ledger is newest-first with running balance — fine for browsing, but accountants expect **oldest-first with Opening and Closing balance rows** when a date range is chosen. Add a toggle.
* Date pickers use `mm/dd/yyyy`. Force **dd-mm-yyyy** app-wide.
* No search/filter within ledger by amount, voucher type or reference.
* No drill-down from a ledger row to the invoice lines / print copy (not visible).
* Buttons wrap in two rows (Edit / Export Balance / Export Bills / Export Payments / Export PDF). Move exports under one **Export ▾** menu.
* Avatar tile top-right is blank dark square.

### 4.5 Narration / references

`BUSY:busy 26-27...DAT:Sale:ff9a43febf2fd1270331f04e` is shown on every row. Show a human narration (`Sale Invoice 26-27-596 — 27 Sep 2026`) and tuck the sync ID behind an ⓘ or "Source" column.

### 4.6 Receipts list

* 1,816 receipts across **91 pages**. Add page-size, infinite scroll or virtualised table; filter by mode, amount range, allocated/on-account, and party (not just name search).
* Receipt numbers `PMT-112204` carry no FY or series, unlike invoices (`26-27-544`). Use `RC-26-27-00001`.
* Show **Allocated / Unallocated** split on each card, not just an "ON ACCT" chip.
* Add column totals for the filtered result (the "Total" in the top-right looks all-time, not filtered).
* No print/PDF receipt, no export from this screen (not visible).

### 4.7 Journal Entry

*(See §3.3.)* UX additions: show a **before → after** balance preview, Dr/Cr toggle instead of signed numbers, past-journal list with filters, reverse button.

### 4.8 Purchases & Add Vendor modal

* Empty state doesn't tell the user what to do first (the modal opens over a blank page).
* `TYPE: KARIGAR` as default for every new vendor is risky; force a deliberate choice (Supplier / Karigar-Job worker / Transporter / Other).
* Phone placeholder shows a sample number — fine, but add validation.
* No required GSTIN/state for suppliers.

### 4.9 Party picker (Record Payment)

* Alphabetical list dominated by **Due: ₹0** parties — noise. Default to *parties with dues or advances*, with a "Show all" toggle; recent parties on top.
* Show Due **and** Advance; highlight best match as user types.
* Tiny scrollbar and no keyboard navigation hint; support ↑/↓/Enter.

### 4.10 Visual / accessibility

* Many labels are ~10–11 px light grey on cream — low contrast. Minimum 12–13 px and WCAG AA (4.5:1).
* Colour-only meaning (red = due, green = adv) — add ▲/▼ or text labels.
* Dashed underlines + ⓘ icons on numbers are inconsistent (some have them, some don't).

---

## 5. Proposed Improvements

### 5.1 Core data model (minimum viable double-entry)

```sql
accounts(id, code, name, type  -- ASSET/LIAB/INCOME/EXPENSE/EQUITY
        , parent_id, is_party_control bool, is_system bool, active)

parties(id, name, city, market_code, agent_id, gstin, pan, state_code,
        phone, whatsapp, credit_days, credit_limit NULL, party_type, archived_at)

vouchers(id, voucher_type,         -- SALE, RECEIPT, PURCHASE, PAYMENT,
                                   -- CREDIT_NOTE, DEBIT_NOTE, JOURNAL, CONTRA
         series, number, voucher_date, fy, narration,
         ref_voucher_id NULL,      -- original invoice for returns
         status,                   -- DRAFT / POSTED / CANCELLED / REVERSED
         created_by, created_at, approved_by, posted_at,
         reversed_by_voucher_id NULL, source, source_ref)  -- source='BUSY'

voucher_lines(id, voucher_id, account_id, party_id NULL,
              debit numeric(14,2), credit numeric(14,2),
              item_id NULL, qty NULL, rate NULL, tax_code NULL, line_narration)
-- CHECK (debit = 0 OR credit = 0)
-- TRIGGER on post: SUM(debit) = SUM(credit) per voucher

allocations(id, receipt_line_id, invoice_voucher_id, amount)  -- bill-by-bill
stock_ledger(id, item_id, godown_id, voucher_id, qty_in, qty_out, rate)
audit_log(id, entity, entity_id, action, before_json, after_json, user_id, at)
period_locks(fy, month, locked_by, locked_at)
```

**Rules:** posted vouchers are immutable; corrections are done by *Reverse* + *Re-enter*; archived (not deleted) masters; period-locked months reject postings.

### 5.2 Sales Return / Credit Note — specification

**Entry points:** Party page → *New Credit Note*; Invoice view → *Return / Credit*; Sidebar → *Credit Notes*.

**Types:** (a) Goods return, (b) Rate / discount difference, (c) Short supply / quality claim, (d) Cancellation.

**Form**

```
Credit Note No: CN-26-27-0001 (auto)         Date: [dd-mm-yyyy]
Party: [ search ]                            Against Invoice: [ 26-27-596 ▾ ] (optional but recommended)
Reason: [Goods return | Rate diff | Short supply | Quality | Other]
Lines (pre-filled from invoice; editable qty ≤ invoiced − already returned):
  Item | HSN | Invoiced Qty | Return Qty | Rate | Taxable | GST% | Tax | Total
Return to stock?  [Yes → Godown ▾ ] [No → Damaged/Scrap ▾]
Settlement:  ( ) Reduce outstanding on this invoice
             ( ) Keep as party credit (adjust later)
             ( ) Refund now (creates Payment)
Narration / Attachment (photos, LR copy)           [Save Draft] [Post]
```

**Accounting entry (goods return, with GST, perpetual stock):**

| Dr / Cr | Account | Amount |
|---|---|---|
| Dr | Sales Returns (contra-income) | Taxable value |
| Dr | Output CGST + SGST (or IGST) | Tax |
| Cr | Customer (party A/R) | Total |
| Dr | Stock / Inventory | Cost value of returned goods |
| Cr | Cost of Goods Sold | Cost value of returned goods |

*(Rate/discount-difference credit note: only the first three lines — no stock lines.)*

**Validations:** return qty ≤ remaining returnable qty; cannot exceed invoice value; original invoice must be posted; period must be open; requires approval above a threshold; cannot be deleted — only *Cancel* with reason.
**Side effects:** party ledger credit, invoice open-amount reduced, stock increased, GST report picks it up, appears on Outstanding Statement.
**Print:** Credit Note PDF with original-invoice reference.

### 5.3 Purchase Return / Debit Note — specification

**Entry points:** Vendor page → *New Debit Note*; Purchase bill → *Return*; Job-work receipt → *Short/Reject*.

**Form** (mirror of §5.2): `DN-26-27-0001`, vendor, against purchase bill, reason (Defective / Excess / Wrong item / Rate diff / Short from job-work), lines, return-from godown, settlement (reduce payable / keep as vendor credit / refund received).

**Accounting entry (goods return, with GST):**

| Dr / Cr | Account | Amount |
|---|---|---|
| Dr | Vendor (party A/P) | Total |
| Cr | Purchase Returns (contra-expense) | Taxable value |
| Cr | Input CGST + SGST (or IGST) | Tax (ITC reversal) |
| Dr | *(stock side)* | Stock decrease at purchase cost |

**Maxwell-specific:** because material flows *supplier → job worker → back → cut*, a debit note must be able to point to the **lot / packing lineage** (your BRD problem). Store `lot_id` on the line so a rejected quantity at the karigar can be debited to the right supplier and credited to the right job-worker account.

### 5.4 Real Journal Voucher — specification

**List screen** (new): Voucher No · Date · Type · Narration · Total · Status · Created by · ⟲ Reverse.

**New Journal form**

```
Voucher: JV-26-27-0001 (auto)    Date: [dd-mm-yyyy]    Type: [General | Adjustment | Opening | Write-off | Reversal]
Narration*: [ ........................ ]     Attachment: [ + ]
┌────────────────────────────┬───────────────┬──────────────┬──────────────┬──────────────┐
│ Account                    │ Party (if A/R)│ Debit (₹)    │ Credit (₹)   │ Line note    │
├────────────────────────────┼───────────────┼──────────────┼──────────────┼──────────────┤
│ Discount Allowed           │ —             │ 5,000.00     │              │              │
│ Sundry Debtors (control)   │ AMAR BHAI     │              │ 5,000.00     │              │
└────────────────────────────┴───────────────┴──────────────┴──────────────┴──────────────┘
Total Dr 5,000.00   Total Cr 5,000.00   ✓ Balanced     Impact: AMAR BHAI ₹X → ₹X−5,000
[Save Draft]  [Submit for approval]  [Post]
```

* Post is **disabled until Dr = Cr**.
* "Party" column appears only if the selected account is a debtor/creditor control account.
* **Quick templates** (keeps the current simplicity, but correct underneath):

| Template | Dr | Cr |
|---|---|---|
| Discount allowed | Discount Allowed | Party |
| Bad debt write-off | Bad Debts | Party |
| Rate/price difference | Sales / Sales Returns | Party |
| Interest charged on late payment | Party | Interest Income |
| Round-off | Round-off | Party |
| Transfer balance between parties | Party B | Party A |
| Reverse a voucher | Auto-swapped Dr/Cr of original | |

* **Reverse** creates a new posted voucher with opposite entries and links both; the original is marked REVERSED, never edited.
* Write-offs and entries > threshold require a second user's approval.

### 5.5 Receipt & Payment flow upgrade

1. Pick party → show **open invoices** (oldest first) + existing advance.
2. Enter amount + mode (Cash/Bank/UPI/Cheque) + reference.
3. **Auto-allocate FIFO** (editable grid). Remainder → "Advance / On Account".
4. Show compliance hint for cash.
5. Post → generate receipt PDF / WhatsApp link.

### 5.6 Reports to add (priority order)

1. **Day Book / Cash Book / Bank Book**
2. **Trial Balance** (this is also your integrity test — must always tally)
3. **Outstanding Aging** (party-wise, agent-wise)
4. **Sales Register, Sales Return Register, Purchase Register, Purchase Return Register**
5. **Profit & Loss** and **Balance Sheet**
6. **GST:** GSTR-1 / 3B working sheets, HSN summary, credit/debit-note register
7. **Stock Summary / Stock Ledger**
8. **Data Health** (header-vs-ledger mismatches, unbalanced vouchers, orphan receipts)

### 5.7 Safeguards

* Archive instead of delete; "cancel with reason" for vouchers.
* Immutable audit log, visible per voucher ("History" tab).
* FY/month lock.
* Roles: *Owner, Accountant, Sales-entry, Viewer*; money visibility must respect your earlier rule (**dispatcher/coordinator never see ₹ values**).
* Daily DB backup + export of all vouchers to Excel/Tally-XML/BUSY-compatible format.

---

## 6. Roadmap

| Phase | Items | Outcome |
|-------|-------|---------|
| **P0 – Trust (1–2 wks)** | Fix KPI mismatches (§3.1); single party count; reconcile header vs ledger; dd-mm-yyyy; replace delete with archive; rename Payment/Receipt/Bill/Invoice consistently; hide BUSY hashes | Numbers can be believed |
| **P1 – Accounting core (3–5 wks)** | Chart of accounts; `vouchers`+`voucher_lines`; real Journal Voucher + list + reverse; **Sales Return (Credit Note)**; **Purchase Return (Debit Note)**; audit log; period lock | Books balance; returns possible |
| **P2 – Payables & stock (3–4 wks)** | Complete Purchases (bills, payments, vendor GSTIN/opening balance); item master → stock ledger; COGS on sale/return; lot lineage for job-work | Gross profit; supplier side |
| **P3 – Reports & compliance (3–4 wks)** | Trial Balance, Day/Cash/Bank Book, Aging, P&L, BS, GST sheets, bank reconciliation, cash-limit warnings | Close-the-month capability |
| **P4 – Polish** | Table-view parties, WhatsApp reminders/statements, role-based views, better dashboard & charts, accessibility pass | Daily-use delight |

---

## 7. Acceptance Tests (copy into your QA list)

1. Post a journal with Dr ≠ Cr → **blocked**.
2. Post a Credit Note against an invoice for 3 of 10 units → party balance ↓, stock ↑ 3, GST output ↓, invoice open amount ↓; a second credit note for 8 units → **blocked** (only 7 returnable).
3. Post a Debit Note → vendor payable ↓, input GST reversed, stock ↓.
4. Reverse a posted journal → both vouchers linked; Trial Balance unchanged net.
5. For **every** party: `Invoiced − CreditNotes − Paid ± Journals + Opening = Closing = ledger last balance = Due`.
6. Home Parties count = Parties-page count.
7. Edit/delete in a locked period → **rejected** with message.
8. Archive a party with transactions → allowed; **delete** → rejected.
9. Cash receipts ≥ ₹2,00,000 from one party in a day → warning shown.
10. Trial Balance total Dr = total Cr at any date.

---

## 8. Open Questions

1. Is the app meant to **replace BUSY** or sit beside it? Who is the system of record for invoices vs receipts vs returns?
2. Is Maxwell a company, LLP, or proprietorship (affects audit-trail and reporting rules)?
3. Are you GST-registered and issuing e-invoices from BUSY today?
4. What does "Accounts" (Home quick action) open?
5. Do job-worker (karigar) payments need TDS (e.g. Sec. 194C) handling?
6. Who are the user roles, and what should each be allowed to see/post?
7. Is the 161 vs 74 party discrepancy from imports of inactive/duplicate parties?

---

*Limitations: this review is based on seven screenshots; screens not shown (Invoices, Addresses, Accounts, Analytics, Pending Dues, Manage Users) may already contain some of the missing features. Share those and I'll refine the review.*
