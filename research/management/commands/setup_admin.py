from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = "Creates a default superuser/admin account if none exists."

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, default='admin', help='Admin username (default: admin)')
        parser.add_argument('--email', type=str, default='admin@kab.ac.ug', help='Admin email (default: admin@kab.ac.ug)')
        parser.add_argument('--password', type=str, default='admin123', help='Admin password (default: admin123)')

    def handle(self, *args, **options):
        User = get_user_model()
        username = options['username']
        email = options['email']
        password = options['password']

        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f"Superuser '{username}' already exists."))
            user = User.objects.get(username=username)
            user.set_password(password)
            user.is_staff = True
            user.is_superuser = True
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Updated password for '{username}' to '{password}'."))
        else:
            User.objects.create_superuser(username=username, email=email, password=password)
            self.stdout.write(self.style.SUCCESS(f"Successfully created superuser '{username}' (email: {email}, password: {password})."))
