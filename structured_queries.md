# Coverage SQL Queries

The database is created by running:

```powershell
python scripts/load_coverage.py
```

It contains two cleaned tables:

- `plans`: one row per health plan, keyed by `plan_id`.
- `claims`: one row per claim, keyed by `claim_id`, with `plan_id` referencing `plans.plan_id`.

## 1. What plan am I enrolled in?

**Member question:** What plan is member `M1001` enrolled in, and what are its premium and deductible?

```sql
SELECT DISTINCT
    c.member_id,
    p.plan_id,
    p.plan_name,
    p.monthly_premium,
    p.annual_deductible,
    p.copay_pct
FROM claims AS c
JOIN plans AS p ON p.plan_id = c.plan_id
WHERE c.member_id = 'M1001';
```

## 2. Which claims are still pending?

**Member question:** Which of my claims are still pending?

```sql
SELECT
    claim_id,
    member_id,
    procedure,
    claim_amount,
    date_filed
FROM claims
WHERE member_id = 'M1001'
  AND status = 'Pending'
ORDER BY date_filed;
```

## 3. What is my approved claim total?

**Member question:** How much has been approved for each member?

```sql
SELECT
    member_id,
    COUNT(*) AS approved_claim_count,
    SUM(claim_amount) AS approved_claim_total
FROM claims
WHERE status = 'Approved'
GROUP BY member_id
ORDER BY approved_claim_total DESC;
```

## 4. How much has each plan received in claims?

**Member question:** What is the total claim amount and claim count for each plan?

```sql
SELECT
    p.plan_id,
    p.plan_name,
    COUNT(c.claim_id) AS claim_count,
    COALESCE(SUM(c.claim_amount), 0) AS total_claim_amount
FROM plans AS p
LEFT JOIN claims AS c ON c.plan_id = p.plan_id
GROUP BY p.plan_id, p.plan_name
ORDER BY total_claim_amount DESC;
```

## 5. What is the claim history with plan details?

**Member question:** Show member `M1002`'s claims with the plan's coverage type and network tier.

```sql
SELECT
    c.claim_id,
    c.date_filed,
    c.procedure,
    c.status,
    c.claim_amount,
    p.plan_name,
    p.coverage_type,
    p.network_tier
FROM claims AS c
JOIN plans AS p ON p.plan_id = c.plan_id
WHERE c.member_id = 'M1002'
ORDER BY c.date_filed;
```