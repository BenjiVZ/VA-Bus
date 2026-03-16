"""
Management command: cancela reservas 'pendiente' expiradas (>15 min sin comprobante).
Las reservas en estado 'apartado' NO se tocan — solo el admin las cambia.

Usage:
    python manage.py cancelar_expiradas
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from reservas.models import Reserva


class Command(BaseCommand):
    help = "Cancela reservas pendientes que superaron el tiempo de expiración (15 min) sin comprobante."

    def handle(self, *args, **options):
        ahora = timezone.now()

        expiradas = Reserva.objects.filter(
            estado='pendiente',
            fecha_expiracion__isnull=False,
            fecha_expiracion__lt=ahora,
        )

        count = expiradas.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS("No hay reservas expiradas."))
            return

        expiradas.update(estado='cancelado')

        self.stdout.write(self.style.WARNING(
            f"✅ {count} reserva(s) pendiente(s) canceladas por expiración."
        ))
