"""
Seed script to populate the database with test merchants and ledger entries.
Run this with: python manage.py shell < seed.py
or: python seed.py
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'payout_engine.settings')
django.setup()

from ledger.models import Merchant, BankAccount, LedgerEntry
from decimal import Decimal


def create_test_merchants():
    """Create test merchants with bank accounts and credit history."""

    merchants_data = [
        {
            'name': 'TechSolutions India Pvt Ltd',
            'email': 'contact@techsolutions.in',
            'credits': [
                {'amount': 10000000, 'desc': 'Payment from US Client - Website Development'},  # ₹100,000
                {'amount': 5000000, 'desc': 'Payment from UK Client - Mobile App'},  # ₹50,000
                {'amount': 7500000, 'desc': 'Payment from Australia - Consulting'},  # ₹75,000
            ],
            'bank_accounts': [
                {
                    'account_name': 'TechSolutions India Pvt Ltd',
                    'account_number': '123456789012',
                    'ifsc_code': 'HDFC0001234',
                    'account_type': 'CURRENT'
                }
            ]
        },
        {
            'name': 'Creative Designs Agency',
            'email': 'hello@creativedesigns.com',
            'credits': [
                {'amount': 8000000, 'desc': 'Payment from Canada - Brand Identity'},  # ₹80,000
                {'amount': 12000000, 'desc': 'Payment from UAE - Marketing Campaign'},  # ₹120,000
            ],
            'bank_accounts': [
                {
                    'account_name': 'Rahul Sharma',
                    'account_number': '987654321098',
                    'ifsc_code': 'ICIC0002345',
                    'account_type': 'SAVINGS'
                }
            ]
        },
        {
            'name': 'FreelanceHub Services',
            'email': 'team@freelancehub.io',
            'credits': [
                {'amount': 15000000, 'desc': 'Payment from Singapore - Software Development'},  # ₹150,000
                {'amount': 6000000, 'desc': 'Payment from Netherlands - UI/UX Design'},  # ₹60,000
                {'amount': 9000000, 'desc': 'Payment from Germany - Data Analysis'},  # ₹90,000
                {'amount': 11000000, 'desc': 'Payment from France - DevOps Services'},  # ₹110,000
            ],
            'bank_accounts': [
                {
                    'account_name': 'FreelanceHub Services',
                    'account_number': '456789012345',
                    'ifsc_code': 'SBIN0003456',
                    'account_type': 'CURRENT'
                },
                {
                    'account_name': 'Priya Patel',
                    'account_number': '789012345678',
                    'ifsc_code': 'AXIS0004567',
                    'account_type': 'SAVINGS'
                }
            ]
        }
    ]

    print("Creating test merchants...")

    for merchant_data in merchants_data:
        # Extract bank accounts data
        bank_accounts_data = merchant_data.pop('bank_accounts')
        credits_data = merchant_data.pop('credits')

        # Create merchant
        merchant, created = Merchant.objects.get_or_create(
            email=merchant_data['email'],
            defaults=merchant_data
        )

        if created:
            print(f"✓ Created merchant: {merchant.name}")

            # Create bank accounts
            for bank_data in bank_accounts_data:
                BankAccount.objects.create(
                    merchant=merchant,
                    **bank_data
                )
                print(f"  ✓ Added bank account: {bank_data['ifsc_code']}")

            # Create credit entries
            for credit in credits_data:
                LedgerEntry.objects.create(
                    merchant=merchant,
                    entry_type='CREDIT',
                    amount_paise=credit['amount'],
                    description=credit['desc'],
                    is_held=False
                )
                print(f"  ✓ Added credit: ₹{credit['amount'] / 100:.2f} - {credit['desc'][:50]}...")

            # Print balance
            balance = merchant.get_balance()
            print(f"  ✓ Total balance: ₹{balance / 100:.2f}")
        else:
            print(f"✓ Merchant already exists: {merchant.name}")
            balance = merchant.get_balance()
            print(f"  ✓ Current balance: ₹{balance / 100:.2f}")

    print("\n✅ Seed data created successfully!")
    print("\nMerchant Summary:")
    for merchant in Merchant.objects.all():
        balance = merchant.get_balance()
        held = merchant.get_held_balance()
        print(f"  • {merchant.name}: ₹{balance / 100:.2f} available, ₹{held / 100:.2f} held")


if __name__ == '__main__':
    # Clear existing data (optional - comment out if you want to keep data)
    print("Warning: This will delete all existing merchants and ledger entries.")
    response = input("Do you want to continue? (yes/no): ")

    if response.lower() == 'yes':
        print("\nDeleting existing data...")
        LedgerEntry.objects.all().delete()
        Payout.objects.all().delete()
        BankAccount.objects.all().delete()
        Merchant.objects.all().delete()
        print("✓ Existing data deleted\n")

        create_test_merchants()
    else:
        print("Cancelled. Adding new data without deleting...")

        # Check if any merchants exist
        if Merchant.objects.count() == 0:
            create_test_merchants()
        else:
            print("Merchants already exist. Skipping seed.")
