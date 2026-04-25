from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta
import uuid
import logging

from .models import Merchant, BankAccount, LedgerEntry, Payout, IdempotencyKey
from .serializers import (
    MerchantSerializer, MerchantDetailSerializer, BankAccountSerializer,
    LedgerEntrySerializer, PayoutSerializer, PayoutCreateSerializer
)

logger = logging.getLogger(__name__)


class MerchantViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing merchants.
    """
    queryset = Merchant.objects.all()
    serializer_class = MerchantSerializer

    def retrieve(self, request, pk=None):
        """
        Get detailed merchant information including balances.
        """
        merchant = get_object_or_404(Merchant, pk=pk)
        serializer = MerchantDetailSerializer(merchant)
        return Response(serializer.data)


class PayoutAPIView(APIView):
    """
    API view for creating and listing payouts.
    Implements idempotency and concurrency control.
    """

    def get(self, request, merchant_id):
        """
        List all payouts for a merchant.
        """
        merchant = get_object_or_404(Merchant, pk=merchant_id)
        payouts = merchant.payouts.all()
        serializer = PayoutSerializer(payouts, many=True)
        return Response({
            'merchant_id': str(merchant.id),
            'merchant_name': merchant.name,
            'payouts': serializer.data
        })

    def post(self, request, merchant_id):
        """
        Create a new payout request with idempotency support.

        This endpoint:
        1. Checks for idempotency key to prevent duplicates
        2. Uses SELECT FOR UPDATE to lock merchant ledger rows
        3. Validates sufficient balance
        4. Creates payout with held funds
        """
        merchant = get_object_or_404(Merchant, pk=merchant_id)

        # Get idempotency key from header
        idempotency_key_str = request.headers.get('Idempotency-Key')
        if not idempotency_key_str:
            return Response(
                {'error': 'Idempotency-Key header is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            idempotency_key = uuid.UUID(idempotency_key_str)
        except ValueError:
            return Response(
                {'error': 'Invalid Idempotency-Key format. Must be a UUID.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if idempotency key exists
        existing_key = IdempotencyKey.objects.filter(
            merchant=merchant,
            key=idempotency_key
        ).first()

        # If key exists and is not expired, return cached response
        if existing_key and not existing_key.is_expired():
            logger.info(f"Returning cached response for idempotency key: {idempotency_key}")
            return Response(existing_key.response_data, status=status.HTTP_200_OK)

        # Validate request data
        serializer = PayoutCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        amount_paise = serializer.validated_data['amount_paise']
        bank_account_id = serializer.validated_data['bank_account_id']

        # Validate bank account
        try:
            bank_account = BankAccount.objects.get(
                id=bank_account_id,
                merchant=merchant,
                is_active=True
            )
        except BankAccount.DoesNotExist:
            return Response(
                {'error': 'Bank account not found or inactive'},
                status=status.HTTP_404_NOT_FOUND
            )

        # CRITICAL: Use database transaction with SELECT FOR UPDATE lock
        # This prevents concurrent payouts from overdrawing the balance
        try:
            with transaction.atomic():
                # Lock the merchant's ledger entries for this transaction
                # This prevents other transactions from modifying them concurrently
                locked_entries = LedgerEntry.objects.select_for_update().filter(
                    merchant=merchant,
                    is_held=False
                )

                # Calculate available balance using database-level aggregation
                # This is done within the locked transaction to ensure consistency
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
                    return Response(
                        {
                            'error': 'Insufficient balance',
                            'available_balance_paise': available_balance,
                            'available_balance_rupees': available_balance / 100,
                            'requested_amount_paise': amount_paise,
                            'requested_amount_rupees': amount_paise / 100
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Create payout in PENDING state
                payout = Payout.objects.create(
                    merchant=merchant,
                    bank_account=bank_account,
                    amount_paise=amount_paise,
                    status='PENDING',
                    idempotency_key=idempotency_key
                )

                # Create held debit entry (funds are held until payout completes)
                held_debit = LedgerEntry.objects.create(
                    merchant=merchant,
                    entry_type='DEBIT',
                    amount_paise=amount_paise,
                    is_held=True,  # Funds are held
                    description=f'Held for payout {payout.id}',
                    payout=payout
                )

                # Prepare response data
                response_data = {
                    'id': str(payout.id),
                    'merchant': str(merchant.id),
                    'merchant_name': merchant.name,
                    'amount_paise': payout.amount_paise,
                    'amount_rupees': payout.amount_paise / 100,
                    'status': payout.status,
                    'bank_account': {
                        'id': str(bank_account.id),
                        'account_name': bank_account.account_name,
                        'ifsc_code': bank_account.ifsc_code
                    },
                    'created_at': payout.created_at.isoformat()
                }

                # Store idempotency key for future requests
                # Delete any expired keys first
                IdempotencyKey.objects.filter(
                    merchant=merchant,
                    created_at__lt=timezone.now() - timedelta(hours=24)
                ).delete()

                # Create new idempotency key record
                IdempotencyKey.objects.create(
                    merchant=merchant,
                    key=idempotency_key,
                    response_data=response_data
                )

                logger.info(f"Created payout {payout.id} for merchant {merchant.id} with amount {amount_paise}")

                return Response(response_data, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Error creating payout: {str(e)}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LedgerEntryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing ledger entries.
    """
    serializer_class = LedgerEntrySerializer

    def get_queryset(self):
        """
        Filter ledger entries by merchant.
        """
        merchant_id = self.kwargs.get('merchant_id')
        return LedgerEntry.objects.filter(merchant_id=merchant_id).select_related('payout')
