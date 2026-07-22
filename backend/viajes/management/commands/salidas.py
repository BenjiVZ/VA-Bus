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
import requests
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from viajes import aerorutas
from viajes.models import RutaAerorutasSnapshot

# Endpoint público que consume la web (default: producción). Se puede cambiar
# con --url para comparar contra un backend local (http://localhost:5002/api/...).
URL_PAGINA_DEFAULT = 'https://aerorutasdevenezuela.net/api/aerorutas/viajes/'


def _precio(v) -> float:
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


class Command(BaseCommand):
    help = 'Diagnóstico de salidas de Aerorutas: valida por qué una oficina sale o no como origen.'

    def add_arguments(self, parser):
        parser.add_argument('accion', choices=[
            'oficinas', 'buscar', 'origen', 'destino', 'snapshot', 'diagnostico',
            'mapa', 'resumen'])
        parser.add_argument('termino', nargs='?', default='',
                            help='codofi o texto de la oficina (según la acción)')
        parser.add_argument('--fecha', default=None, help='YYYY-MM-DD (por defecto HOY)')
        parser.add_argument('--raw', action='store_true', help='Imprime la respuesta cruda de la API')
        parser.add_argument('--asientos', action='store_true',
                            help='En origen/destino: también consulta asientos libres (más lento en hubs)')
        parser.add_argument('--url', default=URL_PAGINA_DEFAULT,
                            help='En mapa: endpoint de la web a comparar (default: producción)')

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

    def _asientos(self, origen_cod, codrut, fecha):
        """Asientos libres (BUSQPUESTO) de una ruta. None si falla la consulta."""
        try:
            return len(aerorutas.consultar_puestos(origen_cod, codrut, fecha))
        except aerorutas.AerorutasError:
            return None

    def _imprimir_rutas(self, encontrados, ofis, fecha, sentido='origen',
                        mostrar_asientos=False, raw=False):
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
            asi = ''
            if mostrar_asientos:
                n = self._asientos(i, r.get('codrut', ''), fecha)
                asi = f" asientos={('?' if n is None else n)!s:>3}"
            self.stdout.write(
                f"  {etiqueta}{self._nombre(otro, ofis)[:24].ljust(24)} "
                f"codrut={str(r.get('codrut','')).ljust(5)} "
                f"hora={str(r.get('hora','')).ljust(7)} "
                f"precio={str(r.get('precio','')).rjust(5)}{asi}  {flag}")
            # Nombre de la línea completa (desrut), útil para ubicar el servicio.
            desrut = str(r.get('desrut', '') or '').strip()
            if desrut:
                self.stdout.write(f"      línea: {desrut}")
            if raw:
                self.stdout.write(f"      raw: {r}")
        return con_precio, sin_precio

    def _accion_origen(self, termino, fecha, ofis, raw=False, asientos=False):
        objetivos = self._resolver(termino, ofis)
        if not objetivos:
            raise CommandError(f"No hay oficina que coincida con '{termino}'. Usa: salidas buscar {termino}")
        for o in objetivos:
            cod, nom = o.get('codofi'), o.get('desofi')
            self.stdout.write(self.style.MIGRATE_HEADING(
                f'\n== SALIDAS EN VIVO desde {nom} ({cod}) — {fecha} =='))
            enc = self._barrer_desde(cod, fecha, ofis)
            cp, sp = self._imprimir_rutas(enc, ofis, fecha, 'origen',
                                          mostrar_asientos=asientos, raw=raw)
            self.stdout.write(
                f'  -> {len(enc)} rutas | {cp} visibles (precio>0) | {sp} ocultas (precio 0)')

    def _accion_destino(self, termino, fecha, ofis, raw=False, asientos=False):
        objetivos = self._resolver(termino, ofis)
        if not objetivos:
            raise CommandError(f"No hay oficina que coincida con '{termino}'.")
        for o in objetivos:
            cod, nom = o.get('codofi'), o.get('desofi')
            self.stdout.write(self.style.MIGRATE_HEADING(
                f'\n== LLEGADAS EN VIVO hacia {nom} ({cod}) — {fecha} =='))
            enc = self._barrer_hacia(cod, fecha, ofis)
            cp, sp = self._imprimir_rutas(enc, ofis, fecha, 'destino',
                                          mostrar_asientos=asientos, raw=raw)
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

    def _fetch_pagina(self, url, fecha):
        """Trae lo que muestra la PÁGINA (endpoint público) para esa fecha.

        El backend ya filtra precio<=0, así que esto es exactamente lo que ve el
        cliente. Devuelve la lista de viajes o None si no se pudo leer.
        """
        try:
            r = requests.get(url, params={'fecha': fecha}, timeout=30)
            r.raise_for_status()
            d = r.json()
            return d.get('results', d) if isinstance(d, dict) else d
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  No se pudo leer la página ({url}): {e}'))
            return None

    @staticmethod
    def _por_origen(viajes):
        """{codofi_origen: set(codofi_destino)} de una lista de viajes."""
        o = {}
        for v in viajes or []:
            p = str(v.get('id', '')).split('_')
            if len(p) >= 3 and p[1] and p[2]:
                o.setdefault(p[1], set()).add(p[2])
        return o

    def _accion_mapa(self, fecha, ofis, url):
        """Barrido EN VIVO del día completo vs lo que muestra la PÁGINA."""
        self.stdout.write(self.style.MIGRATE_HEADING(
            f'\n== MAPEO DEL DÍA {fecha}: barrido EN VIVO (.bat) vs la PÁGINA =='))
        self.stdout.write('  Barriendo todos los pares en vivo (tarda ~1 min)…')
        encontrados = aerorutas.barrer_rutas(fecha, aerorutas.pares_oficinas())
        vivo = aerorutas.construir_viajes(encontrados, fecha, con_asientos=False)
        vivo_p = [v for v in vivo if _precio(v.get('precio_usd')) > 0]
        ov = self._por_origen(vivo_p)
        self.stdout.write(
            f'  EN VIVO (.bat): {len(vivo)} viajes | {len(vivo_p)} con precio | {len(ov)} orígenes')

        pagina = self._fetch_pagina(url, fecha)
        if pagina is None:
            self.stdout.write(self.style.WARNING(
                '  Sin comparación con la página; muestro solo el mapa en vivo.'))
            self._imprimir_mapa_origen(ov, {}, ofis)
            return
        op = self._por_origen(pagina)
        self.stdout.write(f'  EN LA PÁGINA:   {len(pagina)} viajes con precio | {len(op)} orígenes')
        self.stdout.write(f'  (página: {url})')

        # Viajes que el .bat ve con precio pero la página NO muestra.
        ids_pag = {v.get('id') for v in pagina}
        faltan = [v for v in vivo_p if v.get('id') not in ids_pag]
        self.stdout.write(self.style.MIGRATE_HEADING(
            f'  FALTAN en la página (con precio pero no salen): {len(faltan)}'))
        for v in sorted(faltan, key=lambda x: str(x.get('id'))):
            p = str(v.get('id')).split('_')
            self.stdout.write(
                f'    {self._nombre(p[1], ofis)[:22].ljust(22)} -> '
                f'{self._nombre(p[2], ofis)[:22].ljust(22)} '
                f'${str(v.get("precio_usd")).rjust(4)}   ({v.get("id")})')
        if not faltan:
            self.stdout.write(self.style.SUCCESS(
                '    (ninguno: la página está mostrando todo lo que hay en vivo)'))

        # Lo que la página muestra y el barrido no trajo (viajes de prueba locales, etc.)
        ids_vivo = {v.get('id') for v in vivo_p}
        extra = [v for v in pagina if v.get('id') not in ids_vivo]
        if extra:
            self.stdout.write(self.style.WARNING(
                f'  La página muestra {len(extra)} que el barrido no trajo '
                f'(probable viajes de prueba locales).'))

        # Tabla por origen.
        self._imprimir_mapa_origen(ov, op, ofis)

    def _imprimir_mapa_origen(self, ov, op, ofis):
        self.stdout.write(self.style.MIGRATE_HEADING(
            '  Destinos por origen (vivo vs página):'))
        for cod in sorted(ov, key=lambda c: -len(ov[c])):
            v_d = ov.get(cod, set())
            s_d = op.get(cod, set())
            faltan = v_d - s_d
            extra = ' ' + self.style.ERROR(
                'FALTAN: ' + ', '.join(self._nombre(m, ofis) for m in sorted(faltan))
            ) if faltan else ''
            self.stdout.write(
                f'    {self._nombre(cod, ofis)[:24].ljust(24)} '
                f'vivo={len(v_d):>2}  pág={len(s_d):>2}{extra}')

    def _accion_resumen(self, fecha, ofis):
        """Clasifica TODAS las oficinas del día: origen visible / oculta por
        precio 0 / sin salidas. Responde 'qué orígenes faltan y por qué'."""
        self.stdout.write(self.style.MIGRATE_HEADING(
            f'\n== RESUMEN DE OFICINAS — {fecha} =='))
        self.stdout.write('  Barriendo todo el día en vivo (tarda ~1 min)…')
        enc = aerorutas.barrer_rutas(fecha, aerorutas.pares_oficinas())
        stats = {}
        for i, _f, r in enc:
            s = stats.setdefault(i, {'con': 0, 'sin': 0})
            if _precio(r.get('precio')) > 0:
                s['con'] += 1
            else:
                s['sin'] += 1

        visibles, ocultas, sin = [], [], []
        for o in ofis:
            s = stats.get(o.get('codofi'))
            if s and s['con'] > 0:
                visibles.append((o, s))
            elif s and s['sin'] > 0:
                ocultas.append((o, s))
            else:
                sin.append(o)

        self.stdout.write(self.style.SUCCESS(
            f'\n  [A] ORÍGENES VISIBLES (salen en la web): {len(visibles)}'))
        for o, s in sorted(visibles, key=lambda x: -x[1]['con']):
            self.stdout.write(
                f"      {o.get('desofi','')[:24].ljust(24)} ({o.get('codofi')})  "
                f"{s['con']} salidas con precio")

        self.stdout.write(self.style.ERROR(
            f'\n  [B] OCULTAS — tienen salidas pero TODAS con precio 0: {len(ocultas)}'))
        self.stdout.write(
            '      (la web las oculta; para que salgan hay que cargarles PRECIO en Aerorutas)')
        for o, s in sorted(ocultas, key=lambda x: -x[1]['sin']):
            self.stdout.write(
                f"      {o.get('desofi','')[:24].ljust(24)} ({o.get('codofi')})  "
                f"{s['sin']} salidas SIN precio")

        self.stdout.write(self.style.WARNING(
            f'\n  [C] SIN SALIDAS (solo destino o sin uso): {len(sin)}'))
        for o in sorted(sin, key=lambda x: str(x.get('desofi', ''))):
            self.stdout.write(
                f"      {o.get('desofi','')[:24].ljust(24)} ({o.get('codofi')})")

        self.stdout.write(self.style.MIGRATE_HEADING(
            '\n  -> Para el proveedor (Aerorutas): las de [B] tienen buses saliendo '
            'pero sin precio.'))
        self.stdout.write(
            '     Cargándoles precio de salida, aparecen solas como origen en la web.')

    def _accion_diagnostico(self, termino, fecha, ofis, raw=False):
        objetivos = self._resolver(termino, ofis)
        if not objetivos:
            raise CommandError(f"No hay oficina que coincida con '{termino}'.")
        snap, _, origenes_snap = self._origenes_snapshot(fecha)
        for o in objetivos:
            cod, nom = o.get('codofi'), o.get('desofi')
            self.stdout.write(self.style.MIGRATE_HEADING(
                f'\n########## DIAGNÓSTICO: {nom} ({cod}) — {fecha} ##########'))
            # Identidad de la oficina
            self.stdout.write(
                f"  Oficina: {nom}  |  codofi={cod}  |  siglas={o.get('siglas','') or '—'}")

            # 1. ¿Aparece como origen en el snapshot (lo que ve la web)?
            en_snap = origenes_snap.get(cod, 0)
            if snap:
                estado_snap = (f'{snap.actualizado:%Y-%m-%d %H:%M}, '
                               f'{len(origenes_snap)} orígenes visibles')
            else:
                estado_snap = 'NO hay snapshot para esta fecha'
            if en_snap:
                self.stdout.write(self.style.SUCCESS(
                    f'  [1] Catálogo web: SÍ sale como salida ({en_snap} viaje/s). [{estado_snap}]'))
            else:
                self.stdout.write(self.style.ERROR(
                    f'  [1] Catálogo web: NO sale como salida. [{estado_snap}]'))

            # 2. Salidas en vivo (con línea y asientos)
            enc = self._barrer_desde(cod, fecha, ofis)
            cp = sum(1 for _i, _f, r in enc if _precio(r.get('precio')) > 0)
            sp = len(enc) - cp
            self.stdout.write(self.style.MIGRATE_HEADING(
                f'  [2] SALIDAS EN VIVO desde {nom} (API RUTAS): {len(enc)} ruta/s '
                f'| {cp} con precio | {sp} sin precio'))
            if enc:
                self._imprimir_rutas(enc, ofis, fecha, 'origen',
                                     mostrar_asientos=True, raw=raw)

            # 3. Llegadas en vivo — expandidas (¿solo es destino?)
            hacia = self._barrer_hacia(cod, fecha, ofis)
            hcp = sum(1 for _i, _f, r in hacia if _precio(r.get('precio')) > 0)
            self.stdout.write(self.style.MIGRATE_HEADING(
                f'  [3] LLEGADAS EN VIVO hacia {nom} (es destino): {len(hacia)} ruta/s '
                f'| {hcp} con precio'))
            if hacia:
                self._imprimir_rutas(hacia, ofis, fecha, 'destino',
                                     mostrar_asientos=True, raw=raw)

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

            # 5. Cómo encontrarla EN LA WEB como DESTINO (si tiene llegadas con precio).
            # Aunque no salga como origen, el cliente SÍ puede filtrar hacia ella:
            # elige uno de estos orígenes y aparece en el desplegable de destino.
            por_origen = {}
            for i, _f, r in hacia:
                p = _precio(r.get('precio'))
                if p > 0:
                    por_origen[i] = min(por_origen.get(i, p), p)
            if por_origen:
                self.stdout.write(self.style.MIGRATE_HEADING(
                    f'  -> EN LA WEB, para ver {nom} como DESTINO:'))
                self.stdout.write(
                    '     Elige en ORIGEN una de estas ciudades y luego se habilita en DESTINO:')
                for i, p in sorted(por_origen.items(), key=lambda x: x[1]):
                    self.stdout.write(f'       - {self._nombre(i, ofis)}  (desde ${p:g})')
            elif en_snap == 0:
                self.stdout.write(self.style.MIGRATE_HEADING(
                    f'  -> EN LA WEB: {nom} NO se puede filtrar (ni origen ni destino con precio).'))

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
        if accion == 'mapa':
            self._accion_mapa(fecha, self._oficinas(), o['url'])
            return
        if accion == 'resumen':
            self._accion_resumen(fecha, self._oficinas())
            return
        if accion == 'origen':
            self._accion_origen(o['termino'], fecha, self._oficinas(), o['raw'], o['asientos'])
            return
        if accion == 'destino':
            self._accion_destino(o['termino'], fecha, self._oficinas(), o['raw'], o['asientos'])
            return
        if accion == 'diagnostico':
            self._accion_diagnostico(o['termino'], fecha, self._oficinas(), o['raw'])
            return
