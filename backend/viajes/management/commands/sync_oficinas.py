"""
Sincroniza las oficinas/sucursales desde el sistema externo de Aerorutas.

Uso:
    python manage.py sync_oficinas
    python manage.py sync_oficinas --url <url> --token <token>
    python manage.py sync_oficinas --json '{"items":[...]}'   # pegar JSON directo
    python manage.py sync_oficinas --dry-run                  # ver qué pasaría sin guardar

El endpoint externo devuelve:
    {"items": [{"codofi": 01, "desofi": "VALERA", "siglas": "VLR"}, ...]}

Este comando hace upsert por `codofi`. Si la oficina ya existe se actualiza
desofi y siglas. Si no existe, se crea. Marca la fecha_sincronizacion.

También intenta autocompletar `estado` y `ciudad` desde un catálogo local.
"""
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

from django.core.management.base import BaseCommand
from django.db import transaction
from viajes.models import Oficina


DEFAULT_URL = (
    'https://aerorutasdevenezuela.com/server/request.php'
    '?token=B80A6A8758F4&consul=OFICINAS'
)


# Catálogo local: mapeo desofi → (estado, ciudad)
# Si una oficina no está acá, queda con estado/ciudad vacíos (se puede llenar en admin).
OFICINA_METADATA = {
    'VALERA':              ('Trujillo', 'Valera'),
    'SAN CRISTOBAL':       ('Tachira', 'San Cristobal'),
    'MARACAIBO':           ('Zulia', 'Maracaibo'),
    'CARACAS LA BANDERA':  ('Distrito Capital', 'Caracas'),
    'TRUJILLO':            ('Trujillo', 'Trujillo'),
    'MARACAY':             ('Aragua', 'Maracay'),
    'LOS TEQUES':          ('Miranda', 'Los Teques'),
    'MERIDA':              ('Merida', 'Merida'),
    'EL VIGIA':            ('Merida', 'El Vigia'),
    'CAÑO SANCUDO':        ('Zulia', 'Caño Sancudo'),
    'OFICINA PRINCIPAL':   ('Distrito Capital', 'Caracas'),
    'SOCOPO':              ('Barinas', 'Socopo'),
    'SANTA BARBARA':       ('Zulia', 'Santa Barbara'),
    'VALENCIA':            ('Carabobo', 'Valencia'),
    'ARAPUEY':             ('Merida', 'Arapuey'),
    'TUCANI':              ('Merida', 'Tucani'),
    'EL PINAL':            ('Tachira', 'El Pinal'),
    'BARINAS':             ('Barinas', 'Barinas'),
    'MONAY':               ('Trujillo', 'Monay'),
    'PUERTO LA CRUZ':      ('Anzoategui', 'Puerto La Cruz'),
    'PUERTO PIRITU':       ('Anzoategui', 'Puerto Piritu'),
    'CAJA SECA':           ('Zulia', 'Caja Seca'),
    'SAN ANTONIO':         ('Tachira', 'San Antonio'),
    'EL CRUZE':            ('', 'El Cruze'),
    'BARQUISIMETO':        ('Lara', 'Barquisimeto'),
}


