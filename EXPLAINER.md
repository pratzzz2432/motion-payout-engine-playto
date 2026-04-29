# EXPLAINER.md

---

## 1. The Ledger — how I calculate balance and why

So here's the thing — I don't store a `balance` column anywhere. No single number sitting in the database getting updated every time money moves. Instead, every transaction is its own immutable row, and the balance is always *computed* from those rows on the fly.

Here's the actual query:

```python
from django.db.models import Sum

def get_available_balance(merchant):
    credits = LedgerEntry.objects.filter(
        merchant=merchant, entry_type="CREDIT"
    ).aggregate(total=Sum("amount_paise"))["total"] or 0

    debits = LedgerEntry.objects.filter(
        merchant=merchant, entry_type="DEBIT"
    ).aggregate(total=Sum("amount_paise"))["total"] or 0

    held = PayoutRequest.objects.filter(
        merchant=merchant, status__in=["PENDING", "PROCESSING"]
    ).aggregate(total=Sum("amount_paise"))["total"] or 0

    return credits - debits - held
```

**Why model it this way?**

Two reasons. First, floating-point money is a disaster — `0.1 + 0.2` in Python gives you `0.30000000000000004`. Everything here is stored in paise as `BigIntegerField`, so the math is always exact integer arithmetic.

Second, a mutable balance column is a consistency trap under concurrency. Two writes happen at the same time, one of them loses an update, and now your balance is wrong and you have no audit trail to debug it. With an append-only ledger, you can always replay history and get the same answer. The balance is deterministic.

The `held` piece is what prevents double-spending. Any payout that's PENDING or PROCESSING has already "claimed" that money — so we subtract it from what's available, even before the payout settles.

---

## 2. The Lock — how two concurrent requests can't both succeed

Here's the exact code that makes this safe:

```python
from django.db import transaction

def create_payout(merchant, amount_paise, idempotency_key):
    with transaction.atomic():
        # This is the key line — lock the merchant row before we check anything
        merchant = Merchant.objects.select_for_update().get(pk=merchant.pk)

        available = get_available_balance(merchant)

        if available < amount_paise:
            raise InsufficientFundsError(
                f"Available: {available} paise, Requested: {amount_paise} paise"
            )

        payout = PayoutRequest.objects.create(
            merchant=merchant,
            amount_paise=amount_paise,
            idempotency_key=idempotency_key,
            status="PENDING",
        )
        return payout
```

**The database primitive it relies on: `SELECT FOR UPDATE`**

`select_for_update()` tells the database to hold an exclusive row-level lock on that merchant record until the transaction commits or rolls back. Any other transaction trying to lock the same row just has to wait.

The classic failure case this prevents: two requests for ₹60 come in simultaneously against a ₹100 balance. Without the lock, both read `available = 100`, both pass the check, and both get created — merchant is now ₹20 overdrawn. With `SELECT FOR UPDATE`, only one gets through at a time. The second one waits, re-reads the balance (now ₹40), and either succeeds or fails correctly.

I treated this as a correctness problem, not a performance problem. The lock is slightly slower. That's fine.

---

## 3. The Idempotency — how we handle duplicate requests

Every payout request comes in with a merchant-scoped `Idempotency-Key` header. When a request arrives, we look it up first:

```python
def create_payout_idempotent(merchant, amount_paise, idempotency_key):
    existing = PayoutRequest.objects.filter(
        merchant=merchant,
        idempotency_key=idempotency_key
    ).first()

    if existing:
        return existing, False  # seen this before, return the original

    # New request — go through the full create flow
    payout = create_payout(merchant, amount_paise, idempotency_key)
    return payout, True
```

The application check is the fast path. But the *real* enforcer is a database unique constraint on `(merchant_id, idempotency_key)`. Even if two requests race past the lookup simultaneously, only one `INSERT` will succeed — the other hits an `IntegrityError`, which we catch and handle by re-fetching the row that just got created.

**What if the first request is still in flight when the second arrives?**

The second request does the lookup, finds nothing (first hasn't committed yet), and tries its own `INSERT`. Now one of two things:

- First request commits → second's `INSERT` fails with `IntegrityError` → we catch it, re-fetch the row, return the original payout.
- Both hit `INSERT` at the same instant → database constraint ensures only one wins → loser gets `IntegrityError` → same recovery path.

Either way, the caller gets the same payout object back. No duplicate is ever created. Keys expire after 24 hours — after that, a new key means a new payout.

Honestly, in payment systems, more bugs come from duplicate side effects than from actual logic errors. Idempotency isn't optional.

---

## 4. The State Machine — where illegal transitions are blocked

The payout lifecycle is: `PENDING → PROCESSING → COMPLETED` or `PENDING → PROCESSING → FAILED`. That's it. No going backward, no jumping states.

Here's where the check lives — in the model itself:

```python
VALID_TRANSITIONS = {
    "PENDING":    ["PROCESSING"],
    "PROCESSING": ["COMPLETED", "FAILED"],
    "COMPLETED":  [],   # terminal — nothing allowed out
    "FAILED":     [],   # terminal — nothing allowed out
}

class PayoutRequest(models.Model):

    def transition_to(self, new_status):
        allowed = VALID_TRANSITIONS.get(self.status, [])
        if new_status not in allowed:
            raise InvalidTransitionError(
                f"Cannot transition payout from '{self.status}' to '{new_status}'"
            )
        self.status = new_status
        self.save(update_fields=["status", "updated_at"])
```

`COMPLETED` and `FAILED` both have empty allowed-next lists. Any attempt to move out of them — `FAILED → COMPLETED`, `COMPLETED → PENDING`, whatever — raises immediately before anything is written.

I put this in the model layer intentionally. If it were only in the API view, a background worker or a Django management command could bypass it without realizing. The model layer is the last line of defense that everything has to go through.

---

## 5. The AI Audit — the bug I caught and fixed

This one's worth being specific about because it's subtle.

**What the AI generated:**

```python
def save(self, *args, **kwargs):
    if not self.pk:
        # First save — set defaults
        self.status = "PENDING"
    super().save(*args, **kwargs)
```

This looks completely fine. `if not self.pk` is a standard Django pattern for detecting new instances — and it works correctly for models with auto-increment integer primary keys, where `pk` is `None` until the first `INSERT`.

**Why it breaks with UUID primary keys:**

Django assigns UUIDs at object *construction* time, before `save()` is ever called. So on a new, unsaved payout, `self.pk` already has a value — it's a UUID. `if not self.pk` evaluates to `False`. The branch never runs. The payout gets created without a status, the state machine sees an invalid state on the first transition attempt, and the whole creation fails.

It's the kind of bug that passes a code review easily because the logic reads naturally. It only breaks in production when your PK type is UUID.

**What I replaced it with:**

```python
def save(self, *args, **kwargs):
    if self._state.adding:
        # Correctly identifies: this object hasn't been saved to the DB yet
        self.status = "PENDING"
    super().save(*args, **kwargs)
```

`self._state.adding` is Django's internal flag for "this instance has never been INSERTed." It stays `True` until the first successful write, regardless of whether `pk` is populated. That's the right primitive for this check.

Catching this is what I mean when I say engineering isn't just writing code — it's knowing *why* a pattern works and recognizing when the assumptions behind it don't hold.

---

## Quick summary of tradeoffs

- Correctness first, features second. Money that moves incorrectly is worse than a feature that's missing.
- Everything enforced at the data/model layer, not just the API layer.
- Stuck payouts retry with exponential backoff (max 3 attempts) before being marked failed — failures are recoverable by default, not immediately terminal.

That's the shape of the system.
