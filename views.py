from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Profile, Coach, Plan, Program, NutritionTemplate, CoachRequest, Order, SiteSetting, CoachingSession, CoachReview
from .permissions import IsAdminUser, IsCoach
from .serializers import (
    UserSerializer, RegisterSerializer, ProfileSerializer, CoachSerializer,
    PlanSerializer, ProgramSerializer, NutritionTemplateSerializer,
    CoachRequestSerializer, OrderSerializer, SiteSettingSerializer, CoachingSessionSerializer, CoachReviewSerializer
)

class RegisterView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            "user": UserSerializer(user).data,
            "access": str(refresh.access_token),
            "refresh": str(refresh)
        }, status=status.HTTP_201_CREATED)

class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    def get_object(self):
        return self.request.user

@api_view(["GET","PATCH"])
def my_profile(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if request.method == "GET":
        return Response(ProfileSerializer(profile).data)
    s = ProfileSerializer(profile, data=request.data, partial=True)
    s.is_valid(raise_exception=True); s.save()
    return Response(s.data)

class PublicCoachViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CoachSerializer
    permission_classes = [permissions.AllowAny]
    def get_queryset(self):
        return Coach.objects.filter(active=True).select_related("user")

class PublicPlanViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PlanSerializer
    permission_classes = [permissions.AllowAny]
    def get_queryset(self):
        return Plan.objects.filter(active=True).order_by("price")

class ProgramViewSet(viewsets.ModelViewSet):
    serializer_class = ProgramSerializer
    queryset = Program.objects.all().order_by("-created_at")
    permission_classes = [IsAdminUser]

class NutritionViewSet(viewsets.ModelViewSet):
    serializer_class = NutritionTemplateSerializer
    queryset = NutritionTemplate.objects.all().order_by("-created_at")
    permission_classes = [IsAdminUser]

class AdminCoachViewSet(viewsets.ModelViewSet):
    serializer_class = CoachSerializer
    queryset = Coach.objects.all().select_related("user").order_by("-created_at")
    permission_classes = [IsAdminUser]

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        data = request.data
        username = data.get("username") or data.get("email")
        email = data.get("email","")
        if not username:
            return Response({"detail":"username or email is required"}, status=400)
        if User.objects.filter(username=username).exists():
            return Response({"detail":"username already exists"}, status=400)
        user = User.objects.create_user(username=username, email=email, password=data.get("password") or User.objects.make_random_password())
        Profile.objects.create(user=user, role="coach")
        coach = Coach.objects.create(
            user=user, focus=data.get("focus","Powerlifting"), tags=data.get("tags",[]),
            bio=data.get("bio",""), initials=data.get("initials",""), active=data.get("active",True),
            hourly_rate=data.get("hourly_rate",0)
        )
        return Response(CoachSerializer(coach).data, status=201)

class PlanViewSet(viewsets.ModelViewSet):
    serializer_class = PlanSerializer
    queryset = Plan.objects.all().order_by("price")
    permission_classes = [IsAdminUser]

class UserAdminViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    queryset = User.objects.all().order_by("-date_joined")
    permission_classes = [IsAdminUser]

class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self):
        if self.request.user.is_staff:
            return Order.objects.all().select_related("user","plan").order_by("-created_at")
        return Order.objects.filter(user=self.request.user).select_related("plan").order_by("-created_at")
    def perform_create(self, serializer):
        plan = get_object_or_404(Plan, pk=self.request.data.get("plan"))
        if not plan.active:
            raise ValidationError("Plan is not active")
        utr = str(self.request.data.get("utr", "")).strip()
        if not utr:
            raise ValidationError("UTR / transaction ID is required")
        serializer.save(user=self.request.user, plan=plan, amount=plan.price, status="created", utr=utr, payment_note=str(self.request.data.get("payment_note", "")).strip())

@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def public_payment_settings(request):
    setting = SiteSetting.objects.filter(key="manual_payment").first()
    value = setting.value if setting else {}
    return Response(value)

