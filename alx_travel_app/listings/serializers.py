from rest_framework import serializers
from .models import Listing, Booking, Payment

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"


class ListingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Listing
        fields = "__all__"


class BookingSerializer(serializers.ModelSerializer):
    payments = PaymentSerializer(many=True, read_only=True)
    
    class Meta:
        model = Booking
        fields = "__all__"
