"""
Diagnóstico de SALIDAS de Aerorutas.

Sirve para validar por qué una sucursal (oficina) aparece —o NO— como ORIGEN
("salida") en la web/app. Una oficina puede faltar como salida por 3 motivos
distintos, y este comando los separa:

    1. Aerorutas no devuelve NINGUNA ruta con esa oficina como `inicio`
       (solo es destino, nunca origen).
    2. Sí tiene rutas, pero con PRECIO 0/vacío -> la web las oculta
       (el listado público filtra precio_usd <= 0).
    3. El catálogo PRECARGADO (snapshot) quedó incompleto/viejo para esa fecha.

Acciones (se usan desde validar_salidas.bat, o a mano):

    python manage.py salidas oficinas
    python manage.py salidas buscar <texto>
    python manage.py salidas origen  <codofi|texto> [--fecha YYYY-MM-DD]
    python manage.py salidas destino <codofi|texto> [--fecha YYYY-MM-DD]
    python manage.py salidas snapshot [--fecha YYYY-MM-DD]
    python manage.py salidas diagnostico <codofi|texto> [--fecha YYYY-MM-DD]

`--fecha` por defecto es HOY (hora de Venezuela).
`--raw` (en origen/destino/diagnostico) imprime la respuesta cruda de la API.
"""
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from viajes import aerorutas
from viajes.models import RutaAerorutasSnapshot


def _precio(v) -> float:
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