@api_view(["POST"])
@permission_classes([IsAdminUser])
def approve_order(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if order.status == "paid":
        return Response({"detail": "Order is already approved.", "order": OrderSerializer(order).data})
    order.status = "paid"
    order.reviewed_at = timezone.now()
    order.reviewed_by = request.user
    order.save(update_fields=["status", "reviewed_at", "reviewed_by"])
    profile, _ = Profile.objects.get_or_create(user=order.user)
    if order.plan:
        profile.plan_name = order.plan.name
        profile.save(update_fields=["plan_name"])
    return Response({"detail": "Payment approved and plan activated.", "order": OrderSerializer(order).data})

@api_view(["POST"])
@permission_classes([IsAdminUser])
def reject_order(request, pk):
    order = get_object_or_404(Order, pk=pk)
    order.status = "failed"
    order.reviewed_at = timezone.now()
    order.reviewed_by = request.user
    order.save(update_fields=["status", "reviewed_at", "reviewed_by"])
    return Response({"detail": "Payment rejected.", "order": OrderSerializer(order).data})

class CoachRequestViewSet(viewsets.ModelViewSet):
    serializer_class = CoachRequestSerializer
    def get_queryset(self):
        if self.request.user.is_staff:
            return CoachRequest.objects.all().select_related("athlete","coach__user")
        if hasattr(self.request.user, "coach"):
            return CoachRequest.objects.filter(coach=self.request.user.coach).select_related("athlete","coach__user")
        return CoachRequest.objects.filter(athlete=self.request.user).select_related("athlete","coach__user")
    def perform_create(self, serializer):
        serializer.save(athlete=self.request.user)

class AdminSettingsViewSet(viewsets.ModelViewSet):
    serializer_class = SiteSettingSerializer
    queryset = SiteSetting.objects.all().order_by("key")
    permission_classes = [IsAdminUser]


class CoachingSessionViewSet(viewsets.ModelViewSet):
    serializer_class=CoachingSessionSerializer
    def get_queryset(self):
        u=self.request.user
        if u.is_staff: return CoachingSession.objects.all().select_related("athlete","coach__user").order_by("-scheduled_at")
        if hasattr(u,"coach"): return CoachingSession.objects.filter(coach=u.coach).select_related("athlete","coach__user").order_by("-scheduled_at")
        return CoachingSession.objects.filter(athlete=u).select_related("athlete","coach__user").order_by("-scheduled_at")
    def perform_create(self,serializer):
        u=self.request.user
        if u.is_staff: serializer.save()
        elif hasattr(u,"coach") and u.coach.active: serializer.save(coach=u.coach,athlete_id=self.request.data.get("athlete"))
        else: raise permissions.PermissionDenied("Only an admin or active coach can create sessions.")
    def perform_update(self,serializer):
        u=self.request.user; obj=self.get_object()
        if u.is_staff or (hasattr(u,"coach") and obj.coach_id==u.coach.id): serializer.save()
        else: raise permissions.PermissionDenied("You can only manage your own coaching sessions.")

class PrivateCoachReviewViewSet(viewsets.ModelViewSet):
    serializer_class=CoachReviewSerializer
    def get_queryset(self):
        if not self.request.user.is_staff: return CoachReview.objects.none()
        return CoachReview.objects.all().select_related("athlete","coach__user","session")
    def create(self,request,*args,**kwargs):
        if request.user.is_staff or hasattr(request.user,"coach"):
            raise permissions.PermissionDenied("Reviews are submitted by athletes only and are private from coaches.")
        session=get_object_or_404(CoachingSession,pk=request.data.get("session"),athlete=request.user)
        if session.status!="completed": return Response({"detail":"Review is available only after a completed session."},status=400)
        if CoachReview.objects.filter(session=session).exists(): return Response({"detail":"Review already submitted."},status=400)
        rating=int(request.data.get("rating",0))
        if rating<1 or rating>5: return Response({"detail":"Rating must be between 1 and 5."},status=400)
        r=CoachReview.objects.create(session=session,athlete=request.user,coach=session.coach,rating=rating,review=request.data.get("review",""))
        return Response(CoachReviewSerializer(r).data,status=201)
