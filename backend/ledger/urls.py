from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MerchantViewSet, PayoutAPIView, LedgerEntryViewSet

router = DefaultRouter()
router.register(r'merchants', MerchantViewSet, basename='merchant')
router.register(r'merchants/(?P<merchant_id>[^/.]+)/ledger', LedgerEntryViewSet, basename='ledgerentry')

urlpatterns = [
    path('', include(router.urls)),
    path('merchants/<uuid:merchant_id>/payouts/', PayoutAPIView.as_view(), name='payout-list-create'),
]
