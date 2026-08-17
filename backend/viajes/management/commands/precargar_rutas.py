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
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

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
        parser.add_argument('--forzar', action='store_true',
                            help='Sobrescribe el snapshot aunque el barrido nuevo traiga muchos menos '
                                 'viajes que el anterior (por defecto se conserva el anterior si parece parcial).')
        parser.add_argument('--usar-conocidos', action='store_true',
                            help='No barre los 600 pares para descubrir corredores: reutiliza los que ya '
                                 'salieron en los snapshots recientes. Para el refresco frecuente de HOY '
                                 '(~130 llamadas en vez de ~670). Si no hay snapshots, descubre igual.')
        parser.add_argument('--dias-conocidos', type=int, default=7,
                            help='Cuántos días atrás mirar para sacar los corredores conocidos.')

    def _hay_data_hoy(self):
        """True si ya existe un snapshot con viajes para HOY (chequeo barato de BD)."""
        # localdate(): fecha en hora de Venezuela (settings.TIME_ZONE), NO la del
        # reloj del SO. Así el snapshot se guarda/consulta bajo la misma fecha que
        # pide el navegador aunque el servidor esté en UTC.
        snap = RutaAerorutasSnapshot.objects.filter(fecha=timezone.localdate()).first()
        return bool(snap and snap.data)

    def _corredores_conocidos(self, dias_atras):
        """Pares (inicio, fin) que ya aparecieron en los snapshots recientes.

        Sirve para saltarse el descubrimiento: los 600 pares posibles tardan
        ~75 s y casi todos vienen vacíos, mientras que los corredores que de
        verdad operan son ~60. Cada viaje guardado trae el id compuesto
        `codrut_inicio_fin_fecha`, así que los pares salen de ahí sin tocar la
        red.

        Un corredor NUEVO no se detecta por aquí; lo encuentra la corrida
        completa (la que sí descubre), que debe seguir programada.
        """
        desde = timezone.localdate() - timedelta(days=dias_atras)
        pares = set()
        for snap in RutaAerorutasSnapshot.objects.filter(fecha__gte=desde):
            for v in (snap.data or []):
                partes = str(v.get('id') or '').split('_')
                if len(partes) >= 3 and partes[1] and partes[2]:
                    pares.add((partes[1], partes[2]))
        return sorted(pares)

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

    def _precargar(self, dias, intentos, espera, forzar=False,
                   usar_conocidos=False, dias_conocidos=7):
        hoy = timezone.localdate()  # hora de Venezuela, no el reloj del SO
        fechas = [hoy + timedelta(days=i) for i in range(dias)]

        # Fase 1: qué pares consultar.
        encontrados0, activos = [], []
        if usar_conocidos:
            conocidos = self._corredores_conocidos(dias_conocidos)
            if conocidos:
                self.stdout.write(f'Reusando {len(conocidos)} corredores conocidos '
                                  f'(sin descubrir).')
                try:
                    encontrados0 = aerorutas.barrer_rutas(fechas[0].isoformat(), conocidos)
                except Exception as e:
                    self.stderr.write(f'  Error de red: {e}')
                    encontrados0 = []
                # Si no volvió NADA, no darlo por bueno: `barrer_rutas` se traga
                # los fallos par a par, así que un corte de red se ve igual que
                # "hoy no hay viajes". Se cae al barrido completo, que sí
                # reintenta y aborta sin tocar la BD si de verdad no hay red.
                activos = conocidos if encontrados0 else []
            else:
                self.stdout.write(self.style.WARNING(
                    'No hay snapshots de donde sacar corredores: se descubre igual.'))

        # Sin conocidos (o si fallaron): barrido completo con reintentos.
        if not activos:
            encontrados0, activos = self._descubrir_activos(
                fechas[0].isoformat(), intentos, espera)
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
            existente = RutaAerorutasSnapshot.objects.filter(fecha=f).first()
            prev = len(existente.data) if (existente and existente.data) else 0
            # No sobrescribir un snapshot bueno con uno vacío o claramente parcial
            # (probable fallo de red durante el barrido). Umbral: si el nuevo trae
            # menos del 60% del anterior, se conserva el anterior. --forzar lo salta.
            if prev and not forzar and (not viajes or len(viajes) < prev * 0.6):
                self.stdout.write(self.style.WARNING(
                    f'  {fstr}: {len(viajes)} viajes (< 60% de {prev}) — parece barrido '
                    f'parcial, conservo el anterior. (usa --forzar para sobrescribir)'))
                total += prev
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
            self._precargar(o['dias'], o['intentos'], o['espera_red'], o['forzar'],
                            o['usar_conocidos'], o['dias_conocidos'])
            return
        self.stdout.write(self.style.SUCCESS(
            f'Precargando cada {o["cada"]}s (Ctrl+C para salir)…'))
        try:
            while True:
                try:
                    if not (o['solo_si_falta'] and self._hay_data_hoy()):
                        self._precargar(o['dias'], o['intentos'], o['espera_red'], o['forzar'],
                            o['usar_conocidos'], o['dias_conocidos'])
                except CommandError as e:
                    self.stderr.write(self.style.ERROR(str(e)))
                time.sleep(o['cada'])
        except KeyboardInterrupt:
            self.stdout.write('\nDetenido.')
