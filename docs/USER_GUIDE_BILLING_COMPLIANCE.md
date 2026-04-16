# User Guide: Billing & Compliance

**ORGON Platform - Phase 2**  
**Last Updated:** 2026-02-12  
**For:** Organization Administrators & Compliance Officers

---

## Table of Contents

1. [Introduction](#introduction)
2. [Billing Management](#billing-management)
3. [Compliance Management](#compliance-management)
4. [Best Practices](#best-practices)
5. [Troubleshooting](#troubleshooting)

---

## Introduction

This guide covers the Billing and Compliance features introduced in ORGON Phase 2. These features enable organizations to:

- **Billing:**
  - Subscribe to service plans
  - Manage subscriptions (upgrade/downgrade/cancel)
  - View and pay invoices
  - Track transaction fees

- **Compliance:**
  - Submit and verify KYC records
  - Monitor AML alerts
  - Generate compliance reports for regulators
  - Manage sanctioned address blocklists

---

## Billing Management

### Getting Started with Billing

#### 1. View Available Plans

1. Navigate to **Settings → Billing** in the sidebar
2. Click **"View Plans"** or **"Upgrade Plan"**
3. Compare available plans:
   - **Starter** ($99/month) - For small exchanges
   - **Professional** ($299/month) - For growing exchanges
   - **Enterprise** ($999/month) - For large exchanges

Each plan includes:
- Max users
- Max wallets
- Monthly transaction limits
- Feature access (analytics, custom branding, white-label)
- 14-day free trial (Starter/Professional) or 30-day (Enterprise)

---

#### 2. Subscribe to a Plan

**Steps:**
1. Click **"Select Plan"** on your chosen plan
2. Choose billing cycle: **Monthly** or **Yearly** (2 months free)
3. Review subscription details
4. Click **"Start Free Trial"**
5. Confirmation: "Trial started - ends in 14 days"

**What Happens:**
- Trial period begins immediately
- No payment required during trial
- Full access to plan features
- First invoice generated after trial ends

---

#### 3. Manage Subscription

Navigate to **Billing → Subscription** to:

**View Current Subscription:**
- Plan name & pricing
- Status (Trial / Active / Past Due / Cancelled)
- Current billing period
- Next billing date
- Usage this month (users, wallets, transactions)

**Upgrade/Downgrade Plan:**
1. Click **"Change Plan"**
2. Select new plan
3. Review prorated charges (if upgrading mid-cycle)
4. Click **"Confirm Change"**
5. Invoice generated for price difference (if applicable)

**Cancel Subscription:**
1. Click **"Cancel Subscription"**
2. Choose:
   - **Cancel at end of period** (access until current period ends)
   - **Cancel immediately** (access ends now, may receive prorated refund)
3. Optional: Provide cancellation reason
4. Click **"Confirm Cancellation"**

---

### Invoices & Payments

#### View Invoices

Navigate to **Billing → Invoices**

**Invoice List shows:**
- Invoice number (INV-2026-001234)
- Issue date
- Due date
- Amount
- Status badge (Open / Paid / Void)

**Click invoice** to view details:
- Line items (subscription fee, transaction fees, one-time charges)
- Subtotal, tax, discount, total
- Payment status
- PDF download button

---

#### Pay an Invoice

**For Open Invoices:**
1. Click **"Pay Now"** button
2. Select payment method:
   - Credit/Debit Card (Stripe)
   - Bank Transfer (manual)
   - Crypto (if enabled)
3. Enter payment details
4. Click **"Submit Payment"**
5. Confirmation: "Payment successful - Invoice #INV-2026-001234 paid"

**Auto-pay (if enabled):**
- Invoices are automatically charged to saved payment method
- Email notification sent after successful payment

---

### Transaction Fees

Navigate to **Billing → Fees**

**Fee Dashboard:**
- Total fees this month
- Fees by type (Withdrawal / Exchange / Deposit / Transfer)
- Pending fees (not yet invoiced)
- Paid fees

**Fee Schedule:**
Default rates (configurable per org):
- Withdrawal: 2.5%
- Exchange: 0.5%
- Deposit: 0% (free)
- Transfer: 1.0%

**How Fees Work:**
1. Transaction executed (e.g., customer withdraws $1,000)
2. Fee calculated (2.5% = $25)
3. Fee recorded in system (status: pending)
4. End of month: Fees added to invoice (status: invoiced)
5. Invoice paid: Fees marked as paid

---

## Compliance Management

### KYC (Know Your Customer)

#### Submit KYC Record

Navigate to **Compliance → KYC → Add Customer**

**Required Information:**
- Customer ID (your internal ID)
- Full Name
- Email
- Phone number
- Date of Birth
- Nationality
- Address

**Documents to Upload:**
- Government ID (passport, national ID, driver's license)
- Address Proof (utility bill, bank statement < 3 months old)
- Selfie with ID (optional, depends on risk level)

**Steps:**
1. Fill in customer information
2. Upload documents
3. Click **"Submit for Verification"**
4. Status: **Pending** (awaiting review)

---

#### KYC Verification Process

**Status Flow:**
```
Pending → In Review → Approved/Rejected
```

**Pending:**
- Documents submitted, awaiting compliance officer review

**In Review:**
- Compliance officer reviewing documents
- May request additional documents

**Approved:**
- Customer verified (risk level: Low/Medium/High)
- Customer can proceed with high-value transactions
- Verification valid for 1 year (then expires)

**Rejected:**
- Documents insufficient or suspicious
- Reason provided
- Customer cannot proceed (can resubmit with better documents)

---

#### Manage KYC Records

Navigate to **Compliance → KYC**

**KYC Dashboard:**
- Total KYC records
- Pending verification count
- Approved count
- Rejected count
- Expiring soon (< 30 days)

**Filter & Search:**
- By status (Pending / Approved / Rejected / Expired)
- By risk level (Low / Medium / High)
- By customer name/email

**Actions:**
- **View Details:** See all customer info & documents
- **Approve:** Mark as verified (requires compliance officer role)
- **Reject:** Mark as rejected with reason
- **Request More Info:** Email customer for additional documents

---

### AML (Anti-Money Laundering)

#### AML Alerts

Navigate to **Compliance → AML Alerts**

**Alert Types:**
- **High Value Transaction:** Transaction exceeds threshold ($10K default)
- **Rapid Movement:** Multiple transactions in short time (>10/hour)
- **Sanctioned Address:** Transaction involves blocklisted address
- **Suspicious Pattern:** Unusual transaction behavior detected

**Severity Levels:**
- **Low:** Minor concern, monitor
- **Medium:** Investigate within 24 hours
- **High:** Investigate immediately
- **Critical:** Block transaction, escalate to regulator

---

#### Handle AML Alerts

**Alert Flow:**
```
Open → Investigating → Resolved/Escalated
```

**Steps:**
1. Click alert to view details
2. Review transaction history, customer profile, risk factors
3. Click **"Start Investigation"**
4. Add investigation notes
5. Decision:
   - **False Positive:** Legitimate transaction, mark resolved
   - **Legitimate Concern:** Suspicious, file SAR (Suspicious Activity Report)
   - **Escalate:** Report to regulator immediately

**For Sanctioned Addresses:**
- Transaction automatically blocked
- No manual investigation needed
- Alert created for audit trail

---

### Compliance Reports

Navigate to **Compliance → Reports**

**Report Types:**
- **Monthly Transactions:** Summary of all transactions (for regulator)
- **KYC Summary:** All KYC verifications this period
- **AML Alerts:** All alerts and resolutions
- **Suspicious Activity Report (SAR):** High-risk transactions
- **Tax Report:** Transaction volume for tax purposes

---

#### Generate a Report

**Steps:**
1. Click **"Generate Report"**
2. Select report type
3. Select period (start date, end date)
4. Select export format:
   - **PDF:** For printing/emailing
   - **Excel:** For analysis
   - **XML:** For regulatory API submission
5. Click **"Generate"**
6. Wait 10-30 seconds (depending on data volume)
7. Click **"Download"** when ready

**Report Contents:**
- Organization details
- Period covered
- Transaction summary (count, volume, averages)
- KYC statistics
- AML alert summary
- Risk assessment
- Compliance officer attestation

---

#### Submit Report to Regulator

**Manual Submission:**
1. Download report (PDF or XML)
2. Visit regulator portal (e.g., National Bank of Kyrgyzstan)
3. Upload report
4. In ORGON, click **"Mark as Submitted"**
5. Enter submission date & reference number

**Automatic Submission (Future):**
- Connect ORGON to regulator API
- One-click submission
- Automatic confirmation

---

### Sanctioned Addresses

Navigate to **Compliance → Sanctioned Addresses**

**Purpose:**
Block transactions to/from addresses associated with:
- Terrorism financing
- Money laundering
- Fraud
- Mixers/Tumblers
- Darknet markets

**Sources:**
- OFAC (US Treasury)
- Chainalysis
- Local regulator (National Bank of KR)
- Manual additions by compliance officer

**How It Works:**
1. Customer initiates transaction
2. ORGON checks recipient address against blocklist
3. If match: Transaction blocked, AML alert created (Critical severity)
4. Customer notified: "Transaction blocked - sanctioned address"

**Add Sanctioned Address:**
1. Navigate to **Compliance → Sanctioned Addresses → Add**
2. Enter blockchain address
3. Select blockchain (Ethereum, Bitcoin, etc.)
4. Select sanction type
5. Provide reason
6. Click **"Add to Blocklist"**

---

## Best Practices

### Billing

**1. Choose the Right Plan:**
- Start with Starter for testing
- Upgrade to Professional when you hit limits (users/wallets/transactions)
- Enterprise only if you need white-label or unlimited resources

**2. Save with Yearly Billing:**
- Yearly plans = 2 months free (save 17%)
- More predictable budgeting

**3. Monitor Usage:**
- Check Billing Dashboard regularly
- Upgrade before hitting limits (to avoid service disruption)

**4. Enable Auto-pay:**
- Avoid service interruption from missed payments
- Save time (no manual invoice payments)

**5. Review Invoices:**
- Check line items for unexpected charges
- Contact support if discrepancies

---

### Compliance

**1. KYC Early & Often:**
- Verify new customers immediately (don't wait for high-value transaction)
- Re-verify yearly (documents expire)
- Use KYC provider integration for faster verification (Onfido, Jumio)

**2. Respond to AML Alerts Quickly:**
- High severity: Investigate within 1 hour
- Medium severity: Investigate within 24 hours
- Don't ignore Low severity (trends may emerge)

**3. Monthly Report Routine:**
- Generate report on 1st of month (for previous month)
- Review before submitting to regulator
- Keep local copy for 5 years (legal requirement)

**4. Update Sanctioned Lists:**
- Check OFAC/Chainalysis monthly for updates
- Subscribe to automatic updates (when available)

**5. Train Staff:**
- Compliance officers: Full KYC/AML training
- Support staff: Basic KYC document requirements
- All staff: Sanctioned address policy

**6. Document Everything:**
- Investigation notes for every AML alert
- Rejection reasons for KYC
- Audit trail = legal protection

---

## Troubleshooting

### Billing Issues

#### "Payment Failed"
**Causes:**
- Insufficient funds
- Card declined
- Expired card
- Bank fraud protection

**Solutions:**
1. Check card details (number, expiry, CVV)
2. Try different card
3. Contact your bank
4. Use manual bank transfer if card doesn't work

---

#### "Subscription Cancelled Unexpectedly"
**Causes:**
- Multiple failed payments (3 attempts)
- Manual cancellation by admin

**Solutions:**
1. Check payment method
2. Review invoice payment history
3. Contact support to restore subscription
4. Update payment method before retrying

---

#### "Invoice Not Generated"
**Causes:**
- Subscription in trial (no invoices during trial)
- Payment method on file (auto-pay succeeded, no open invoice)
- System error (rare)

**Solutions:**
1. Check subscription status
2. Check "Paid Invoices" section (may already be paid)
3. Contact support if subscription active but no invoice for >1 month

---

### Compliance Issues

#### "KYC Stuck in Pending"
**Causes:**
- High volume (compliance officer backlog)
- Documents unclear (need better quality)

**Solutions:**
1. Wait 24-48 hours for initial review
2. Check email for document requests
3. Re-upload higher quality documents if requested
4. Contact compliance team if >3 days

---

#### "False Positive AML Alerts"
**Causes:**
- Conservative thresholds (default $10K)
- Legitimate high-value customer

**Solutions:**
1. Investigate and mark as false positive (add notes)
2. Adjust thresholds in Transaction Monitoring Rules
3. Whitelist known legitimate high-volume customers (custom rule)

---

#### "Cannot Download Report"
**Causes:**
- Report still generating (large data volume)
- Browser popup blocker

**Solutions:**
1. Wait 1-2 minutes, refresh page
2. Disable popup blocker for ORGON domain
3. Try different browser
4. Contact support for direct email delivery

---

## Getting Help

### Support Channels

**Documentation:**
- [API Reference](./API_BILLING_COMPLIANCE.md)
- [Architecture Guide](./ARCHITECTURE.md)
- [FAQ](./FAQ.md)

**Contact:**
- **Email:** support@orgon.example.com
- **Priority Support:** Available for Professional & Enterprise plans
- **24/7 Support:** Available for Enterprise plans

**Response Times:**
- Starter: 48 hours
- Professional: 24 hours (priority)
- Enterprise: 2 hours (24/7)

---

## Appendix

### Glossary

**Billing Terms:**
- **Subscription:** Recurring payment for service plan
- **Invoice:** Bill for charges (subscription + fees)
- **Prorated:** Partial charge for mid-cycle plan changes
- **Trial Period:** Free access for 14-30 days

**Compliance Terms:**
- **KYC:** Know Your Customer (identity verification)
- **AML:** Anti-Money Laundering (transaction monitoring)
- **SAR:** Suspicious Activity Report (to regulator)
- **OFAC:** Office of Foreign Assets Control (US sanctions list)
- **PEP:** Politically Exposed Person (high-risk customer type)
- **Sanctioned Address:** Blocklisted crypto address

---

### Legal & Regulatory

**Kyrgyzstan Crypto Regulations:**
- Law on Virtual Assets (2024)
- National Bank of Kyrgyzstan oversight
- Mandatory KYC for transactions > $1,000
- AML reporting requirements

**Data Privacy:**
- Customer data encrypted at rest and in transit
- GDPR-compliant (for EU customers)
- Data retention: 5 years (legal requirement)

**Liability:**
- Organization responsible for compliance
- ORGON provides tools, not legal advice
- Consult legal counsel for complex cases

---

**Document Version:** 2.0  
**Last Updated:** 2026-02-12  
**Next Review:** 2026-03-12
