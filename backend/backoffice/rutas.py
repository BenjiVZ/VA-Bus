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
import re

from django.db.models import Count, Q
from django.utils import timezone

from viajes.models import Ruta, RutaAerorutasSnapshot, Viaje

# Una reserva en cualquiera de estos estados ocupa el puesto.
ESTADOS_OCUPAN = ['pendiente', 'apartado', 'confirmado']

# El número de unidad va dentro del nombre: "VOLVO BLANCO 2006 (#26)".
# Se respetan los ceros a la izquierda: la flota los rotula "#08", no "#8".
_NUM_BUS = re.compile(r'\(\s*#\s*(\d+)\s*\)')


def _num(valor):
    """A número, tolerando None, '' y basura ('' → 0.0)."""
    try:
        return float(valor or 0)
    except (TypeError, ValueError):
        return 0.0


def _numero_bus(nombre, placa):
    """Número de la unidad: el "(#26)" del nombre; si no, la placa.

    No hay campo propio para el número en el modelo, así que se saca del
    nombre (que es donde lo escriben) y se cae a la placa, que sí es única.
    """
    m = _NUM_BUS.search(nombre or '')
    if m:
        return '#%s' % m.group(1)
    return (placa or '').strip()


def _fila(**kw):
    """Fila de la tabla. Un solo sitio donde están todas las claves.

    `tipo` decide el orden y qué se puede rellenar:
      salida            · una salida de verdad (propia o de Aerorutas)
      ruta_sin_salidas  · la ruta existe pero ese día no sale nada
      bus_sin_viaje     · el autobús no está puesto en ninguna salida
    """
    fila = {
        'tipo': 'salida',
        'orden': 0,
        'fuente': 'propio',      # propio | aerorutas
        'codrut': '',            # nº de ruta/línea (codrut en Aerorutas)
        'num_bus': '',           # nº de unidad ("#26") o, si no lo tiene, la placa
        'origen': '', 'destino': '', 'hora': '', 'autobus': '', 'placa': '',
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
        if not (v.ruta.origen or '').strip() or not (v.ruta.destino or '').strip():
            problemas.append('La ruta está incompleta: le falta el origen o el destino.')

        filas.append(_fila(
            fuente='propio',
            # En los propios no hay "número de línea" como en Aerorutas; lo más
            # parecido es el id de la ruta, que es con lo que se busca en el admin.
            codrut=v.aerorutas_codrut or ('R%s' % v.ruta_id),
            num_bus=_numero_bus(v.autobus.nombre, v.autobus.placa),
            origen=v.ruta.origen, destino=v.ruta.destino,
            hora=v.hora_salida.strftime('%H:%M') if v.hora_salida else '',
            autobus=v.autobus.nombre, placa=v.autobus.placa,
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

        if not (ruta.get('origen') or '').strip() or not (ruta.get('destino') or '').strip():
            problemas.append('Aerorutas no devolvió el nombre de la oficina de '
                             'origen o destino para este tramo.')
        if not (v.get('autobus') or {}).get('nombre'):
            problemas.append('Sin línea/autobús en el catálogo de Aerorutas.')

        # El id trae codrut_ofisal_ofides_fecha; de ahí sale el espejo.
        partes = str(v.get('id') or '').split('_', 3)
        clave = tuple(partes[:3]) if len(partes) >= 3 else None
        ocupados = nuestros.get(clave)

        filas.append(_fila(
            fuente='aerorutas',
            codrut=str(v.get('codrut') or ''),
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
    salidas = propias + aero
    cubiertas = {(f['origen'].strip().lower(), f['destino'].strip().lower())
                 for f in salidas}
    sueltas = rutas_sin_salidas(fecha, cubiertas) + buses_sin_viaje(fecha)
    filas = salidas + sueltas

    # El resumen se calcula ANTES de filtrar: si no, decir "3 ocultas" mientras
    # se está viendo justamente el filtro de ocultas no informa de nada.
    # Cuenta SALIDAS: las rutas y los buses sueltos no son salidas, meterlos
    # inflaría el total y "ocultas" dejaría de significar nada.
    resumen = {
        'total': len(salidas),
        'visibles': sum(1 for f in salidas if f['visible']),
        'ocultas': sum(1 for f in salidas if not f['visible']),
        # Publicadas PERO con algo mal: son las peligrosas, porque el cliente
        # las ve y las compra igual (sin precio, bus en taller, sin puestos).
        'con_defecto': sum(1 for f in salidas if f['visible'] and f['problemas']),
        'sin_precio': sum(1 for f in salidas if f['precio'] <= 0),
        'propias': len(propias),
        'aerorutas': len(aero),
        'sueltas': len(sueltas),
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
        filas = [f for f in filas if f['tipo'] == 'salida' and f['precio'] <= 0]
    elif filtro == 'salidas':
        filas = [f for f in filas if f['tipo'] == 'salida']

    # Primero las salidas (por ruta y hora), después lo que quedó suelto.
    filas.sort(key=lambda f: (f['orden'], f['origen'], f['destino'],
                              f['hora'], f['autobus']))

    return {
        'filas': filas,
        'resumen': resumen,
        'hay_catalogo': bool(aero),
        'catalogo_actualizado': actualizado,
    }


def rutas_sin_salidas(fecha, cubiertas=frozenset()):
    """Rutas dadas de alta que ese día no salen por ningún lado.

    No es un error por sí solo (puede que ese día simplemente no salga), pero
    explica por qué un par que "existe" no aparece.

    `cubiertas`: pares (origen, destino) en minúsculas que YA aparecen como
    salida. Hace falta porque cada par de Aerorutas deja una `Ruta` local
    creada por el viaje espejo: sin este filtro, un par que el catálogo sí
    publica ese día saldría listado como "no tiene ninguna salida", justo
    debajo de su propia salida. Contradecirse sería peor que no informar.
    """
    con_viaje = set(Viaje.objects.filter(fecha_salida=fecha)
                    .values_list('ruta_id', flat=True))
    filas = []
    for r in Ruta.objects.exclude(id__in=con_viaje).order_by('origen', 'destino'):
        if ((r.origen or '').strip().lower(),
                (r.destino or '').strip().lower()) in cubiertas:
            continue
        problemas = []
        if not (r.origen or '').strip() or not (r.destino or '').strip():
            problemas.append('La ruta está incompleta: le falta el origen o el destino.')
        filas.append(_fila(
            tipo='ruta_sin_salidas', orden=1,
            codrut='R%s' % r.pk,
            origen=r.origen, destino=r.destino,
            visible=False,
            motivos=['No tiene ninguna salida cargada ese día, así que no '
                     'aparece por ningún lado.'],
            problemas=problemas,
        ))
    return filas


def buses_sin_viaje(fecha):
    """Autobuses que ese día no están puestos en ninguna salida.

    Van en la misma lista porque la pregunta es la misma: por qué no se está
    vendiendo algo. Un bus parado con puestos dibujados es capacidad ociosa;
    uno sin puestos dibujados no serviría ni asignándolo.
    """
    from viajes.models import Autobus

    ocupados = set(Viaje.objects.filter(fecha_salida=fecha)
                   .values_list('autobus_id', flat=True))
    filas = []
    # Los "AR-<codrut>" no son flota: los crea solo el espejo de Aerorutas para
    # poder bloquear puestos. Listarlos como buses parados sería puro ruido.
    for b in (Autobus.objects.exclude(id__in=ocupados)
              .exclude(placa__startswith='AR-')
              .prefetch_related('pisos_config').order_by('nombre')):
        problemas = []
        capacidad = b.capacidad_total
        if capacidad == 0:
            problemas.append('No tiene puestos dibujados: aunque se le asigne '
                             'una ruta, nadie podría comprar.')
        if not b.disponible:
            problemas.append('Marcado como NO disponible (%s).'
                             % (b.motivo_no_disponible or 'sin motivo anotado'))
        filas.append(_fila(
            tipo='bus_sin_viaje', orden=2,
            num_bus=_numero_bus(b.nombre, b.placa),
            autobus=b.nombre, placa=b.placa,
            capacidad=capacidad, ocupados=0, disponibles=0,
            visible=False,
            motivos=['No está asignado a ninguna salida ese día.'],
            problemas=problemas,
        ))
    return filas
