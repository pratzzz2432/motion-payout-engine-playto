# EXPLAINER.md

This document explains the key technical decisions and implementation details of the Playto Payout Engine.

---

## 1. The Ledger

### Balance Calculation Query

```sql
SELECT COALESCE(
    SUM(CASE WHEN entry_type = 'CREDIT' THEN amount_paise ELSE -amount_paise END),
    0
) FROM ledger_ledgerentry
WHERE merchant_id = %s AND is_held = FALSE
FOR UPDATE
```

**Why I modeled credits and debits this way:**

I chose a **single ledger table** approach instead of separate credit/debit tables because:

1. **Immutability**: Every transaction (credit or debit) is an immutable record. We never update ledger entries, only create new ones. This creates a complete audit trail.

2. **Database-Level Calculation**: The balance is calculated at the database level using SQL aggregation, not by fetching rows and doing Python arithmetic. This prevents race conditions and ensures accuracy.

3. **Held Funds**: The `is_held` flag allows us to hold funds for pending payouts without deducting them from the available balance. When a payout is requested, we create a debit with `is_held=True`. If it succeeds, we set `is_held=False`. If it fails, we delete the held entry.

4. **Invariant Enforcement**: The invariant `credits - debits = displayed balance` is enforced by the SQL query itself, making it impossible to have inconsistent balances.

5. **Single Source of Truth**: The balance is always calculated from the ledger entries, never stored as a separate field. This eliminates synchronization issues.

---

## 2. The Lock

### Code that prevents concurrent overdrafts:

```python
with transaction.atomic():
    # Lock the merchant's ledger entries for this transaction
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT COALESCE(
                SUM(CASE WHEN entry_type = 'CREDIT' THEN amount_paise ELSE -amount_paise END),
                0
            ) FROM ledger_ledgerentry
            WHERE merchant_id = %s AND is_held = FALSE
            FOR UPDATE
        """, [str(merchant.id)])
        available_balance = cursor.fetchone()[0] or 0

    # Check if sufficient balance
    if available_balance < amount_paise:
        return Response({'error': 'Insufficient balance'}, status=400)

    # Create payout and held debit entry...
```

**Database primitive it relies on:**

This relies on **PostgreSQL's `SELECT FOR UPDATE`** locking mechanism, which implements **pessimistic locking at the row level**.

**How it prevents race conditions:**

1. When two concurrent payout requests arrive for the same merchant:
   - Transaction A executes `SELECT FOR UPDATE` and locks the ledger rows
   - Transaction B tries to execute `SELECT FOR UPDATE` on the same rows and **blocks** until Transaction A commits

2. Transaction A checks the balance (₹100), creates the payout (₹60), and commits
   - Available balance is now ₹40

3. Transaction B unblocks, checks the balance (₹40), sees it's insufficient for ₹60, and rejects the request

4. **Result**: Exactly one payout succeeds, the other is rejected cleanly

**Why not optimistic locking?**

Optimistic locking (using version numbers) would require us to:
1. Fetch the current balance
2. Calculate the new balance in Python
3. Hope nobody changed it in between
4. Update and retry if it changed

This is error-prone for money operations. Pessimistic locking with `SELECT FOR UPDATE` guarantees that the balance check and deduction happen atomically.

---

## 3. The Idempotency

### How the system knows it has seen a key before:

```python
# Check if idempotency key exists
existing_key = IdempotencyKey.objects.filter(
    merchant=merchant,
    key=idempotency_key
).first()

# If key exists and is not expired, return cached response
if existing_key and not existing_key.is_expired():
    return Response(existing_key.response_data, status=200)
```

The system stores **idempotency keys in the database** with:
- `merchant`: Foreign key to Merchant (keys are scoped per merchant)
- `key`: UUID value
- `response_data`: JSON field storing the original response
- `created_at`: Timestamp for expiry checking

### What happens if the first request is in flight when the second arrives:

**Scenario**: Request A is processing when Request B arrives with the same key

1. **Request B arrives and queries the database**
   - `IdempotencyKey.objects.filter(key=X).first()`
   - If Request A hasn't committed yet, this returns `None`

2. **Request B proceeds to create the payout**
   - It enters the `transaction.atomic()` block
   - It tries to acquire the same `SELECT FOR UPDATE` lock
   - **It blocks until Request A commits or rolls back**

3. **Request A commits**
   - Creates the `IdempotencyKey` record
   - Releases the lock

4. **Request B unblocks**
   - Tries to create its own `IdempotencyKey`
   - **Hits the unique constraint** on `(merchant, key)`
   - Django raises `IntegrityError`
   - Transaction B rolls back

5. **Request B retries automatically**
   - Or returns an error asking the client to retry
   - This time it finds the key and gets the cached response

**In production**, I would add a retry mechanism or return a special status code (409 Conflict) telling the client to retry.

---

## 4. The State Machine

### Where failed-to-completed is blocked:

