from django.db import models
from django.db.models import Sum, F, Q
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
import uuid


class Merchant(models.Model):
    """
    Merchant model representing a business entity that can receive payouts.
    """
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def get_balance(self):
        """
        Calculate available balance using database-level aggregation.
        Returns balance in paise as an integer.
        """
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COALESCE(
                    SUM(CASE WHEN entry_type = 'CREDIT' THEN amount_paise ELSE -amount_paise END),
                    0
                ) FROM ledger_ledgerentry
                WHERE merchant_id = %s
                  AND is_held = FALSE
            """, [self.id])
            result = cursor.fetchone()[0]
            return result or 0

    def get_held_balance(self):
        """
        Calculate held balance (funds held for pending payouts).
        """
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COALESCE(SUM(amount_paise), 0)
                FROM ledger_ledgerentry
                WHERE merchant_id = %s
                  AND is_held = TRUE
                  AND entry_type = 'DEBIT'
            """, [self.id])
            result = cursor.fetchone()[0]
            return result or 0


class BankAccount(models.Model):
    """
    Bank account details for payouts.
    """
    ACCOUNT_TYPES = [
        ('SAVINGS', 'Savings Account'),
        ('CURRENT', 'Current Account'),
    ]

    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name='bank_accounts')
    account_name = models.CharField(max_length=255)
    account_number = models.CharField(max_length=255)
    ifsc_code = models.CharField(max_length=11)
    account_type = models.CharField(max_length=10, choices=ACCOUNT_TYPES, default='SAVINGS')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.account_name} - {self.ifsc_code}"


class LedgerEntry(models.Model):
    """
    Ledger entry representing a credit or debit.
    All amounts are stored in paise as BigIntegerField.
    """
    ENTRY_TYPES = [
        ('CREDIT', 'Credit'),
        ('DEBIT', 'Debit'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name='ledger_entries')
    entry_type = models.CharField(max_length=10, choices=ENTRY_TYPES)
    amount_paise = models.BigIntegerField()  # Amount in paise
    is_held = models.BooleanField(default=False)  # True if funds are held for pending payout
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Reference to the payout if this entry is from a payout
    payout = models.ForeignKey('Payout', on_delete=models.SET_NULL, null=True, blank=True, related_name='ledger_entries')

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['merchant', 'created_at']),
            models.Index(fields=['merchant', 'is_held']),
        ]

    def __str__(self):
        return f"{self.entry_type} - {self.merchant.name} - ₹{self.amount_paise / 100:.2f}"


class IdempotencyKey(models.Model):
    """
    Idempotency key to prevent duplicate operations.
    Keys are scoped per merchant and expire after 24 hours.
    """
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name='idempotency_keys')
    key = models.UUIDField(default=uuid.uuid4, unique=True)
    response_data = models.JSONField()  # Store the original response
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['merchant', 'key']
        indexes = [
            models.Index(fields=['merchant', 'key']),
            models.Index(fields=['created_at']),
        ]

    def is_expired(self):
        """
        Check if the idempotency key has expired (24 hours).
        """
        from django.conf import settings
        expiry_time = timezone.now() - timedelta(hours=settings.IDEMPOTENCY_KEY_EXPIRY_HOURS)
        return self.created_at < expiry_time

    def clean(self):
        """
        Validate that the key is not expired.
        """
        if self.is_expired():
            raise ValidationError("This idempotency key has expired.")


class Payout(models.Model):
    """
    Payout model representing a payout request from a merchant.
    Implements a state machine with proper transitions.
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name='payouts')
    bank_account = models.ForeignKey(BankAccount, on_delete=models.PROTECT, related_name='payouts')
    amount_paise = models.BigIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    failure_reason = models.TextField(blank=True)

    # Retry tracking
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    last_retry_at = models.DateTimeField(null=True, blank=True)

    # Metadata
    idempotency_key = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['merchant', 'status']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['idempotency_key']),
        ]

    def __str__(self):
        return f"Payout {self.id} - {self.merchant.name} - ₹{self.amount_paise / 100:.2f} ({self.status})"

    def clean(self):
        """
        Validate state transitions.
        """
        if not self.pk:
            # New payout, can only be created as PENDING
            if self.status != 'PENDING':
                raise ValidationError({"status": "New payouts must be created with PENDING status."})
        else:
            # Existing payout, validate transition
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

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def should_retry(self):
        """
        Check if payout should be retried.
        """
        if self.status != 'PROCESSING':
            return False

        if self.retry_count >= self.max_retries:
            return False

        # Check if stuck in processing for more than 30 seconds
        if self.last_retry_at:
            time_since_last_retry = timezone.now() - self.last_retry_at
            # Exponential backoff: 2^retry_count seconds, max 30 seconds
            backoff_seconds = min(2 ** self.retry_count, 30)
            return time_since_last_retry.total_seconds() > backoff_seconds

        return True
