"""Qué salidas existen, cómo van de puestos y por qué (no) se ven en la página.

Junta los dos mundos que alimentan la web y la app:

  · Viajes PROPIOS (modelo `Viaje`): salen de nuestra base, así que los números
    son exactos.
  · Catálogo de AERORUTAS (`RutaAerorutasSnapshot`): lo que publica el sistema
    de la empresa para esa fecha. De ahí vienen el precio y los puestos libres.

Las reglas de "se ve / no se ve" son las MISMAS que aplican las vistas públicas
(`ViajeListView` y `AerorutasViajesView`). Si cambian allá hay que cambiarlas
aquí: esta pantalla existe para explicar por qué una salida no aparece, y
mentiría si se desincronizara.
"""
from django.db.models import Count, Q
from django.utils import timezone

from viajes.models import Ruta, RutaAerorutasSnapshot, Viaje

# Una reserva en cualquiera de estos estados ocupa el puesto.
ESTADOS_OCUPAN = ['pendiente', 'apartado', 'confirmado']


def _num(valor):
    """A número, tolerando None, '' y basura ('' → 0.0)."""
    try:
        return float(valor or 0)
    except (TypeError, ValueError):
        return 0.0


def _fila(**kw):
    """Fila de la tabla. Un solo sitio donde están todas las claves."""
    fila = {
        'fuente': 'propio',      # propio | aerorutas
        'origen': '', 'destino': '', 'hora': '', 'autobus': '',
        'precio': 0.0,
        'capacidad': None,       # None = no se sabe (Aerorutas no la publica)
        'ocupados': None,
        'disponibles': None,
        'ocupados_es_parcial': False,   # en Aerorutas solo sabemos LO NUESTRO
        'visible': True,
        'motivos': [],           # por qué NO se ve
        'problemas': [],         # cosas mal aunque sí se vea
        'viaje_id': None,
    }
    fila.update(kw)
    return fila


# ══════════════════════════════════════════════════════════════════
#  Viajes propios
# ══════════════════════════════════════════════════════════════════

def salidas_propias(fecha, hoy=None):
    hoy = hoy or timezone.localdate()

    qs = (Viaje.objects
          .select_related('ruta', 'autobus')
          .prefetch_related('autobus__pisos_config')
          .filter(fecha_salida=fecha)
          .annotate(ocupados=Count('reservas',
                                   filter=Q(reservas__estado__in=ESTADOS_OCUPAN)))
          .order_by('ruta__origen', 'ruta__destino', 'hora_salida'))

    filas = []
    for v in qs:
        capacidad = v.autobus.capacidad_total
        precio = _num(v.precio_usd)
        motivos, problemas = [], []

        # ── Por qué no se ve (mismas reglas que ViajeListView) ──
        if v.aerorutas_codrut:
            motivos.append('Es el espejo de un viaje de Aerorutas: en la página '
                           'se muestra el del catálogo, no este.')
        if not v.activo:
            motivos.append('Está desactivado.')
        if v.fecha_salida < hoy:
            motivos.append('La fecha ya pasó.')
        if v.fecha_inicio_venta and v.fecha_inicio_venta > hoy:
            motivos.append('La venta abre el %s.' % v.fecha_inicio_venta.strftime('%d/%m/%Y'))
        if v.fecha_fin_venta and v.fecha_fin_venta < hoy:
            motivos.append('La venta cerró el %s.' % v.fecha_fin_venta.strftime('%d/%m/%Y'))

        # ── Cosas mal que NO lo ocultan (por eso pasan desapercibidas) ──
        if precio <= 0:
            problemas.append('Sin precio: se publica en $0.00.')
        if capacidad == 0:
            problemas.append('El autobús no tiene puestos dibujados: nadie puede comprar.')
        elif v.ocupados >= capacidad:
            problemas.append('Lleno, no quedan puestos.')
        if not v.autobus.disponible:
            problemas.append('El autobús está marcado como NO disponible (%s).'
                             % (v.autobus.motivo_no_disponible or 'sin motivo anotado'))

        filas.append(_fila(
            fuente='propio',
            origen=v.ruta.origen, destino=v.ruta.destino,
            hora=v.hora_salida.strftime('%H:%M') if v.hora_salida else '',
            autobus=v.autobus.nombre,
            precio=precio,
            capacidad=capacidad,
            ocupados=v.ocupados,
            disponibles=max(capacidad - v.ocupados, 0),
            visible=not motivos,
            motivos=motivos, problemas=problemas,
            viaje_id=v.pk,
        ))
    return filas


# ══════════════════════════════════════════════════════════════════
#  Catálogo de Aerorutas
# ══════════════════════════════════════════════════════════════════

def _ocupados_nuestros(fecha):
    """Puestos que hemos vendido NOSOTROS de cada salida de Aerorutas.

    Viven en los viajes espejo, que se crean al ver los asientos. Un viaje del
    catálogo sin espejo simplemente no tiene ventas nuestras.
    """
    espejos = (Viaje.objects
               .filter(fecha_salida=fecha)
               .exclude(aerorutas_codrut='')
               .annotate(n=Count('reservas',
                                 filter=Q(reservas__estado__in=ESTADOS_OCUPAN)))
               .values_list('aerorutas_codrut', 'aerorutas_ofisal',
                            'aerorutas_ofides', 'n'))
    return {(c, i, f): n for c, i, f, n in espejos}


