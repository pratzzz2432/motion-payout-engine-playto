from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from .models import Merchant, BankAccount, LedgerEntry, Payout
from .serializers import (
    MerchantSerializer,
    MerchantDetailSerializer,
    LedgerEntrySerializer,
    PayoutSerializer,
    PayoutCreateSerializer
)


class MerchantViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Merchant.objects.all()
    serializer_class = MerchantSerializer

    def retrieve(self, request, pk=None):
        merchant = get_object_or_404(Merchant, pk=pk)
        serializer = MerchantDetailSerializer(merchant)
        return Response(serializer.data)


class PayoutAPIView(APIView):

    def get(self, request, merchant_id):
        merchant = get_object_or_404(Merchant, pk=merchant_id)

        payouts = merchant.payouts.all()

        serializer = PayoutSerializer(
            payouts,
            many=True
        )

        return Response({
            "merchant_id": str(merchant.id),
            "merchant_name": merchant.name,
            "payouts": serializer.data
        })


    def post(self, request, merchant_id):

        merchant = get_object_or_404(
            Merchant,
            pk=merchant_id
        )

        serializer = PayoutCreateSerializer(
            data=request.data
        )

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=400
            )

        amount_paise = serializer.validated_data["amount_paise"]

        bank_account_id = serializer.validated_data["bank_account_id"]

        try:
            bank_account = BankAccount.objects.get(
                id=bank_account_id,
                merchant=merchant,
                is_active=True
            )

        except BankAccount.DoesNotExist:
            return Response(
                {
                    "error":
                    "Bank account not found"
                },
                status=404
            )

        # -------------------------
        # MINIMAL DEBUG CREATE ONLY
        # -------------------------

        payout = Payout.objects.create(
            merchant=merchant,
            bank_account=bank_account,
            amount_paise=amount_paise,
            status="PENDING"
        )

        return Response(
            {
                "id": str(payout.id),
                "merchant": str(merchant.id),
                "status": payout.status,
                "amount_paise": payout.amount_paise
            },
            status=201
        )


class LedgerEntryViewSet(viewsets.ReadOnlyModelViewSet):

    serializer_class = LedgerEntrySerializer

    def get_queryset(self):
        merchant_id = self.kwargs.get(
            "merchant_id"
        )

        return LedgerEntry.objects.filter(
            merchant_id=merchant_id
        ).select_related("payout")