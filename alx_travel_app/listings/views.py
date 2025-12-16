from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Listing, Booking, Payment
from .serializers import ListingSerializer, BookingSerializer, PaymentSerializer
from drf_yasg.utils import swagger_auto_schema
from decouple import config
from .tasks import send_payment_confirmation_email


class ListingViewSet(viewsets.ModelViewSet):
    queryset = Listing.objects.all()
    serializer_class = ListingSerializer

    @swagger_auto_schema(
        operation_description="Retrieve a list of all travel listings.",
        responses={200: ListingSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer

    @swagger_auto_schema(
        operation_description="Retrieve a list of all bookings.",
        responses={200: BookingSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
# Initiate Pyment by making POST request to chapa API
CHAPA_API_URL = "https://api.chapa.co/v1/transaction/initialize"
CHAPA_SECRET_KEY = config("CHAPA_SECRET_KEY")

class InitiatePaymentAPIView(APIView):
    
    def post(self, request):
        # Make a post request to the Chapa api
        booking_reference = request.data.get("booking_reference")
        amount = request.data.get("amount")
        email = request.data.get("email")
        currency = request.data.get("currency", "ETB")
        callback_url = request.data.get("callback_url")
        
        # Check that all required fields are provided from the request
        if not all(booking_reference, amount, email, callback_url):
            return Response(
                {"error": "booking_reference, amount, email, and callback_url are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # prepare the payload for Chapa
        payload = {
            "amount": amount,
            "currency": currency,
            "email": email,
            "tx_ref": booking_reference,
            "callback_url": callback_url
        }
        
        # set payload headers
        headers = {
            "Authorization": f"Bearer {CHAPA_SECRET_KEY}",
            "Content-Type": "application/json"
        }
        
        try:
            # post payload to chapa api url
            response = response.post(
                CHAPA_API_URL,
                json=payload,
                headers=headers
            )
            
            response_data = response.json()
            
            if response.status_code != 200:
                # If response os not successful, display error
                return Response(response_data, status=response.status_code)
            
            transaction_id = response.data.get("data", {}).get("id")
            
            # Store payment in database with pending status
            payment = Payment.objects.create(
                booking_reference=booking_reference,
                amount=amount,
                transaction_id=transaction_id,
                status="pending",
            )
            
            serializer = PaymentSerializer(payment)
            
            return Response(
                {
                    "message": "Payment initiated successfully",
                    "payment": serializer.data,
                    "checkout_url": response_data.get("data", {}).get("checkout_url")
                },
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            

# verify payment with Chapa after a user completes payment
class VerifyPaymentAPIView(APIView):
    
    def get(self, request, tx_ref):
        try:
            payment = Payment.objects.get(booking_reference=tx_ref)
            
            headers = {
                "Authorization": f"Bearer {CHAPA_SECRET_KEY}"
            }
            
            # Chapa verify url
            verify_url = f"https://api.chapa.co/v1/transaction/verify/{tx_ref}"
            
            # send request to verify payment
            response = request.get(verify_url, headers=headers)
            data = response.json()
            
            if response.status_code != 200:
                payment.status = "failed"
                payment.save()
                
                return Response(data, status.HTTP_400_BAD_REQUEST)
            
            # Get payment status from Chapa to update the status on the payment instance
            payment_status = data.get("data", {}).get("status")
            
            if payment_status == "success":
                payment.status = "completed"
                send_payment_confirmation_email(
                    payment.user.email, payment.booking_reference
                )
            
            else:
                payment.status = "failed"
                
            payment.save()
            
            return Response(
                {
                    "message": "Payment verified successfully",
                    "status": payment.status
                },
                status=status.HTTP_200_OK
            )
        
        except Payment.DoesNotExist:
            return Response(
                {"error": "Payment not found"},
                status=status.HTTP_404_NOT_FOUND
            )