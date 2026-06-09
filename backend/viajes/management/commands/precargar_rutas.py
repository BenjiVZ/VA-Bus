"""
Precarga el catálogo de viajes de Aerorutas para los próximos N días, barriendo
todos los pares de oficinas, y lo guarda en BD (RutaAerorutasSnapshot).
El endpoint /aerorutas/viajes/ luego lo sirve al instante.

Optimización: el primer día se barren TODOS los pares para descubrir los
"corredores activos"; los días siguientes solo se consultan esos corredores
(mucho más rápido).

Uso:
    python manage.py precargar_rutas               # próximos 15 días
    python manage.py precargar_rutas --dias 7
    python manage.py precargar_rutas --loop --cada 1800   # cada 30 min
"""
import time
from datetime import date, timedelta

from django.core.management.base import BaseCommand, CommandError

from viajes import aerorutas
from viajes.models import RutaAerorutasSnapshot


class Command(BaseCommand):
    help = 'Precarga el catálogo de viajes de Aerorutas (barrido de oficinas) por fecha.'

    def add_arguments(self, parser):
        parser.add_argument('--dias', type=int, default=15)
        parser.add_argument('--loop', action='store_true')
        parser.add_argument('--cada', type=int, default=1800, help='Segundos entre corridas en --loop')
        parser.add_argument('--intentos', type=int, default=6,
                            help='Reintentos del barrido inicial si la red no responde (ej. al despertar la PC)')
        parser.add_argument('--espera-red', type=int, default=60,
                            help='Segundos de espera entre reintentos del barrido inicial')
        parser.add_argument('--solo-si-falta', action='store_true',
                            help='Solo barre si HOY no tiene catálogo; si ya hay data, sale al instante.')

    def _hay_data_hoy(self):
        """True si ya existe un snapshot con viajes para HOY (chequeo barato de BD)."""
        snap = RutaAerorutasSnapshot.objects.filter(fecha=date.today()).first()
        return bool(snap and snap.data)

    def _descubrir_activos(self, fecha0, intentos, espera):
        """Barre todos los pares para hallar corredores activos.

        Si devuelve 0 (típico cuando el WiFi aún no se reconectó tras despertar
        de suspensión), reintenta varias veces con una espera entre cada uno.
        Hoy Aerorutas SIEMPRE publica rutas, así que 0 = fallo de red, no dato real.
        """
        encontrados0, activos = [], []
        for intento in range(1, intentos + 1):
            try:
                # La lista de oficinas también va dentro del reintento: si el DNS
                # aún no resuelve (PC recién despierta), esto falla y reintentamos.
                todos = aerorutas.pares_oficinas()
                self.stdout.write(f'Barriendo {len(todos)} pares (intento {intento}/{intentos})…')
                encontrados0 = aerorutas.barrer_rutas(fecha0, todos)
            except Exception as e:  # red caída / DNS no listo / API inalcanzable
                encontrados0 = []
                self.stderr.write(f'  Error de red en el barrido: {e}')
            activos = sorted({(i, f) for (i, f, _r) in encontrados0})
            if activos:
                return encontrados0, activos
            if intento < intentos:
                self.stdout.write(self.style.WARNING(
                    f'  0 corredores (¿red no lista?). Reintento en {espera}s…'))
                time.sleep(espera)
        return encontrados0, activos

    def _precargar(self, dias, intentos, espera):
        hoy = date.today()
        fechas = [hoy + timedelta(days=i) for i in range(dias)]

        # Fase 1: descubrir corredores activos con la primera fecha (barrido completo, con reintentos)
        encontrados0, activos = self._descubrir_activos(fechas[0].isoformat(), intentos, espera)
        if not activos:
            # No hay datos ni red: NO tocar la BD para no borrar el catálogo bueno.
            raise CommandError(
                'No se obtuvieron corredores tras varios intentos (red caída). '
                'Se conserva el catálogo anterior; reintentar más tarde.')
        self.stdout.write(self.style.SUCCESS(f'Corredores activos: {len(activos)}'))

        total = 0
        for idx, f in enumerate(fechas):
            fstr = f.isoformat()
            encontrados = encontrados0 if idx == 0 else aerorutas.barrer_rutas(fstr, activos)
            viajes = aerorutas.construir_viajes(encontrados, fstr)
            if not viajes:
                # No sobrescribir un snapshot bueno con uno vacío (probable fallo de red puntual).
                existente = RutaAerorutasSnapshot.objects.filter(fecha=f).first()
                if existente and existente.data:
                    self.stdout.write(
                        f'  {fstr}: 0 viajes nuevos — conservo snapshot anterior ({len(existente.data)}).')
                    total += len(existente.data)
                    continue
            RutaAerorutasSnapshot.objects.update_or_create(
                fecha=f, defaults={'data': viajes})
            total += len(viajes)
            self.stdout.write(f'  {fstr}: {len(viajes)} viajes')
        self.stdout.write(self.style.SUCCESS(f'Precarga lista: {total} viajes en {dias} días.'))

    def handle(self, *args, **o):
        if not o['loop']:
            if o['solo_si_falta'] and self._hay_data_hoy():
                self.stdout.write('Ya hay catálogo para hoy; nada que hacer.')
                return
            self._precargar(o['dias'], o['intentos'], o['espera_red'])
            return
        self.stdout.write(self.style.SUCCESS(
            f'Precargando cada {o["cada"]}s (Ctrl+C para salir)…'))
        try:
            while True:
                try:
                    if not (o['solo_si_falta'] and self._hay_data_hoy()):
                        self._precargar(o['dias'], o['intentos'], o['espera_red'])
                except CommandError as e:
                    self.stderr.write(self.style.ERROR(str(e)))
                time.sleep(o['cada'])
        except KeyboardInterrupt:
            self.stdout.write('\nDetenido.')
