#!/usr/bin/env python
import os
import sys
from django.core.management import call_command

def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'birge.settings')
    
    import django
    django.setup()
    
    from django.contrib.auth import get_user_model
    User = get_user_model()
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
        print("✅ Суперпользователь 'admin' создан (пароль: admin123)")

    call_command('migrate', interactive=False)

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django"
        ) from exc
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()