class Command(BaseCommand):
    help = 'Sincroniza las oficinas desde el sistema externo de Aerorutas.'

    def add_arguments(self, parser):
        parser.add_argument('--url', default=DEFAULT_URL, help='URL del endpoint externo')
        parser.add_argument('--json', dest='json_data', help='JSON pegado directamente (ignora --url)')
        parser.add_argument('--dry-run', action='store_true', help='No guarda cambios, solo muestra')

    def handle(self, *args, **opts):
        # 1) Obtener payload
        if opts.get('json_data'):
            raw = opts['json_data']
            self.stdout.write('Usando JSON desde --json')
        else:
            url = opts['url']
            self.stdout.write(f'Descargando: {url}')
            try:
                with urllib.request.urlopen(url, timeout=15) as resp:
                    raw = resp.read().decode('utf-8', errors='replace')
            except urllib.error.URLError as e:
                self.stderr.write(f'[ERROR] No se pudo conectar: {e}')
                sys.exit(1)

        # 2) Parsear (tolerante: el endpoint a veces devuelve JSON mal formado
        #    con objetos sin comas/array. Lo normalizamos.)
        items = self._parse_items(raw)
        if not items:
            self.stderr.write('[ERROR] No se encontraron oficinas en la respuesta.')
            self.stderr.write(f'Primeros 200 chars: {raw[:200]}')
            sys.exit(2)

        self.stdout.write(f'Encontradas {len(items)} oficinas en la respuesta.')

        # 3) Upsert
        creadas = 0
        actualizadas = 0
        errores = []
        now = datetime.now(timezone.utc)

        with transaction.atomic():
            for item in items:
                try:
                    codofi = str(item.get('codofi', '')).strip()
                    desofi = str(item.get('desofi', '')).strip()
                    siglas = str(item.get('siglas', '')).strip()
                    if not codofi or not desofi:
                        errores.append(f'Item sin codofi/desofi: {item}')
                        continue

                    estado, ciudad = OFICINA_METADATA.get(desofi.upper(), ('', ''))

                    oficina, created = Oficina.objects.update_or_create(
                        codofi=codofi,
                        defaults={
                            'desofi': desofi,
                            'siglas': siglas,
                            'estado': estado,
                            'ciudad': ciudad,
                            'fecha_sincronizacion': now,
                        },
                    )
                    if created:
                        creadas += 1
                        self.stdout.write(f'  + {codofi}  {desofi}  ({siglas})')
                    else:
                        actualizadas += 1
                        self.stdout.write(f'  ~ {codofi}  {desofi}  ({siglas})')
                except Exception as e:
                    errores.append(f'Error con item {item}: {e}')

            if opts.get('dry_run'):
                transaction.set_rollback(True)
                self.stdout.write(self.style.WARNING('\n[DRY RUN] No se guardaron cambios.'))

        # 4) Resumen
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=== Sincronización completa ==='))
        self.stdout.write(f'  Creadas:      {creadas}')
        self.stdout.write(f'  Actualizadas: {actualizadas}')
        self.stdout.write(f'  Total en DB:  {Oficina.objects.count()}')
        if errores:
            self.stdout.write(self.style.WARNING(f'  Errores ({len(errores)}):'))
            for e in errores:
                self.stdout.write(f'    - {e}')

    def _parse_items(self, raw):
        """
        Intenta parsear el payload tolerando varios formatos:
          1) JSON válido: {"items": [{"codofi":"01",...}, ...]}
          2) JSON mal formado del API (sin comas entre objetos)
          3) Solo array: [{"codofi":...}, ...]
        """
        # Intento 1: JSON válido
        try:
            data = json.loads(raw)
            if isinstance(data, dict) and 'items' in data:
                items = data['items']
                if isinstance(items, list):
                    return items
                # Items puede ser un dict si el JSON está roto
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

        # Intento 2: extraer todos los objetos {...} con regex
        # Captura cada par {"codofi":..., "desofi":..., "siglas":...}
        pattern = r'\{\s*"codofi"\s*:\s*[^,}]+,\s*"desofi"\s*:\s*"[^"]*"\s*,\s*"siglas"\s*:\s*"[^"]*"\s*\}'
        matches = re.findall(pattern, raw)
        items = []
        for m in matches:
            try:
                items.append(json.loads(m))
            except json.JSONDecodeError:
                # Forzar comillas en codofi numérico: {"codofi":01,...} -> {"codofi":"01",...}
                fixed = re.sub(r'"codofi"\s*:\s*(\d+)', r'"codofi":"\1"', m)
                try:
                    items.append(json.loads(fixed))
                except json.JSONDecodeError:
                    continue
        return items
