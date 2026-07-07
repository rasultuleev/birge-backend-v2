from django.urls import path
from . import views

urlpatterns = [
    path('health/', views.health_check),
    path('send-verification/', views.send_verification_code),
    path('verify-code/', views.verify_code),
    path('profile/', views.get_profile),
    path('profile/update/', views.update_profile),
    path('skills/', views.skill_list),
    path('events/create/', views.create_event),
    path('events/my/', views.my_events),
    path('events/<str:code>/qr/', views.event_qr),
    path('events/<int:event_id>/participants/', views.event_participants),
    path('participations/<int:participation_id>/verify/', views.verify_participation),
    path('register-event/', views.register_event_by_code),
]