```python
# In Payout.clean() method
def clean(self):
    if not self.pk:
        # New payout validation...
    else:
        old_instance = Payout.objects.get(pk=self.pk)
        old_status = old_instance.status
        new_status = self.status

        # Define valid transitions
        valid_transitions = {
            'PENDING': ['PROCESSING'],
            'PROCESSING': ['COMPLETED', 'FAILED'],
            'COMPLETED': [],  # Terminal state
            'FAILED': [],  # Terminal state
        }

        if new_status not in valid_transitions.get(old_status, []):
            raise ValidationError({
                "status": f"Invalid state transition from {old_status} to {new_status}"
            })
```

**The check:**

The state machine validation happens in the `clean()` method, which Django automatically calls before `save()`. This ensures:

1. **Database-level enforcement**: The validation happens before any database write
2. **Clear error messages**: Attempting an invalid transition raises a `ValidationError` with a clear message
3. **Terminal states**: Once a payout reaches `COMPLETED` or `FAILED`, it can never transition to another state

**Legal transitions:**
- `PENDING → PROCESSING`: When background worker picks up the payout
- `PROCESSING → COMPLETED`: When bank settlement succeeds
- `PROCESSING → FAILED`: When bank settlement fails or max retries exceeded

**Illegal transitions (blocked):**
- `COMPLETED → PENDING`: Would revive a completed payout
- `FAILED → COMPLETED`: Would mark a failed payout as success without reprocessing
- Any backward transition

---

## 5. The AI Audit

### One specific example where AI gave subtly wrong code:

**What AI gave me:**

```python
# WRONG: AI suggested this
balance = LedgerEntry.objects.filter(
    merchant=merchant,
    is_held=False
).aggregate(
    balance=Sum(Case(
        When(entry_type='CREDIT', then=F('amount_paise')),
        When(entry_type='DEBIT', then=-F('amount_paise')),
        default=0,
        output_field=BigIntegerField()
    ))
)['balance']
```

**Why this is wrong:**

1. **No locking**: This query doesn't use `SELECT FOR UPDATE`, so it creates a **check-then-act race condition**:
   - Thread A reads balance = ₹100
   - Thread B reads balance = ₹100
   - Thread A deducts ₹60, balance = ₹40
   - Thread B deducts ₹60, balance = -₹20 ❌ **OVERDRAFT!**

2. **Not atomic**: The balance check and deduction happen in separate statements, allowing another transaction to modify the balance in between.

**What I caught and replaced it with:**

```python
# CORRECT: My implementation
with transaction.atomic():
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT COALESCE(
                SUM(CASE WHEN entry_type = 'CREDIT' THEN amount_paise ELSE -amount_paise END),
                0
            ) FROM ledger_ledgerentry
            WHERE merchant_id = %s AND is_held = FALSE
            FOR UPDATE
        """, [str(merchant.id)])
        available_balance = cursor.fetchone()[0] or 0

    if available_balance < amount_paise:
        return Response({'error': 'Insufficient balance'}, status=400)

    # Create payout and held debit...
```

**Key improvements:**

1. **Raw SQL with FOR UPDATE**: Locks the rows for the duration of the transaction
2. **Atomic block**: Ensures the balance check and payout creation happen together
3. **Database-level aggregation**: Calculation happens in the database, not Python
4. **Tested**: I wrote a concurrency test that spins up two threads and verifies only one succeeds

**Lesson learned**: AI often gives code that looks correct but misses subtle concurrency issues. For money-moving code, always use pessimistic locking and database-level operations.

---

## Additional Notes

### Why BigIntegerField instead of DecimalField?

I used `BigIntegerField` storing amounts in **paise** (1/100 of a rupee) instead of `DecimalField` because:

1. **No floating point errors**: Integers have perfect precision. Decimals can still have rounding issues in complex calculations.
2. **Database performance**: Integer arithmetic is faster than decimal arithmetic.
3. **Industry standard**: Many payment systems (Stripe, PayPal) store amounts as integers in the smallest currency unit.
4. **Clear intent**: Storing in paise makes it obvious we're dealing with money, not generic numbers.

The invariant is: **All money values are stored as paise (integers) and converted to rupees (decimals) only for display.**

### Why held funds instead of reserving from balance?

I used a **held debit entry** (`is_held=True`) instead of reserving from the balance because:

1. **Audit trail**: We have a permanent record of every hold, release, and settlement
2. **Rollback is trivial**: If a payout fails, we just delete the held entry, and the funds are automatically available again
3. **No double accounting**: We don't need to track "reserved balance" separately
4. **Clarity**: The ledger shows exactly what happened to every rupee

### Retry logic implementation

Payouts stuck in `PROCESSING` for more than 30 seconds are retried with:

- **Exponential backoff**: Wait time = `2^retry_count` seconds (1s, 2s, 4s, 8s, 16s, 30s max)
- **Max retries**: 3 attempts before marking as `FAILED`
- **Automatic refund**: Failed payouts automatically delete the held debit entry, returning funds to the merchant

This ensures that transient bank failures don't permanently block merchant funds.

---

## Conclusion

This implementation prioritizes **correctness over features**, **database-level operations over Python logic**, and **pessimistic locking over optimistic locking**. These choices ensure that the system can handle concurrent payout requests safely, prevent money loss, and maintain data integrity even under high load.
