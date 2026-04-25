from django.test import TestCase, TransactionTestCase
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
import uuid
import threading
import time

from .models import Merchant, BankAccount, LedgerEntry, Payout, IdempotencyKey
from .tasks import complete_payout, fail_payout


class ConcurrencyTest(TransactionTestCase):
    """
    Test concurrency control to prevent overdrafts.

    Scenario: Merchant with ₹100 (10000 paise) balance submits two simultaneous
    ₹60 (6000 paise) payout requests. Exactly one should succeed, the other
    should be rejected.
    """

    def setUp(self):
        """Create a test merchant with ₹100 balance."""
        self.merchant = Merchant.objects.create(
            name='Test Merchant',
            email='test@example.com'
        )

        # Add ₹100 credit
        LedgerEntry.objects.create(
            merchant=self.merchant,
            entry_type='CREDIT',
            amount_paise=10000,  # ₹100
            description='Initial credit'
        )

        # Create bank account
        self.bank_account = BankAccount.objects.create(
            merchant=self.merchant,
            account_name='Test Account',
            account_number='1234567890',
            ifsc_code='TEST0001234',
            account_type='SAVINGS'
        )

    def test_concurrent_payouts_prevent_overdraft(self):
        """
        Test that concurrent payout requests don't overdraw the balance.
        """
        print("\n=== Testing Concurrent Payouts ===")

        amount_to_withdraw = 6000  # ₹60 each
        idempotency_key_1 = uuid.uuid4()
        idempotency_key_2 = uuid.uuid4()

        results = []
        errors = []

        def create_payout(key):
            """Function to create a payout in a thread."""
            try:
                from django.db import connection
                from rest_framework.test import APIRequestFactory
                from ledger.views import PayoutAPIView

                # Create a mock request
                factory = APIRequestFactory()
                request = factory.post(
                    f'/api/v1/merchants/{self.merchant.id}/payouts/',
                    {
                        'amount_paise': amount_to_withdraw,
                        'bank_account_id': str(self.bank_account.id)
                    },
                    format='json'
                )
                request.META['HTTP_IDEMPOTENCY_KEY'] = str(key)

                # Create view and process request
                view = PayoutAPIView.as_view()
                response = view(request, merchant_id=str(self.merchant.id))

                results.append({
                    'key': key,
                    'status_code': response.status_code,
                    'data': response.data if hasattr(response, 'data') else None
                })

            except Exception as e:
                errors.append(str(e))

        # Create two threads to simulate concurrent requests
        thread1 = threading.Thread(target=create_payout, args=(idempotency_key_1,))
        thread2 = threading.Thread(target=create_payout, args=(idempotency_key_2,))

        # Start both threads
        thread1.start()
        thread2.start()

        # Wait for both to complete
        thread1.join()
        thread2.join()

        # Verify results
        print(f"\nResults: {len(results)} requests completed")
        for result in results:
            print(f"  - Key {result['key']}: Status {result['status_code']}")

        # Count successful payouts
        success_count = sum(1 for r in results if r['status_code'] == 201)
        rejected_count = sum(1 for r in results if r['status_code'] == 400)

        print(f"\nSuccess count: {success_count}")
        print(f"Rejected count: {rejected_count}")

        # Assertions
        self.assertEqual(success_count, 1, "Exactly one payout should succeed")
        self.assertEqual(rejected_count, 1, "Exactly one payout should be rejected")
        self.assertEqual(len(errors), 0, f"No errors should occur: {errors}")

        # Verify final balance
        final_balance = self.merchant.get_balance()
        expected_balance = 10000 - 6000  # ₹100 - ₹60 = ₹40

        print(f"Final balance: ₹{final_balance / 100:.2f}")
        print(f"Expected balance: ₹{expected_balance / 100:.2f}")

        self.assertEqual(final_balance, expected_balance,
                        "Final balance should be ₹40 (one successful payout)")

        print("✅ Concurrency test passed!")