def salidas_aerorutas(fecha):
    snap = RutaAerorutasSnapshot.objects.filter(fecha=fecha).first()
    if not snap:
        return [], None

    nuestros = _ocupados_nuestros(fecha)
    filas = []
    for v in (snap.data or []):
        ruta = v.get('ruta') or {}
        precio = _num(v.get('precio_usd'))
        disponibles = v.get('asientos_disponibles')
        motivos, problemas = [], []

        # Única regla de la vista pública: sin precio no se publica.
        if precio <= 0:
            motivos.append('Aerorutas no publica precio para este tramo, así que '
                           'la página lo oculta.')

        if disponibles is None:
            problemas.append('No se pudo consultar la disponibilidad en Aerorutas.')
        elif disponibles == 0:
            problemas.append('Lleno, no quedan puestos.')

        # El id trae codrut_ofisal_ofides_fecha; de ahí sale el espejo.
        partes = str(v.get('id') or '').split('_', 3)
        clave = tuple(partes[:3]) if len(partes) >= 3 else None
        ocupados = nuestros.get(clave)

        filas.append(_fila(
            fuente='aerorutas',
            origen=ruta.get('origen', ''), destino=ruta.get('destino', ''),
            hora=(v.get('hora_salida') or '')[:5],
            autobus=(v.get('autobus') or {}).get('nombre', ''),
            precio=precio,
            capacidad=None,          # Aerorutas no publica el total del bus
            ocupados=ocupados,
            disponibles=disponibles,
            ocupados_es_parcial=True,
            visible=not motivos,
            motivos=motivos, problemas=problemas,
            viaje_id=v.get('id'),
        ))
    return filas, snap.actualizado


# ══════════════════════════════════════════════════════════════════
#  Armado de la pantalla
# ══════════════════════════════════════════════════════════════════

def analizar(fecha, origen='', destino='', filtro='', hoy=None):
    """Todo lo que necesita la plantilla para una fecha.

    `filtro`: '' (todo) | 'ocultas' | 'problemas' | 'sin_precio'
    """
    hoy = hoy or timezone.localdate()

    propias = salidas_propias(fecha, hoy=hoy)
    aero, actualizado = salidas_aerorutas(fecha)
    filas = propias + aero

    # El resumen se calcula ANTES de filtrar: si no, decir "3 ocultas" mientras
    # se está viendo justamente el filtro de ocultas no informa de nada.
    resumen = {
        'total': len(filas),
        'visibles': sum(1 for f in filas if f['visible']),
        'ocultas': sum(1 for f in filas if not f['visible']),
        # Publicadas PERO con algo mal: son las peligrosas, porque el cliente
        # las ve y las compra igual (sin precio, bus en taller, sin puestos).
        'con_defecto': sum(1 for f in filas if f['visible'] and f['problemas']),
        'sin_precio': sum(1 for f in filas if f['precio'] <= 0),
        'propias': len(propias),
        'aerorutas': len(aero),
    }

    origen = (origen or '').strip().lower()
    destino = (destino or '').strip().lower()
    if origen:
        filas = [f for f in filas if origen in f['origen'].lower()]
    if destino:
        filas = [f for f in filas if destino in f['destino'].lower()]
    if filtro == 'ocultas':
        filas = [f for f in filas if not f['visible']]
    elif filtro == 'problemas':
        filas = [f for f in filas if f['problemas'] or not f['visible']]
    elif filtro == 'sin_precio':
        filas = [f for f in filas if f['precio'] <= 0]

    filas.sort(key=lambda f: (f['origen'], f['destino'], f['hora']))

    return {
        'filas': filas,
        'resumen': resumen,
        'hay_catalogo': bool(aero),
        'catalogo_actualizado': actualizado,
        'pares': _pares(filas),
        'rutas_sin_salidas': rutas_sin_salidas(fecha),
    }


def _pares(filas):
    """Los "desde → hasta" distintos que hay, con su resumen."""
    pares = {}
    for f in filas:
        clave = (f['origen'], f['destino'])
        p = pares.setdefault(clave, {
            'origen': f['origen'], 'destino': f['destino'],
            'salidas': 0, 'visibles': 0, 'precio_min': None, 'precio_max': None,
            'disponibles': 0, 'sin_disponibilidad': False,
        })
        p['salidas'] += 1
        if f['visible']:
            p['visibles'] += 1
        if f['precio'] > 0:
            p['precio_min'] = f['precio'] if p['precio_min'] is None else min(p['precio_min'], f['precio'])
            p['precio_max'] = f['precio'] if p['precio_max'] is None else max(p['precio_max'], f['precio'])
        if f['disponibles'] is None:
            p['sin_disponibilidad'] = True
        else:
            p['disponibles'] += f['disponibles']
    return sorted(pares.values(), key=lambda p: (p['origen'], p['destino']))


def rutas_sin_salidas(fecha):
    """Rutas dadas de alta que ese día no tienen ningún viaje propio.

    No es un error por sí solo (puede que ese día simplemente no salga), pero
    explica por qué un par que "existe" no aparece por ningún lado.
    """
    con_viaje = set(Viaje.objects.filter(fecha_salida=fecha)
                    .values_list('ruta_id', flat=True))
    return list(Ruta.objects.exclude(id__in=con_viaje).order_by('origen', 'destino'))
