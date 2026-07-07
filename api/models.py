from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class VerificationCode(models.Model):
    email = models.EmailField()
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def is_expired(self):
        return (timezone.now() - self.created_at).seconds > 300

class ParticipantProfile(models.Model):
    USER_TYPES = (
        ('school', 'Школьник'),
        ('college', 'Студент колледжа'),
        ('university', 'Студент вуза'),
        ('graduate', 'Выпускник'),
        ('other', 'Другое'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    user_type = models.CharField(max_length=20, choices=USER_TYPES, default='university')
    institution = models.CharField(max_length=200, blank=True)
    group_name = models.CharField(max_length=100, blank=True)
    total_hours = models.IntegerField(default=0)
    consent_employer = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.get_user_type_display()})"

class Skill(models.Model):
    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.name

class Event(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Черновик'),
        ('active', 'Активно'),
        ('completed', 'Завершено'),
        ('closed', 'Закрыто'),
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    date_start = models.DateTimeField()
    date_end = models.DateTimeField()
    max_hours = models.PositiveIntegerField(default=4)
    code = models.CharField(max_length=20, unique=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    organizer = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'is_staff': True})
    skills = models.ManyToManyField(Skill, through='EventSkill')
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.code:
            import random
            import string
            self.code = f"EV-{''.join(random.choices(string.digits, k=4))}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} ({self.code})"

class EventSkill(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('event', 'skill')

class Participation(models.Model):
    participant = models.ForeignKey(ParticipantProfile, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    hours_claimed = models.PositiveIntegerField(default=0)
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='verifications')
    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('participant', 'event')

    def __str__(self):
        return f"{self.participant.user.get_full_name()} – {self.event.title}"

class ParticipantSkill(models.Model):
    participant = models.ForeignKey(ParticipantProfile, on_delete=models.CASCADE)
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)
    level = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('participant', 'skill')

class OrganizationRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'На рассмотрении'),
        ('approved', 'Одобрено'),
        ('rejected', 'Отклонено'),
    )
    name = models.CharField(max_length=200)
    type = models.CharField(max_length=50, choices=[('university', 'Университет'), ('ngo', 'НПО'), ('company', 'Компания')])
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.status})"