class IdempotencyTest(TestCase):
    """
    Test idempotency key functionality.

    Scenario:
    1. First request with idempotency key should create payout
    2. Second request with same key should return same response
    3. No duplicate payout should be created
    """

    def setUp(self):
        """Create a test merchant with balance."""
        self.merchant = Merchant.objects.create(
            name='Test Merchant',
            email='idempotency@example.com'
        )

        # Add ₹1000 credit
        LedgerEntry.objects.create(
            merchant=self.merchant,
            entry_type='CREDIT',
            amount_paise=100000,  # ₹1000
            description='Initial credit'
        )

        # Create bank account
        self.bank_account = BankAccount.objects.create(
            merchant=self.merchant,
            account_name='Test Account',
            account_number='1234567890',
            ifsc_code='TEST0001234',
            account_type='SAVINGS'
        )

    def test_idempotency_key_prevents_duplicates(self):
        """
        Test that idempotency keys prevent duplicate payouts.
        """
        print("\n=== Testing Idempotency Keys ===")

        idempotency_key = uuid.uuid4()
        payout_amount = 5000  # ₹50

        # First request
        from rest_framework.test import APIRequestFactory
        from ledger.views import PayoutAPIView

        factory = APIRequestFactory()

        request1 = factory.post(
            f'/api/v1/merchants/{self.merchant.id}/payouts/',
            {
                'amount_paise': payout_amount,
                'bank_account_id': str(self.bank_account.id)
            },
            format='json'
        )
        request1.META['HTTP_IDEMPOTENCY_KEY'] = str(idempotency_key)

        view = PayoutAPIView.as_view()
        response1 = view(request1, merchant_id=str(self.merchant.id))

        print(f"\nFirst request status: {response1.status_code}")
        self.assertEqual(response1.status_code, 201, "First request should succeed")
        self.assertIn('id', response1.data, "Response should contain payout ID")

        first_payout_id = response1.data['id']
        print(f"First payout ID: {first_payout_id}")

        # Second request with same idempotency key
        request2 = factory.post(
            f'/api/v1/merchants/{self.merchant.id}/payouts/',
            {
                'amount_paise': payout_amount,
                'bank_account_id': str(self.bank_account.id)
            },
            format='json'
        )
        request2.META['HTTP_IDEMPOTENCY_KEY'] = str(idempotency_key)

        response2 = view(request2, merchant_id=str(self.merchant.id))

        print(f"Second request status: {response2.status_code}")
        self.assertEqual(response2.status_code, 200, "Second request should return cached response")
        self.assertEqual(response2.data['id'], first_payout_id,
                        "Second response should have same payout ID")

        # Verify only one payout was created
        payout_count = Payout.objects.filter(merchant=self.merchant).count()
        print(f"Total payouts created: {payout_count}")

        self.assertEqual(payout_count, 1, "Only one payout should be created")

        # Verify balance
        final_balance = self.merchant.get_balance()
        expected_balance = 100000 - payout_amount  # ₹1000 - ₹50

        print(f"Final balance: ₹{final_balance / 100:.2f}")
        print(f"Expected balance: ₹{expected_balance / 100:.2f}")

        self.assertEqual(final_balance, expected_balance,
                        "Balance should be debited only once")

        print("✅ Idempotency test passed!")

    def test_different_merchants_can_use_same_idempotency_key(self):
        """
        Test that idempotency keys are scoped per merchant.
        """
        print("\n=== Testing Idempotency Key Scoping ===")

        # Create second merchant
        merchant2 = Merchant.objects.create(
            name='Second Merchant',
            email='merchant2@example.com'
        )

        LedgerEntry.objects.create(
            merchant=merchant2,
            entry_type='CREDIT',
            amount_paise=100000,
            description='Initial credit'
        )

        BankAccount.objects.create(
            merchant=merchant2,
            account_name='Second Account',
            account_number='9876543210',
            ifsc_code='TEST0005678',
            account_type='SAVINGS'
        )

        # Both merchants use the same idempotency key
        shared_key = uuid.uuid4()

        from rest_framework.test import APIRequestFactory
        from ledger.views import PayoutAPIView

        factory = APIRequestFactory()

        # First merchant creates payout
        request1 = factory.post(
            f'/api/v1/merchants/{self.merchant.id}/payouts/',
            {
                'amount_paise': 5000,
                'bank_account_id': str(self.bank_account.id)
            },
            format='json'
        )
        request1.META['HTTP_IDEMPOTENCY_KEY'] = str(shared_key)

        view = PayoutAPIView.as_view()
        response1 = view(request1, merchant_id=str(self.merchant.id))

        self.assertEqual(response1.status_code, 201, "First merchant request should succeed")

        # Second merchant uses same key - should work
        bank_account_2 = merchant2.bank_accounts.first()

        request2 = factory.post(
            f'/api/v1/merchants/{merchant2.id}/payouts/',
            {
                'amount_paise': 5000,
                'bank_account_id': str(bank_account_2.id)
            },
            format='json'
        )
        request2.META['HTTP_IDEMPOTENCY_KEY'] = str(shared_key)

        response2 = view(request2, merchant_id=str(merchant2.id))

        self.assertEqual(response2.status_code, 201, "Second merchant should be able to use same key")

        # Both merchants should have their own payouts
        self.assertEqual(Payout.objects.filter(merchant=self.merchant).count(), 1)
        self.assertEqual(Payout.objects.filter(merchant=merchant2).count(), 1)

        print("✅ Idempotency key scoping test passed!")

    def test_expired_idempotency_key(self):
        """
        Test that expired idempotency keys are not reused.
        """
        print("\n=== Testing Expired Idempotency Keys ===")

        # Create an old idempotency key (more than 24 hours old)
        old_key = IdempotencyKey.objects.create(
            merchant=self.merchant,
            key=uuid.uuid4(),
            response_data={'test': 'data'},
            created_at=timezone.now() - timedelta(hours=25)
        )

        self.assertTrue(old_key.is_expired(), "Key should be expired")

        # Try to use the expired key
        from rest_framework.test import APIRequestFactory
        from ledger.views import PayoutAPIView

        factory = APIRequestFactory()

        request = factory.post(
            f'/api/v1/merchants/{self.merchant.id}/payouts/',
            {
                'amount_paise': 5000,
                'bank_account_id': str(self.bank_account.id)
            },
            format='json'
        )
        request.META['HTTP_IDEMPOTENCY_KEY'] = str(old_key.key)

        view = PayoutAPIView.as_view()
        response = view(request, merchant_id=str(self.merchant.id))

        # Should create a new payout, not return cached response
        self.assertEqual(response.status_code, 201, "Should create new payout with expired key")

        print("✅ Expired idempotency key test passed!")


