# Multi-Tenant Monetization Platform - Requirements

## Overview

Build a closed-source SaaS layer on top of the open-source VibeJudge core to enable managed hosting, Stripe payment processing, subscription management, usage-based billing, and customer self-service. The open-source code remains free for self-hosting while the managed service (vibejudge.ai) provides a paid, turnkey solution.

## Goals

- Enable customers to use VibeJudge without AWS accounts or technical expertise
- Implement Stripe for payment processing and subscription management
- Support multiple pricing models: pay-as-you-go, tiered plans, enterprise custom
- Track usage accurately for metered billing (per submission)
- Provide customer self-service portal for signup, billing, and usage analytics
- Maintain tenant isolation (customer A cannot access customer B's data)
- Achieve 37%+ profit margin ($0.10 revenue - $0.063 AWS cost - $0.01 Stripe fee)
- Keep open-source core separate from proprietary billing/multi-tenancy code

## Non-Goals

- Replacing the open-source version (both coexist)
- Complex enterprise features (SSO, SAML, Active Directory) in v1
- Marketplace for custom agents (future enhancement)
- Affiliate/referral program (future growth strategy)
- Free tier abuse prevention (rate limiting handles this)

---

## Requirements

### Requirement 1: Tenant Data Model

**User Story:** As a platform architect, I want a clear tenant data model that ensures isolation and supports multi-tenancy.

**Acceptance Criteria:**
1.1. DynamoDB table: customers with schema {tenant_id, email, name, stripe_customer_id, subscription_status, plan, created_at}
1.2. Each tenant_id maps to unique AWS resources (API keys, hackathons, submissions)
1.3. All DynamoDB queries include tenant_id in partition key to enforce isolation
1.4. Tenant deletion removes all associated data (hackathons, submissions, API keys)
1.5. Tenant schema includes: features (white_label, custom_rubrics), limits (max_hackathons, max_submissions_per_month)
1.6. Tenant metadata tracks: signup_source, referral_code, customer_success_manager
1.7. Tenant status includes: active, suspended, churned, trialing

### Requirement 2: Stripe Customer Creation

**User Story:** As a new customer, I want to sign up and start using VibeJudge in under 5 minutes.

**Acceptance Criteria:**
2.1. Signup form collects: email, name, company name, password
2.2. Stripe customer created via API: stripe.Customer.create() with metadata {tenant_id, signup_date}
2.3. Customer stored in DynamoDB with stripe_customer_id reference
2.4. Welcome email sent with API key and quickstart guide
2.5. Default plan is "Starter" with 14-day free trial
2.6. Trial period starts immediately (no payment method required upfront)
2.7. Signup flow completes in <30 seconds

### Requirement 3: Stripe Checkout Integration

**User Story:** As a customer, I want a secure payment flow using Stripe Checkout without storing card details.

**Acceptance Criteria:**
3.1. Checkout session created via stripe.checkout.Session.create()
3.2. Checkout mode: "subscription" for recurring billing
3.3. Success URL redirects to dashboard with session_id parameter
3.4. Cancel URL returns to pricing page
3.5. Checkout pre-fills customer email from signup
3.6. Checkout supports multiple payment methods: card, ACH, SEPA
3.7. Checkout includes 14-day trial period (no immediate charge)

### Requirement 4: Subscription Plans (Stripe Products)

**User Story:** As a business owner, I want multiple pricing tiers to serve different customer segments.

**Acceptance Criteria:**
4.1. Stripe products created: "VibeJudge Starter", "VibeJudge Professional", "VibeJudge Enterprise"
4.2. Starter Plan: $0.10 per submission (metered billing), no base fee
4.3. Professional Plan: $200/month base + $0.05 per submission (hybrid)
4.4. Enterprise Plan: Custom pricing (contact sales), invoiced quarterly
4.5. All plans include: unlimited hackathons, API access, email support
4.6. Professional adds: white-label branding, priority support, custom rubrics
4.7. Enterprise adds: dedicated account manager, SLA, on-premise option

### Requirement 5: Usage Metering and Reporting to Stripe

**User Story:** As a billing system, I want to accurately report usage to Stripe for metered billing.

**Acceptance Criteria:**
5.1. After each successful submission analysis, call stripe.SubscriptionItem.create_usage_record()
5.2. Usage record includes: quantity=1, timestamp=unix_time, action="increment"
5.3. Usage tracked per billing period (monthly)
5.4. Failed analyses NOT reported to Stripe (customer not charged)
5.5. Usage idempotency key prevents duplicate charges (submission_id as key)
5.6. Usage records sent within 1 minute of analysis completion
5.7. Retry logic handles Stripe API failures (exponential backoff, max 3 retries)

### Requirement 6: Stripe Webhook Handling

**User Story:** As a platform operator, I want to respond to subscription lifecycle events from Stripe.

**Acceptance Criteria:**
6.1. Webhook endpoint: POST /webhooks/stripe verifies signature with stripe.Webhook.construct_event()
6.2. Event customer.subscription.created activates tenant account
6.3. Event customer.subscription.updated syncs plan changes to DynamoDB
6.4. Event customer.subscription.deleted suspends tenant account (soft delete)
6.5. Event invoice.payment_succeeded updates tenant last_payment_date
6.6. Event invoice.payment_failed sends dunning email and suspends after 3 failures
6.7. All webhook events logged to CloudWatch with event type and tenant_id

### Requirement 7: Tenant Isolation Middleware

**User Story:** As a security engineer, I want to ensure customers cannot access each other's data.

**Acceptance Criteria:**
7.1. Lambda middleware extracts tenant_id from API key before calling core functions
7.2. All DynamoDB queries scoped to tenant_id partition key
7.3. API key from Tenant A attempting to access Tenant B's hackathon returns 403 Forbidden
7.4. CloudWatch logs include tenant_id for audit trail
7.5. Cross-tenant data leakage tests run in E2E test suite
7.6. Tenant isolation enforced at database layer (not just API layer)
7.7. Admin API keys have cross-tenant read access (for support, not exposed to customers)

### Requirement 8: Customer Dashboard (Self-Service Portal)

**User Story:** As a customer, I want a dashboard to view usage, manage billing, and monitor costs.

**Acceptance Criteria:**
8.1. Dashboard shows current month usage: submissions analyzed, cost incurred
8.2. Dashboard shows historical usage: chart of submissions per day (last 30 days)
8.3. Dashboard shows current plan and limits: quota remaining, overage rate
8.4. Dashboard has "Manage Billing" button opening Stripe Customer Portal
8.5. Dashboard shows next invoice date and estimated amount
8.6. Dashboard allows plan upgrades/downgrades with prorated billing
8.7. Dashboard shows API key management (create, revoke, rotate)

### Requirement 9: Stripe Customer Portal

**User Story:** As a customer, I want to manage my subscription and payment methods without contacting support.

**Acceptance Criteria:**
9.1. Portal session created via stripe.billing_portal.Session.create()
9.2. Portal allows: update payment method, view invoices, download receipts
9.3. Portal allows plan changes: upgrade, downgrade, cancel
9.4. Portal shows usage history and upcoming charges
9.5. Return URL redirects back to dashboard after portal session
9.6. Portal configuration allows cancellation with immediate effect (no retention flow initially)
9.7. Portal accessible via "Manage Billing" button in dashboard

### Requirement 10: Usage Tracking and Cost Attribution

**User Story:** As a platform operator, I want to track AWS costs per tenant for margin analysis.

**Acceptance Criteria:**
10.1. DynamoDB table: usage_events with schema {tenant_id, timestamp, submission_id, aws_cost_usd, charged_amount_usd, margin_usd}
10.2. After each analysis, record: actual Bedrock cost, amount charged to customer
10.3. Margin calculation: charged_amount - aws_cost - stripe_fee (0.029 + $0.30)
10.4. Dashboard endpoint: GET /admin/margins returns {total_revenue, total_aws_cost, total_stripe_fees, net_margin}
10.5. Alerts trigger if margin <20% for any tenant (indicates cost overrun)
10.6. Cost attribution includes: Bedrock, Lambda, DynamoDB, API Gateway, Step Functions
10.7. Monthly report exports to CSV: {tenant_id, submissions, revenue, costs, margin}

### Requirement 11: Plan Upgrade/Downgrade Flows

**User Story:** As a customer, I want to upgrade or downgrade my plan without losing data or service.

**Acceptance Criteria:**
11.1. Upgrade applies immediately with prorated charge for remaining billing period
11.2. Downgrade applies at next billing cycle (no refund for current period)
11.3. Plan change updates Stripe subscription via stripe.Subscription.modify()
11.4. Plan change syncs to DynamoDB customers table
11.5. Feature access changes immediately on upgrade (e.g., white-label enabled)
11.6. Downgrade preview shows: new limits, overage charges, savings
11.7. Email confirmation sent after plan change

### Requirement 12: Free Trial Management

**User Story:** As a growth marketer, I want to offer 14-day free trials to reduce signup friction.

**Acceptance Criteria:**
12.1. Trial period set via subscription_data.trial_period_days=14
12.2. Trial starts immediately on signup (no payment method required)
12.3. Trial countdown visible in dashboard: "X days remaining in trial"
12.4. Email reminders sent: 7 days before trial ends, 1 day before
12.5. After trial ends, Stripe auto-charges saved payment method
12.6. If no payment method saved, subscription moves to "incomplete" status
12.7. Incomplete subscriptions suspended after 3 days (soft delete, can reactivate)

### Requirement 13: Invoice Generation and Delivery

**User Story:** As a customer, I want detailed invoices showing usage breakdown for accounting.

**Acceptance Criteria:**
13.1. Stripe auto-generates invoices at end of billing period
13.2. Invoice line items show: base subscription fee, usage charges (X submissions @ $Y each)
13.3. Invoice metadata includes: tenant_id, billing_period_start, billing_period_end
13.4. Invoices emailed to customer automatically by Stripe
13.5. Invoices available in Customer Portal for download
13.6. Invoice webhook (invoice.finalized) triggers internal accounting sync
13.7. Failed payment invoices trigger dunning workflow (3 retry attempts over 7 days)

### Requirement 14: Multi-Tenant Gateway Lambda

**User Story:** As a platform architect, I want a thin gateway layer that wraps open-source core with billing logic.

**Acceptance Criteria:**
14.1. Gateway Lambda validates API key and extracts tenant_id
14.2. Gateway Lambda checks subscription status (active/trialing/suspended)
14.3. Gateway Lambda enforces plan limits (quota, rate limits)
14.4. Gateway Lambda calls open-source core Lambda as Lambda layer or invocation
14.5. Gateway Lambda tracks usage and reports to Stripe on success
14.6. Gateway Lambda returns same API responses as open-source (transparent wrapper)
14.7. Gateway Lambda adds <10ms latency overhead

### Requirement 15: Open-Source Compatibility

**User Story:** As an open-source contributor, I want clear separation between free and paid codebases.

**Acceptance Criteria:**
15.1. Open-source repo (vibejudge/vibejudge) has MIT license and no billing code
15.2. Proprietary repo (vibejudge-cloud) is private and contains: billing/, multi_tenant/, analytics/
15.3. Open-source repo includes self-hosting guide in README.md
15.4. Self-hosted version has feature parity with paid (no artificial limits)
15.5. Open-source updates merged into proprietary layer via Git submodule
15.6. Proprietary code never commits to open-source repo
15.7. Documentation clearly explains: "Free to self-host, managed service is paid"

### Requirement 16: Customer Support Tooling

**User Story:** As a customer success manager, I want tools to assist customers without AWS console access.

**Acceptance Criteria:**
16.1. Admin dashboard shows all tenants with: plan, usage, MRR, last login
16.2. Admin can impersonate tenant (read-only mode) for troubleshooting
16.3. Admin can manually adjust usage credits for service issues
16.4. Admin can extend free trials by X days
16.5. Admin can view CloudWatch logs filtered by tenant_id
16.6. Admin can trigger manual invoice generation
16.7. Admin actions logged to audit trail (who, what, when, why)

### Requirement 17: Churn Prevention and Retention

**User Story:** As a growth lead, I want to reduce churn with proactive retention strategies.

**Acceptance Criteria:**
17.1. Email sent when usage drops >50% vs previous month (engagement check-in)
17.2. Email sent when subscription cancellation initiated (retention offer)
17.3. Exit survey on cancellation: {reason, feature_requests, would_recommend}
17.4. Pause subscription option (freeze for 3 months, no charges)
17.5. Downgrade suggestion if usage consistently below plan limits
17.6. Reactivation campaign for churned customers after 30 days
17.7. Churn metrics tracked: MRR churn, logo churn, voluntary vs involuntary

### Requirement 18: Revenue Metrics and Analytics

**User Story:** As a CEO, I want clear revenue metrics to track business health.

**Acceptance Criteria:**
18.1. Dashboard shows: MRR, ARR, new MRR, expansion MRR, churned MRR
18.2. Dashboard shows: ARPU (average revenue per user), LTV (lifetime value)
18.3. Dashboard shows: customer count by plan (Starter, Pro, Enterprise)
18.4. Dashboard shows: growth rate (month-over-month, year-over-year)
18.5. Dashboard shows: CAC payback period (if marketing costs tracked)
18.6. Export to CSV for financial reporting
18.7. Stripe Dashboard integrated via iframe for detailed reports

### Requirement 19: Tax and Compliance

**User Story:** As a CFO, I want tax handling automated via Stripe Tax.

**Acceptance Criteria:**
19.1. Stripe Tax enabled for automatic tax calculation (VAT, sales tax)
19.2. Customer location determines tax jurisdiction
19.3. Tax-exempt customers provide exemption certificate (stored in Stripe)
19.4. Invoices show tax breakdown by jurisdiction
19.5. Stripe Tax handles nexus determination and filing (US states)
19.6. European VAT MOSS handled by Stripe for EU customers
19.7. Tax reports exportable for accountant review

### Requirement 20: Enterprise Custom Contracts

**User Story:** As a sales lead, I want to close enterprise deals with custom pricing and invoicing.

**Acceptance Criteria:**
20.1. Enterprise tier has no Stripe subscription (manual invoice workflow)
20.2. Custom contracts stored in DynamoDB: {tenant_id, contract_terms, annual_value, payment_schedule}
20.3. Usage tracked but not auto-billed (manual reconciliation quarterly)
20.4. Enterprise customers get dedicated Slack channel with support team
20.5. Enterprise invoices generated manually with NET 30 payment terms
20.6. Enterprise features: on-premise deployment option, custom SLA, dedicated infrastructure
20.7. Enterprise sales workflow: demo → trial → contract negotiation → onboarding

---

## Technical Constraints

1. **Payment Processor:** Stripe only (no PayPal, cryptocurrency)
2. **Billing Frequency:** Monthly (annual plans future enhancement)
3. **Currency:** USD only initially (multi-currency later)
4. **Tax Compliance:** Stripe Tax handles all jurisdictions
5. **Data Residency:** US-only initially (EU region later for GDPR)
6. **Code Separation:** Proprietary code never merged into open-source repo

## Dependencies

- Stripe account with production API keys
- DynamoDB tables: customers, subscriptions, usage_events
- Email service (SES or SendGrid) for transactional emails
- Open-source VibeJudge core as Lambda layer or Git submodule
- Customer dashboard (Next.js or Streamlit)

## Success Metrics

- **Conversion Rate:** 30%+ trial-to-paid conversion
- **Churn:** <5% monthly churn
- **Margin:** >37% gross margin (after AWS + Stripe fees)
- **CAC Payback:** <6 months
- **NPS:** >50 (customer satisfaction)
- **Support Load:** <10% customers contact support per month

## Out of Scope (Future Enhancements)

- Annual billing with discount (20% off)
- Multi-currency support (EUR, GBP, etc.)
- Referral program (give $50, get $50)
- Usage-based credits system (buy credits in bulk)
- Reseller/white-label partnerships
- Marketplace for custom agents
