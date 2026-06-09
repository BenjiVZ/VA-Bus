"""
Cliente del sistema de control externo de Aerorutas
(https://aerorutasdevenezuela.com/server/request.php).

Consultas disponibles (todas vía GET con ?token=...&consul=...):
    OFICINAS    -> agencias/sucursales
    RUTAS       -> rutas disponibles (inicio, fin, fecha)
    BUSQPUESTO  -> puestos disponibles (codofi, codrut, fecha)
    TMPPUESTO   -> aparta un puesto temporalmente (MUTA estado)

OJO: el endpoint responde un "pseudo-JSON" inválido (clave `items` sin comillas,
objetos sin comas/array y números con ceros a la izquierda). Por eso NO se puede
usar response.json(): hay que normalizarlo con `parse_items`.
"""
import concurrent.futures
import json
import logging
import re
import time

import requests
from django.conf import settings

logger = logging.getLogger('aerorutas')

# Caché en memoria del barrido por fecha: {fecha: (timestamp, [viajes])}
_CACHE_TODAS = {}
_CACHE_TTL = 300  # 5 minutos


class AerorutasError(Exception):
    """Error de comunicación o configuración con el sistema Aerorutas."""


def parse_items(raw: str) -> list:
    """
    Normaliza el pseudo-JSON de Aerorutas a una lista de dicts.
    Extrae cada objeto `{...}` y pone comillas a los números (conserva los ceros
    a la izquierda: '01', '001'), tratando los códigos como texto.
    """
    objetos = re.findall(r'\{[^{}]*\}', raw or '')
    out = []
    for o in objetos:
        fixed = re.sub(r':\s*(\d+)(?=\s*[,}])', r':"\1"', o)
        try:
            obj = json.loads(fixed)
        except json.JSONDecodeError:
            continue
        # Normaliza las claves: la API a veces las manda con espacios o un ':'
        # pegado (ej. "precio:"). Las dejamos limpias: precio, codrut, etc.
        out.append({k.strip().rstrip(':').strip(): v for k, v in obj.items()})
    return out


def _token() -> str:
    token = getattr(settings, 'AERORUTAS_API_TOKEN', '') or ''
    if not token:
        raise AerorutasError('AERORUTAS_API_TOKEN no está configurado en el entorno.')
    return token


def _get_raw(consul: str, **params) -> str:
    """GET a la API. Devuelve el texto crudo o lanza AerorutasError."""
    query = {'token': _token(), 'consul': consul}
    query.update({k: v for k, v in params.items() if v is not None})
    url = getattr(settings, 'AERORUTAS_API_URL', 'https://aerorutasdevenezuela.com/server/request.php')
    timeout = int(getattr(settings, 'AERORUTAS_TIMEOUT', 20))
    try:
        resp = requests.get(url, params=query, timeout=timeout)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error('Aerorutas %s: error de conexión: %s', consul, e)
        raise AerorutasError(f'No se pudo consultar Aerorutas: {e}')
    return resp.text


def _consultar(consul: str, **params) -> list:
    return parse_items(_get_raw(consul, **params))


# ── Consultas de lectura ──

def consultar_oficinas() -> list:
    """Lista de oficinas/sucursales. [{codofi, desofi, siglas}, ...]"""
    return _consultar('OFICINAS')


# Caché de la lista de oficinas (estables) para no llamar al banco en cada apertura.
_OFICINAS_LISTA = {'ts': 0, 'data': []}


def consultar_oficinas_cacheado(ttl: int = 3600) -> list:
    """Oficinas cacheadas 1h. Si falla la llamada, devuelve la última copia."""
    ahora = time.time()
    if not _OFICINAS_LISTA['data'] or (ahora - _OFICINAS_LISTA['ts']) > ttl:
        try:
            datos = consultar_oficinas()
            if datos:
                _OFICINAS_LISTA['data'] = datos
                _OFICINAS_LISTA['ts'] = ahora
        except AerorutasError:
            pass  # conserva la copia anterior
    return _OFICINAS_LISTA['data']


def consultar_rutas(inicio: str, fin: str, fecha: str) -> list:
    """Rutas disponibles entre dos oficinas en una fecha. [{codrut, hora, desrut}, ...]"""
    return _consultar('RUTAS', inicio=inicio, fin=fin, fecha=fecha)


