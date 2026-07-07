from django.contrib import admin
from .models import (
    VerificationCode, ParticipantProfile, Skill, Event,
    Participation, ParticipantSkill, OrganizationRequest
)

class VerificationCodeAdmin(admin.ModelAdmin):
    list_display = ('email', 'code', 'created_at', 'is_used')
    list_filter = ('is_used',)

class ParticipantProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'user_type', 'institution', 'group_name', 'total_hours')
    list_filter = ('user_type', 'institution')
    search_fields = ('user__first_name', 'user__last_name', 'user__username')

class SkillAdmin(admin.ModelAdmin):
    list_display = ('name', 'category')
    search_fields = ('name',)

class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'code', 'status', 'date_start', 'organizer')
    list_filter = ('status', 'date_start')
    search_fields = ('title', 'code')

class ParticipationAdmin(admin.ModelAdmin):
    list_display = ('participant', 'event', 'hours_claimed', 'is_verified', 'verified_at')
    list_filter = ('is_verified', 'event')
    search_fields = ('participant__user__first_name', 'event__title')

class ParticipantSkillAdmin(admin.ModelAdmin):
    list_display = ('participant', 'skill', 'level', 'updated_at')
    list_filter = ('skill', 'level')

class OrganizationRequestAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'email', 'status', 'created_at')
    list_filter = ('status', 'type')

admin.site.register(VerificationCode, VerificationCodeAdmin)
admin.site.register(ParticipantProfile, ParticipantProfileAdmin)
admin.site.register(Skill, SkillAdmin)
admin.site.register(Event, EventAdmin)
admin.site.register(Participation, ParticipationAdmin)
admin.site.register(ParticipantSkill, ParticipantSkillAdmin)
admin.site.register(OrganizationRequest, OrganizationRequestAdmin)