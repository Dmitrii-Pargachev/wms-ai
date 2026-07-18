from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from accounts.models import Business, BusinessMembership


class Command(BaseCommand):
    help = 'Удалить все бизнесы кроме demo и обновить email админа demo'

    def handle(self, *args, **options):
        # Delete all businesses except demo
        demo = Business.objects.filter(slug='demo').first()
        if not demo:
            self.stdout.write(self.style.ERROR('Бизнес demo не найден'))
            return

        others = Business.objects.exclude(slug='demo')
        count = others.count()
        others.delete()
        self.stdout.write(self.style.SUCCESS(f'Удалено бизнесов: {count}'))

        # Update demo admin email
        membership = BusinessMembership.objects.filter(
            business=demo, role='owner'
        ).select_related('user').first()

        if membership:
            membership.user.email = 'demoadmin@mail.ru'
            membership.user.save(update_fields=['email'])
            self.stdout.write(self.style.SUCCESS(
                f'Email админа demo обновлён: demoadmin@mail.ru (user: {membership.user.username})'
            ))
        else:
            self.stdout.write(self.style.WARNING('Владелец demo не найден'))

        self.stdout.write(self.style.SUCCESS('Готово!'))