def consultar_puestos(codofi: str, codrut: str, fecha: str) -> list:
    """Puestos disponibles de una ruta. [{puesto}, ...]"""
    return _consultar('BUSQPUESTO', codofi=codofi, codrut=codrut, fecha=fecha)


def pares_oficinas() -> list:
    """Todos los pares (inicio, fin) de oficinas, inicio != fin."""
    codigos = [o.get('codofi') for o in consultar_oficinas() if o.get('codofi')]
    return [(i, f) for i in codigos for f in codigos if i != f]


def barrer_rutas(fecha: str, pares: list, max_workers: int = 12) -> list:
    """Consulta RUTAS para cada par (concurrente). Devuelve [(inicio, fin, ruta), ...]."""
    encontrados = []

    def _rutas_de(par):
        i, f = par
        try:
            return [(i, f, r) for r in consultar_rutas(i, f, fecha)]
        except AerorutasError:
            return []

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
        for res in ex.map(_rutas_de, pares):
            encontrados.extend(res)
    return encontrados


def construir_viajes(encontrados: list, fecha: str, max_workers: int = 12,
                     con_asientos: bool = True) -> list:
    """Transforma [(inicio, fin, ruta), ...] a viajes (formato app), con asientos."""
    if not encontrados:
        return []

    mapa_oficinas()  # primear caché de nombres antes del pool (evita carrera)

    def _a_viaje(item):
        i, f, r = item
        disp = None
        if con_asientos:
            try:
                disp = len(consultar_puestos(i, r.get('codrut', ''), fecha))
            except AerorutasError:
                disp = None
        return viaje_shape(r, i, f, fecha, disp)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
        return list(ex.map(_a_viaje, encontrados))


def consultar_todas_rutas(fecha: str) -> list:
    """
    Barrido completo en vivo (todos los pares) para una fecha, con caché en
    memoria. Úsalo como fallback; lo normal es servir el catálogo precargado.
    """
    ahora = time.time()
    cache = _CACHE_TODAS.get(fecha)
    if cache and (ahora - cache[0]) < _CACHE_TTL:
        return cache[1]
    encontrados = barrer_rutas(fecha, pares_oficinas())
    viajes = construir_viajes(encontrados, fecha)
    _CACHE_TODAS[fecha] = (ahora, viajes)
    return viajes


# ── Acción que MUTA estado en Aerorutas ──

# ── Transformadores: Aerorutas → formato interno de la app ──
# Para que las pantallas existentes (ViajesPage / AsientosPage) consuman la data
# de Aerorutas SIN cambiar su forma, el backend la traduce a los mismos shapes
# que devuelven /viajes/ y /viajes/<id>/asientos/.

def parse_hora(hora: str) -> str:
    """Convierte la hora de Aerorutas ('02:00P', '10:30A') a 'HH:MM:00' (24h)."""
    try:
        h = (hora or '').strip().upper()
        suf = ''
        if h and h[-1] in ('A', 'P'):
            suf, h = h[-1], h[:-1]
        hh, mm = h.split(':')
        hh, mm = int(hh), int(mm)
        if suf == 'P' and hh != 12:
            hh += 12
        if suf == 'A' and hh == 12:
            hh = 0
        return f'{hh:02d}:{mm:02d}:00'
    except Exception:
        return '00:00:00'


def viaje_id(codrut: str, inicio: str, fin: str, fecha: str) -> str:
    """ID compuesto de un viaje de Aerorutas (no hay un entero único)."""
    return f'{codrut}_{inicio}_{fin}_{fecha}'


def parse_viaje_id(trip_id: str):
    """Inverso de viaje_id → (codrut, inicio, fin, fecha)."""
    return tuple(trip_id.split('_', 3))


def _origen_destino(desrut: str):
    """'SNC-PUERTO LA CRUZ' → ('SNC', 'PUERTO LA CRUZ')."""
    if '-' in (desrut or ''):
        a, b = desrut.split('-', 1)
        return a.strip(), b.strip()
    return (desrut or '').strip(), ''


# Mapa codofi -> desofi, cacheado (las oficinas son estables).
_MAPA_OFI = {'ts': 0, 'map': {}}


