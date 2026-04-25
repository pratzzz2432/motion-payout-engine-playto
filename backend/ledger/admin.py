from django.contrib import admin
from .models import Merchant, BankAccount, LedgerEntry, Payout, IdempotencyKey


@admin.register(Merchant)
class MerchantAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'created_at']
    search_fields = ['name', 'email']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ['account_name', 'ifsc_code', 'merchant', 'account_type', 'is_active']
    list_filter = ['account_type', 'is_active']
    search_fields = ['account_name', 'ifsc_code', 'merchant__name']


@admin.register(LedgerEntry)
class LedgerEntryAdmin(admin.ModelAdmin):
    list_display = ['id', 'merchant', 'entry_type', 'amount_paise', 'is_held', 'created_at']
    list_filter = ['entry_type', 'is_held', 'created_at']
    search_fields = ['merchant__name', 'description']
    readonly_fields = ['id', 'created_at']


@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
    list_display = ['id', 'merchant', 'amount_paise', 'status', 'retry_count', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['merchant__name', 'id']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(IdempotencyKey)
class IdempotencyKeyAdmin(admin.ModelAdmin):
    list_display = ['merchant', 'key', 'created_at']
    search_fields = ['merchant__name', 'key']
    readonly_fields = ['created_at']
