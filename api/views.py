from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken
from django.http import HttpResponse
from django.db.models import Sum
from io import BytesIO
import qrcode
import random
from .models import (
    VerificationCode, ParticipantProfile, Skill, Event,
    Participation, ParticipantSkill
)

# ---------- ОБЩИЕ ----------

@api_view(['GET'])
def health_check(request):
    return Response({'status': 'ok', 'message': 'Birge API работает'})

# ---------- ВЕРИФИКАЦИЯ ПО EMAIL ----------

@api_view(['POST'])
@permission_classes([AllowAny])
def send_verification_code(request):
    email = request.data.get('email')
    if not email:
        return Response({'error': 'Email обязателен'}, status=400)

    # Генерируем 6-значный код
    code = f"{random.randint(100000, 999999)}"

    # Сохраняем в БД
    VerificationCode.objects.create(email=email, code=code)

    # Отправляем письмо (в DEBUG выводим в консоль)
    if settings.DEBUG:
        print(f"📧 Код для {email}: {code}")
    else:
        send_mail(
            subject='Код подтверждения Birge',
            message=f'Ваш код: {code}',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )

    return Response({'message': 'Код отправлен на email'})

@api_view(['POST'])
@permission_classes([AllowAny])
def verify_code(request):
    email = request.data.get('email')
    code = request.data.get('code')

    try:
        verification = VerificationCode.objects.filter(
            email=email,
            code=code,
            is_used=False
        ).latest('created_at')
    except VerificationCode.DoesNotExist:
        return Response({'error': 'Неверный или просроченный код'}, status=400)

    if verification.is_expired():
        return Response({'error': 'Код истёк'}, status=400)

    verification.is_used = True
    verification.save()

    # Создаём или находим пользователя
    user, created = User.objects.get_or_create(username=email, defaults={'email': email})
    if created:
        user.set_unusable_password()
        user.save()
        ParticipantProfile.objects.get_or_create(user=user, defaults={'group_name': 'Новая группа'})

    refresh = RefreshToken.for_user(user)
    return Response({
        'success': True,
        'access_token': str(refresh.access_token),
        'refresh_token': str(refresh),
    })

# ---------- ПРОФИЛЬ УЧАСТНИКА ----------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_profile(request):
    profile = ParticipantProfile.objects.get(user=request.user)
    total_hours = Participation.objects.filter(participant=profile, is_verified=True).aggregate(total=Sum('hours_claimed'))['total'] or 0
    skills = ParticipantSkill.objects.filter(participant=profile, level__gt=0).select_related('skill')
    skills_data = [{'name': s.skill.name, 'level': s.level} for s in skills]
    events = Participation.objects.filter(participant=profile, is_verified=True).select_related('event')[:10]
    events_data = [{'title': p.event.title, 'hours': p.hours_claimed, 'date': p.verified_at} for p in events]

    return Response({
        'first_name': request.user.first_name,
        'last_name': request.user.last_name,
        'user_type': profile.user_type,
        'institution': profile.institution,
        'group_name': profile.group_name,
        'total_hours': total_hours,
        'skills': skills_data,
        'events': events_data,
        'is_staff': request.user.is_staff,
    })

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    user = request.user
    profile = ParticipantProfile.objects.get(user=user)
    data = request.data

    if 'first_name' in data:
        user.first_name = data['first_name']
    if 'last_name' in data:
        user.last_name = data['last_name']
    user.save()

    if 'user_type' in data:
        profile.user_type = data['user_type']
    if 'institution' in data:
        profile.institution = data['institution']
    if 'group_name' in data:
        profile.group_name = data['group_name']
    profile.save()

    return Response({'message': 'Профиль обновлён'})

# ---------- НАВЫКИ ----------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def skill_list(request):
    skills = Skill.objects.all()
    return Response([{'id': s.id, 'name': s.name, 'category': s.category} for s in skills])

# ---------- ОРГАНИЗАТОР ----------

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_event(request):
    if not request.user.is_staff:
        return Response({'error': 'Доступ только для организаторов'}, status=403)
    data = request.data
    event = Event.objects.create(
        title=data['title'],
        description=data.get('description', ''),
        date_start=data['date_start'],
        date_end=data['date_end'],
        max_hours=data['max_hours'],
        code=data.get('code', ''),
        status='active',
        organizer=request.user
    )
    if 'skill_ids' in data:
        event.skills.set(data['skill_ids'])
    return Response({'message': 'Мероприятие создано', 'event_id': event.id, 'code': event.code})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_events(request):
    if not request.user.is_staff:
        return Response({'error': 'Доступ только для организаторов'}, status=403)
    events = Event.objects.filter(organizer=request.user)
    data = [{
        'id': e.id,
        'title': e.title,
        'code': e.code,
        'date_start': e.date_start,
        'date_end': e.date_end,
        'max_hours': e.max_hours,
        'status': e.status,
        'skills': [s.name for s in e.skills.all()]
    } for e in events]
    return Response(data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def event_qr(request, code):
    try:
        event = Event.objects.get(code=code, status='active')
    except Event.DoesNotExist:
        return Response({'error': 'Мероприятие не найдено'}, status=404)
    if request.user != event.organizer and not request.user.is_superuser:
        return Response({'error': 'Доступ запрещён'}, status=403)
    img = qrcode.make(event.code)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return HttpResponse(buffer.getvalue(), content_type="image/png")

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def event_participants(request, event_id):
    try:
        event = Event.objects.get(id=event_id, organizer=request.user)
    except Event.DoesNotExist:
        return Response({'error': 'Мероприятие не найдено или доступ запрещён'}, status=404)
    participations = Participation.objects.filter(event=event).select_related('participant__user')
    data = [{
        'id': p.id,
        'participant_name': f"{p.participant.user.first_name} {p.participant.user.last_name}",
        'user_type': p.participant.user_type,
        'institution': p.participant.institution,
        'group': p.participant.group_name,
        'hours': p.hours_claimed,
        'verified': p.is_verified,
        'registered_at': p.registered_at
    } for p in participations]
    return Response(data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_participation(request, participation_id):
    try:
        participation = Participation.objects.get(id=participation_id)
        if participation.event.organizer != request.user:
            return Response({'error': 'Доступ запрещён'}, status=403)
    except Participation.DoesNotExist:
        return Response({'error': 'Участие не найдено'}, status=404)

    participation.is_verified = True
    participation.verified_at = timezone.now()
    participation.verified_by = request.user
    participation.save()

    # Обновляем навыки участника
    participant = participation.participant
    for skill in participation.event.skills.all():
        ps, created = ParticipantSkill.objects.get_or_create(participant=participant, skill=skill)
        count = Participation.objects.filter(participant=participant, event__skills=skill, is_verified=True).count()
        ps.level = min(count, 3)
        ps.save()

    return Response({'message': 'Часы подтверждены'})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def register_event_by_code(request):
    code = request.data.get('code')
    hours = request.data.get('hours', 0)
    try:
        event = Event.objects.get(code=code, status='active')
    except Event.DoesNotExist:
        return Response({'error': 'Мероприятие не найдено'}, status=404)
    profile = ParticipantProfile.objects.get(user=request.user)
    if hours > event.max_hours:
        return Response({'error': f'Максимум {event.max_hours} часов'}, status=400)
    participation, created = Participation.objects.get_or_create(participant=profile, event=event, defaults={'hours_claimed': hours})
    if not created:
        return Response({'error': 'Вы уже зарегистрированы'}, status=400)
    return Response({'message': 'Регистрация успешна. Ожидайте подтверждения.'})