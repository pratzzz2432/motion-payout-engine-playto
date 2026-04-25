from rest_framework import serializers
from .models import Merchant, BankAccount, LedgerEntry, Payout


class BankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankAccount
        fields = ['id', 'account_name', 'account_number', 'ifsc_code', 'account_type', 'is_active']
        read_only_fields = ['id']


class MerchantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Merchant
        fields = ['id', 'name', 'email', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class LedgerEntrySerializer(serializers.ModelSerializer):
    """
    Serializer for ledger entries (credits and debits).
    """
    amount_rupees = serializers.SerializerMethodField()

    class Meta:
        model = LedgerEntry
        fields = ['id', 'entry_type', 'amount_paise', 'amount_rupees', 'is_held', 'description', 'created_at']
        read_only_fields = ['id', 'created_at']

    def get_amount_rupees(self, obj):
        return obj.amount_paise / 100


class PayoutSerializer(serializers.ModelSerializer):
    """
    Serializer for payout requests.
    """
    amount_rupees = serializers.SerializerMethodField()
    bank_account_details = BankAccountSerializer(source='bank_account', read_only=True)

    class Meta:
        model = Payout
        fields = [
            'id', 'merchant', 'bank_account', 'bank_account_details',
            'amount_paise', 'amount_rupees', 'status', 'failure_reason',
            'retry_count', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'status', 'failure_reason', 'retry_count',
            'created_at', 'updated_at'
        ]

    def get_amount_rupees(self, obj):
        return obj.amount_paise / 100


class PayoutCreateSerializer(serializers.Serializer):
    """
    Serializer for creating payout requests.
    """
    amount_paise = serializers.IntegerField(min_value=1)
    bank_account_id = serializers.UUIDField()

    def validate_amount_paise(self, value):
        """
        Validate that amount is positive.
        """
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value


class MerchantDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for merchant including balances.
    """
    available_balance = serializers.SerializerMethodField()
    held_balance = serializers.SerializerMethodField()
    bank_accounts = BankAccountSerializer(many=True, read_only=True)
    recent_ledger_entries = serializers.SerializerMethodField()

    class Meta:
        model = Merchant
        fields = [
            'id', 'name', 'email', 'available_balance', 'held_balance',
            'bank_accounts', 'recent_ledger_entries', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_available_balance(self, obj):
        """
        Get available balance (not held) in rupees.
        """
        balance_paise = obj.get_balance()
        return {
            'paise': balance_paise,
            'rupees': balance_paise / 100
        }

    def get_held_balance(self, obj):
        """
        Get held balance in rupees.
        """
        balance_paise = obj.get_held_balance()
        return {
            'paise': balance_paise,
            'rupees': balance_paise / 100
        }

    def get_recent_ledger_entries(self, obj):
        """
        Get recent ledger entries for this merchant.
        """
        entries = obj.ledger_entries.all()[:10]
        return LedgerEntrySerializer(entries, many=True).data