class StateMachineTest(TestCase):
    """
    Test state machine transitions.
    """

    def setUp(self):
        """Create a test merchant and payout."""
        self.merchant = Merchant.objects.create(
            name='Test Merchant',
            email='state@example.com'
        )

        LedgerEntry.objects.create(
            merchant=self.merchant,
            entry_type='CREDIT',
            amount_paise=10000,
            description='Initial credit'
        )

        self.bank_account = BankAccount.objects.create(
            merchant=self.merchant,
            account_name='Test Account',
            account_number='1234567890',
            ifsc_code='TEST0001234',
            account_type='SAVINGS'
        )

        # Create a payout in PENDING state
        self.payout = Payout.objects.create(
            merchant=self.merchant,
            bank_account=self.bank_account,
            amount_paise=5000,
            status='PENDING'
        )

    def test_valid_state_transitions(self):
        """
        Test valid state transitions.
        """
        print("\n=== Testing Valid State Transitions ===")

        # PENDING -> PROCESSING
        self.payout.status = 'PROCESSING'
        self.payout.save()
        self.assertEqual(self.payout.status, 'PROCESSING')
        print("✓ PENDING -> PROCESSING: Valid")

        # PROCESSING -> COMPLETED
        self.payout.status = 'COMPLETED'
        self.payout.save()
        self.assertEqual(self.payout.status, 'COMPLETED')
        print("✓ PROCESSING -> COMPLETED: Valid")

    def test_invalid_state_transitions(self):
        """
        Test that invalid state transitions are rejected.
        """
        print("\n=== Testing Invalid State Transitions ===")

        # COMPLETED -> PENDING (should fail)
        self.payout.status = 'COMPLETED'
        self.payout.save()

        self.payout.status = 'PENDING'
        with self.assertRaises(Exception):
            self.payout.save()
        print("✓ COMPLETED -> PENDING: Invalid (blocked)")

        # FAILED -> COMPLETED (should fail)
        payout2 = Payout.objects.create(
            merchant=self.merchant,
            bank_account=self.bank_account,
            amount_paise=3000,
            status='FAILED'
        )

        payout2.status = 'COMPLETED'
        with self.assertRaises(Exception):
            payout2.save()
        print("✓ FAILED -> COMPLETED: Invalid (blocked)")

        print("✅ State machine test passed!")


