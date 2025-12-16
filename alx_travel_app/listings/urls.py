from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ListingViewSet, BookingViewSet, InitiatePaymentAPIView, VerifyPaymentAPIView

router = DefaultRouter()
router.register(r'listings', ListingViewSet, basename='listings')
router.register(r'bookings', BookingViewSet, basename='bookings')

urlpatterns = [
    path('api/', include(router.urls)),
    path('payments/initiate', InitiatePaymentAPIView.as_view()),
    path('payments/verify/<str:tx_ref>/', VerifyPaymentAPIView.as_view())
]