def mapa_oficinas() -> dict:
    """{codofi: desofi}, cacheado 10 min."""
    ahora = time.time()
    if not _MAPA_OFI['map'] or (ahora - _MAPA_OFI['ts']) > 600:
        try:
            _MAPA_OFI['map'] = {
                o.get('codofi'): o.get('desofi')
                for o in consultar_oficinas() if o.get('codofi')
            }
            _MAPA_OFI['ts'] = ahora
        except AerorutasError:
            pass
    return _MAPA_OFI['map']


def viaje_shape(ruta: dict, inicio: str, fin: str, fecha: str, asientos_disponibles=None) -> dict:
    """Una ruta de Aerorutas con el MISMO shape que ViajeListSerializer/Detail.

    origen/destino = las OFICINAS del tramo elegido (inicio/fin). El `desrut`
    (nombre de la línea completa) se muestra como 'autobús'.
    """
    m = mapa_oficinas()
    origen = m.get(inicio) or inicio
    destino = m.get(fin) or fin
    precio = (str(ruta.get('precio', '') or '')).strip() or '0'
    return {
        'id': viaje_id(ruta.get('codrut', ''), inicio, fin, fecha),
        'codrut': ruta.get('codrut', ''),
        'tipo_viaje': 'ida',
        'fecha_salida': fecha,
        'hora_salida': parse_hora(ruta.get('hora', '')),
        'fecha_vuelta': None,
        'hora_vuelta': None,
        'precio_usd': precio,
        'activo': True,
        'asientos_disponibles': asientos_disponibles,
        'fecha_inicio_venta': None,
        'fecha_fin_venta': None,
        'ruta': {'origen': origen, 'destino': destino, 'duracion_estimada': ''},
        'autobus': {'nombre': ruta.get('desrut', ''), 'disponible': True,
                    'motivo_no_disponible': ''},
    }


def pisos_shape(puestos: list, asientos_por_fila: int = 4) -> list:
    """
    Lista de puestos LIBRES (BUSQPUESTO) → pisos_config de UN piso.

    - Aerorutas solo devuelve los libres → dibujamos del 1 al mayor asiento y
      marcamos como ocupado (disponible=False) los que no estén en la lista.
    - Distribución 2 + PASILLO + 2: insertamos una celda 'aisle' en medio de
      cada fila para que se vea el pasillo del bus.
    """
    disponibles = set()
    for p in puestos:
        try:
            disponibles.add(int(p.get('puesto')))
        except (TypeError, ValueError):
            continue

    columnas = asientos_por_fila + 1  # +1 por el pasillo
    if not disponibles:
        return [{'numero_piso': 1, 'filas': 0, 'columnas': columnas,
                 'layout': [], 'capacidad': 0}]

    mitad = asientos_por_fila // 2
    total = max(disponibles)  # el bus llega hasta el asiento más alto visto libre

    def _fila_con_pasillo(asientos):
        # asientos[:mitad] + pasillo + asientos[mitad:]
        fila = asientos[:mitad] + [{'type': 'aisle'}] + asientos[mitad:]
        while len(fila) < columnas:
            fila.append({'type': 'empty'})
        return fila

    layout, buffer = [], []
    for n in range(1, total + 1):
        buffer.append({'type': 'seat', 'number': n, 'disponible': n in disponibles})
        if len(buffer) == asientos_por_fila:
            layout.append(_fila_con_pasillo(buffer))
            buffer = []
    if buffer:
        layout.append(_fila_con_pasillo(buffer))

    return [{
        'numero_piso': 1,
        'filas': len(layout),
        'columnas': columnas,
        'layout': layout,
        'capacidad': len(disponibles),
    }]


def apartar_puesto(fecha: str, codrut: str, nroasi: str, ofisal: str, ofides: str):
    """
    Aparta un puesto temporalmente mientras se completa la transacción (TMPPUESTO).
    Devuelve (items_parseados, texto_crudo) porque el formato de respuesta no se
    ha verificado; el crudo permite inspeccionar lo que devuelva el banco.
    """
    raw = _get_raw('TMPPUESTO', fecha=fecha, codrut=codrut,
                   nroasi=nroasi, ofisal=ofisal, ofides=ofides)
    return parse_items(raw), raw