class Command(BaseCommand):
    help = 'Diagnóstico de salidas de Aerorutas: valida por qué una oficina sale o no como origen.'

    def add_arguments(self, parser):
        parser.add_argument('accion', choices=[
            'oficinas', 'buscar', 'origen', 'destino', 'snapshot', 'diagnostico'])
        parser.add_argument('termino', nargs='?', default='',
                            help='codofi o texto de la oficina (según la acción)')
        parser.add_argument('--fecha', default=None, help='YYYY-MM-DD (por defecto HOY)')
        parser.add_argument('--raw', action='store_true', help='Imprime la respuesta cruda de la API')

    # ── helpers ──
    def _fecha(self, o) -> str:
        return o['fecha'] or timezone.localdate().isoformat()

    def _oficinas(self) -> list:
        try:
            ofis = aerorutas.consultar_oficinas()
        except aerorutas.AerorutasError as e:
            raise CommandError(f'No se pudo consultar OFICINAS: {e}')
        if not ofis:
            raise CommandError('OFICINAS devolvió vacío (¿token o red?).')
        return ofis

    def _resolver(self, termino: str, ofis: list) -> list:
        """Resuelve un término (codofi exacto o texto) a una lista de oficinas."""
        if not termino:
            raise CommandError('Falta el término (codofi o nombre de la oficina).')
        t = termino.strip().lower()
        exactos = [o for o in ofis if str(o.get('codofi', '')).lower() == t]
        if exactos:
            return exactos
        return [o for o in ofis
                if t in str(o.get('desofi', '')).lower()
                or t in str(o.get('codofi', '')).lower()
                or t in str(o.get('siglas', '')).lower()]

    def _nombre(self, cod, ofis):
        for o in ofis:
            if o.get('codofi') == cod:
                return o.get('desofi') or cod
        return cod

    # ── acciones ──
    def _accion_oficinas(self, ofis):
        self.stdout.write(self.style.MIGRATE_HEADING(f'\nOFICINAS ({len(ofis)}):'))
        for o in sorted(ofis, key=lambda x: str(x.get('desofi', ''))):
            self.stdout.write(
                f"  {str(o.get('codofi','')).rjust(4)}  {o.get('desofi','')}"
                f"   [{o.get('siglas','')}]")

    def _accion_buscar(self, termino, ofis):
        res = self._resolver(termino, ofis)
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\nCoincidencias para '{termino}': {len(res)}"))
        for o in res:
            self.stdout.write(
                f"  {str(o.get('codofi','')).rjust(4)}  {o.get('desofi','')}"
                f"   [{o.get('siglas','')}]")
        if not res:
            self.stdout.write(self.style.WARNING('  (ninguna)'))

    def _barrer_desde(self, cod, fecha, ofis):
        """RUTAS en vivo desde `cod` a todas las demás oficinas."""
        otros = [o.get('codofi') for o in ofis if o.get('codofi') and o.get('codofi') != cod]
        return aerorutas.barrer_rutas(fecha, [(cod, f) for f in otros])

    def _barrer_hacia(self, cod, fecha, ofis):
        """RUTAS en vivo desde todas las demás hacia `cod`."""
        otros = [o.get('codofi') for o in ofis if o.get('codofi') and o.get('codofi') != cod]
        return aerorutas.barrer_rutas(fecha, [(i, cod) for i in otros])

    def _imprimir_rutas(self, encontrados, ofis, fecha, sentido='origen', raw=False):
        """Imprime la tabla de rutas y devuelve (con_precio, sin_precio)."""
        con_precio, sin_precio = 0, 0
        if not encontrados:
            self.stdout.write(self.style.WARNING('  (sin rutas)'))
            return con_precio, sin_precio
        # Orden por hora
        for i, f, r in sorted(encontrados, key=lambda x: x[2].get('hora', '')):
            otro = f if sentido == 'origen' else i
            p = _precio(r.get('precio'))
            flag = self.style.SUCCESS('visible') if p > 0 else self.style.ERROR('OCULTA(precio 0)')
            if p > 0:
                con_precio += 1
            else:
                sin_precio += 1
            etiqueta = 'a  ' if sentido == 'origen' else 'de '
            self.stdout.write(
                f"  {etiqueta}{self._nombre(otro, ofis)[:26].ljust(26)} "
                f"codrut={str(r.get('codrut','')).ljust(6)} "
                f"hora={str(r.get('hora','')).ljust(7)} "
                f"precio={str(r.get('precio','')).rjust(6)}  {flag}")
        return con_precio, sin_precio

    def _accion_origen(self, termino, fecha, ofis, raw=False):
        objetivos = self._resolver(termino, ofis)
        if not objetivos:
            raise CommandError(f"No hay oficina que coincida con '{termino}'. Usa: salidas buscar {termino}")
        for o in objetivos:
            cod, nom = o.get('codofi'), o.get('desofi')
            self.stdout.write(self.style.MIGRATE_HEADING(
                f'\n== SALIDAS EN VIVO desde {nom} ({cod}) — {fecha} =='))
            enc = self._barrer_desde(cod, fecha, ofis)
            cp, sp = self._imprimir_rutas(enc, ofis, fecha, 'origen', raw)
            self.stdout.write(
                f'  -> {len(enc)} rutas | {cp} visibles (precio>0) | {sp} ocultas (precio 0)')

    def _accion_destino(self, termino, fecha, ofis, raw=False):
        objetivos = self._resolver(termino, ofis)
        if not objetivos:
            raise CommandError(f"No hay oficina que coincida con '{termino}'.")
        for o in objetivos:
            cod, nom = o.get('codofi'), o.get('desofi')
            self.stdout.write(self.style.MIGRATE_HEADING(
                f'\n== LLEGADAS EN VIVO hacia {nom} ({cod}) — {fecha} =='))
            enc = self._barrer_hacia(cod, fecha, ofis)
            cp, sp = self._imprimir_rutas(enc, ofis, fecha, 'destino', raw)
            self.stdout.write(
                f'  -> {len(enc)} rutas | {cp} visibles (precio>0) | {sp} ocultas (precio 0)')

    def _origenes_snapshot(self, fecha):
        """codofi de orígenes VISIBLES (precio>0) en el catálogo de esa fecha.

        La web arma el desplegable de orígenes con lo que devuelve el endpoint,
        que oculta los viajes sin precio. Por eso contamos solo esos: así el
        conteo coincide exactamente con lo que ve el cliente.
        """
        snap = RutaAerorutasSnapshot.objects.filter(fecha=fecha).first()
        data = snap.data if (snap and isinstance(snap.data, list)) else []
        origenes = {}
        for v in data:
            if _precio(v.get('precio_usd')) <= 0:
                continue  # la web lo oculta -> no aporta origen visible
            partes = str(v.get('id', '')).split('_')
            if len(partes) >= 2 and partes[1]:
                origenes.setdefault(partes[1], 0)
                origenes[partes[1]] += 1
        return snap, data, origenes

    def _accion_snapshot(self, fecha, ofis):
        snap, data, origenes = self._origenes_snapshot(fecha)
        self.stdout.write(self.style.MIGRATE_HEADING(
            f'\n== CATÁLOGO PRECARGADO (lo que ve la web) — {fecha} =='))
        if not snap:
            self.stdout.write(self.style.ERROR('  No hay snapshot para esa fecha (catálogo sin precargar).'))
            return
        # Viajes visibles (con precio) vs total
        visibles = [v for v in data if _precio(v.get('precio_usd')) > 0]
        self.stdout.write(
            f'  Snapshot actualizado: {snap.actualizado:%Y-%m-%d %H:%M} | '
            f'{len(data)} viajes ({len(visibles)} con precio)')
        self.stdout.write(f'  ORÍGENES disponibles (salen en la web): {len(origenes)}')
        for cod, n in sorted(origenes.items(), key=lambda x: -x[1]):
            self.stdout.write(f'    {self._nombre(cod, ofis)[:30].ljust(30)} ({cod})  {n} salidas')

    def _accion_diagnostico(self, termino, fecha, ofis, raw=False):
        objetivos = self._resolver(termino, ofis)
        if not objetivos:
            raise CommandError(f"No hay oficina que coincida con '{termino}'.")
        _, _, origenes_snap = self._origenes_snapshot(fecha)
        for o in objetivos:
            cod, nom = o.get('codofi'), o.get('desofi')
            self.stdout.write(self.style.MIGRATE_HEADING(
                f'\n########## DIAGNÓSTICO: {nom} ({cod}) — {fecha} ##########'))

            # 1. ¿Aparece como origen en el snapshot (lo que ve la web)?
            en_snap = origenes_snap.get(cod, 0)
            if en_snap:
                self.stdout.write(self.style.SUCCESS(
                    f'  [1] En el catálogo web SÍ sale como salida: {en_snap} viaje(s).'))
            else:
                self.stdout.write(self.style.ERROR(
                    '  [1] En el catálogo web NO sale como salida (no está en el snapshot).'))

            # 2. Salidas en vivo
            enc = self._barrer_desde(cod, fecha, ofis)
            cp, sp = 0, 0
            for _i, _f, r in enc:
                if _precio(r.get('precio')) > 0:
                    cp += 1
                else:
                    sp += 1
            self.stdout.write(
                f'  [2] Salidas EN VIVO (API): {len(enc)} rutas | '
                f'{cp} con precio | {sp} sin precio.')
            if enc:
                self._imprimir_rutas(enc, ofis, fecha, 'origen', raw)

            # 3. Llegadas en vivo (¿solo es destino?)
            hacia = self._barrer_hacia(cod, fecha, ofis)
            self.stdout.write(f'  [3] Llegadas EN VIVO (como destino): {len(hacia)} rutas.')

            # 4. Conclusión
            self.stdout.write(self.style.MIGRATE_HEADING('  -> CONCLUSIÓN:'))
            if len(enc) == 0 and len(hacia) > 0:
                self.stdout.write(
                    '     Aerorutas NO publica salidas desde esta oficina en esta fecha '
                    '(solo la usa como DESTINO). No es un bug de la web: no hay qué mostrar.')
            elif len(enc) == 0 and len(hacia) == 0:
                self.stdout.write(
                    '     Aerorutas no devuelve NINGUNA ruta (ni salida ni llegada) para esta '
                    'oficina en esta fecha. Probar otra fecha.')
            elif cp == 0 and sp > 0:
                self.stdout.write(
                    '     Tiene salidas, pero TODAS con precio 0 -> la web las oculta a propósito. '
                    'Hay que cargarles precio en Aerorutas para que salgan.')
            elif cp > 0 and en_snap == 0:
                self.stdout.write(
                    '     Tiene salidas con precio EN VIVO, pero el catálogo precargado no las '
                    'tiene -> snapshot viejo/incompleto. Correr: manage.py precargar_rutas')
            else:
                self.stdout.write(
                    '     Todo correcto: tiene salidas con precio y sale en el catálogo.')

            if raw:
                self.stdout.write(self.style.MIGRATE_HEADING('  RAW RUTAS (muestra):'))
                for _i, _f, r in enc[:8]:
                    self.stdout.write(f'     {r}')

    def handle(self, *args, **o):
        # La consola de Windows suele ser cp1252 y revienta con acentos/símbolos.
        # Forzamos utf-8 en la salida para que nunca falle (el .bat hace chcp 65001
        # para que además se vea bien).
        try:
            self.stdout._out.reconfigure(encoding='utf-8')
        except Exception:
            pass

        accion = o['accion']
        fecha = self._fecha(o)

        if accion == 'oficinas':
            self._accion_oficinas(self._oficinas())
            return
        if accion == 'buscar':
            self._accion_buscar(o['termino'], self._oficinas())
            return
        if accion == 'snapshot':
            self._accion_snapshot(fecha, self._oficinas())
            return
        if accion == 'origen':
            self._accion_origen(o['termino'], fecha, self._oficinas(), o['raw'])
            return
        if accion == 'destino':
            self._accion_destino(o['termino'], fecha, self._oficinas(), o['raw'])
            return
        if accion == 'diagnostico':
            self._accion_diagnostico(o['termino'], fecha, self._oficinas(), o['raw'])
            return