class LedgerIntegrityTest(TestCase):
    """
    Test ledger integrity and balance calculations.
    """

    def setUp(self):
        """Create a test merchant."""
        self.merchant = Merchant.objects.create(
            name='Test Merchant',
            email='ledger@example.com'
        )

    def test_balance_calculation(self):
        """
        Test that balance is calculated correctly at database level.
        """
        print("\n=== Testing Balance Calculation ===")

        # Add credits
        LedgerEntry.objects.create(
            merchant=self.merchant,
            entry_type='CREDIT',
            amount_paise=10000,
            description='Credit 1'
        )
        print("✓ Added credit: ₹100")

        LedgerEntry.objects.create(
            merchant=self.merchant,
            entry_type='CREDIT',
            amount_paise=5000,
            description='Credit 2'
        )
        print("✓ Added credit: ₹50")

        balance = self.merchant.get_balance()
        self.assertEqual(balance, 15000, "Balance should be ₹150")
        print(f"✓ Balance: ₹{balance / 100:.2f}")

        # Add debit (not held)
        LedgerEntry.objects.create(
            merchant=self.merchant,
            entry_type='DEBIT',
            amount_paise=3000,
            is_held=False,
            description='Debit 1'
        )
        print("✓ Added debit: ₹30")

        balance = self.merchant.get_balance()
        self.assertEqual(balance, 12000, "Balance should be ₹120")
        print(f"✓ Balance: ₹{balance / 100:.2f}")

        # Add held debit (should not affect available balance)
        LedgerEntry.objects.create(
            merchant=self.merchant,
            entry_type='DEBIT',
            amount_paise=2000,
            is_held=True,
            description='Held Debit'
        )
        print("✓ Added held debit: ₹20")

        balance = self.merchant.get_balance()
        self.assertEqual(balance, 12000, "Balance should still be ₹120 (held debit not counted)")
        print(f"✓ Balance: ₹{balance / 100:.2f}")

        held_balance = self.merchant.get_held_balance()
        self.assertEqual(held_balance, 2000, "Held balance should be ₹20")
        print(f"✓ Held balance: ₹{held_balance / 100:.2f}")

        print("✅ Ledger integrity test passed!")

    def test_invariant_credits_minus_debits_equals_balance(self):
        """
        Test the invariant: credits - debits = displayed balance
        """
        print("\n=== Testing Ledger Invariant ===")

        # Add multiple entries
        credits = [10000, 5000, 7500]  # ₹100, ₹50, ₹75
        debits = [3000, 2000]  # ₹30, ₹20

        for amount in credits:
            LedgerEntry.objects.create(
                merchant=self.merchant,
                entry_type='CREDIT',
                amount_paise=amount,
                description='Credit'
            )

        for amount in debits:
            LedgerEntry.objects.create(
                merchant=self.merchant,
                entry_type='DEBIT',
                amount_paise=amount,
                is_held=False,
                description='Debit'
            )

        # Calculate expected balance
        expected_balance = sum(credits) - sum(debits)
        actual_balance = self.merchant.get_balance()

        print(f"Total credits: ₹{sum(credits) / 100:.2f}")
        print(f"Total debits: ₹{sum(debits) / 100:.2f}")
        print(f"Expected balance: ₹{expected_balance / 100:.2f}")
        print(f"Actual balance: ₹{actual_balance / 100:.2f}")

        self.assertEqual(actual_balance, expected_balance,
                        "Balance should equal credits - debits")

        print("✅ Ledger invariant test passed!")
