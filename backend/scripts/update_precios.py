"""
Script para actualizar los precios de TODOS los viajes existentes
segun la lista de precios oficial de Aerorutas de Venezuela.

Ejecutar: python update_precios.py
"""
import os, sys, io, django

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from viajes.models import Viaje, Ruta

# ═══════════════════════════════════════════════════════════
# LISTA DE PRECIOS OFICIAL - AERORUTAS DE VENEZUELA
# Clave: (origen_contiene, destino_contiene) → precio_usd
# Se busca coincidencia parcial (case-insensitive)
# ═══════════════════════════════════════════════════════════

PRECIOS = {
    # ── OFICINA CARACAS ──
    ('Caracas', 'San Cristóbal'): 35,
    ('Caracas', 'Valera'): 25,
    ('Caracas', 'Maracaibo'): 28,
    ('Caracas', 'Mérida'): 35,
    ('Caracas', 'Barinas'): 25,
    ('Caracas', 'El Vigía'): 28,

    # ── OFICINA MARACAY ──
    ('Maracay', 'San Cristóbal'): 35,
    ('Maracay', 'Socopo'): 25,
    ('Maracay', 'Barinas'): 15,
    ('Maracay', 'Mérida'): 30,
    ('Maracay', 'El Vigía'): 25,
    ('Maracay', 'Valera'): 25,
    ('Maracay', 'Trujillo'): 25,
    ('Maracay', 'Maracaibo'): 32,
    ('Maracay', 'San Antonio'): 45,

    # ── OFICINA VALENCIA ──
    ('Valencia', 'San Cristóbal'): 35,
    ('Valencia', 'Barinas'): 15,
    ('Valencia', 'Mérida'): 35,
    ('Valencia', 'El Vigía'): 30,
    ('Valencia', 'Valera'): 25,
    ('Valencia', 'Maracaibo'): 32,

    # ── OFICINA LOS TEQUES ──
    ('Los Teques', 'San Cristóbal'): 40,
    ('Los Teques', 'Barinas'): 25,
    ('Los Teques', 'Socopo'): 30,
    ('Los Teques', 'Pedrera'): 30,
    ('Los Teques', 'El Piñal'): 30,

    # ── OFICINA PUERTO LA CRUZ ──
    ('Puerto La Cruz', 'Caracas'): 15,
    ('Puerto La Cruz', 'Maracay'): 20,
    ('Puerto La Cruz', 'Valencia'): 25,
    ('Puerto La Cruz', 'Barinas'): 30,
    ('Puerto La Cruz', 'Santa Bárbara'): 35,
    ('Puerto La Cruz', 'Socopo'): 40,
    ('Puerto La Cruz', 'El Piñal'): 50,
    ('Puerto La Cruz', 'San Cristóbal'): 50,
    ('Puerto La Cruz', 'San Antonio'): 57,
    ('Puerto La Cruz', 'Barquisimeto'): 30,
    ('Puerto La Cruz', 'Maracaibo'): 55,

    # ── OFICINA BARINAS ──
    ('Barinas', 'Caracas'): 25,
    ('Barinas', 'Valencia'): 15,
    ('Barinas', 'Maracay'): 17,
    ('Barinas', 'Puerto La Cruz'): 35,

    # ── OFICINA PTO. PIRITU ──
    ('Puerto Píritu', 'Caracas'): 12,
    ('Puerto Píritu', 'Maracay'): 20,
    ('Puerto Píritu', 'Valencia'): 20,
    ('Puerto Píritu', 'Barquisimeto'): 30,
    ('Puerto Píritu', 'Maracaibo'): 45,
    ('Puerto Píritu', 'Barinas'): 30,
    ('Puerto Píritu', 'San Cristóbal'): 45,
    ('Pto. Píritu', 'Caracas'): 12,
    ('Pto. Píritu', 'Maracay'): 20,
    ('Pto. Píritu', 'Valencia'): 20,
    ('Pto. Píritu', 'Barquisimeto'): 30,
    ('Pto. Píritu', 'Maracaibo'): 45,
    ('Pto. Píritu', 'Barinas'): 30,
    ('Pto. Píritu', 'San Cristóbal'): 45,

    # ── OFICINA MARACAIBO ──
    ('Maracaibo', 'Caracas'): 35,
    ('Maracaibo', 'Maracay'): 32,
    ('Maracaibo', 'Valencia'): 32,
    ('Maracaibo', 'Puerto La Cruz'): 55,

    # ── OFICINA SAN CRISTÓBAL ──
    ('San Cristóbal', 'Caracas'): 35,
    ('San Cristóbal', 'Maracay'): 35,
    ('San Cristóbal', 'Barinas'): 20,
    ('San Cristóbal', 'Puerto La Cruz'): 55,
    ('San Cristóbal', 'Los Teques'): 35,

    # ── OFICINA EL PIÑAL ──
    ('El Piñal', 'Caracas'): 30,
    ('El Piñal', 'Valencia'): 30,
    ('El Piñal', 'Maracay'): 30,
    ('El Piñal', 'Puerto La Cruz'): 45,

    # ── OFICINA SANTA BÁRBARA ──
    ('Santa Bárbara', 'Caracas'): 22,
    ('Santa Bárbara', 'Valencia'): 22,
    ('Santa Bárbara', 'Maracay'): 22,
    ('Santa Bárbara', 'Puerto La Cruz'): 45,
    ('Santa Barbara', 'Caracas'): 22,
    ('Santa Barbara', 'Valencia'): 22,
    ('Santa Barbara', 'Maracay'): 22,
    ('Santa Barbara', 'Puerto La Cruz'): 45,

    # ── OFICINA SOCOPO ──
    ('Socopo', 'Caracas'): 25,
    ('Socopo', 'Valencia'): 25,
    ('Socopo', 'Maracay'): 25,
    ('Socopo', 'Puerto La Cruz'): 40,

    # ── OFICINA VALERA ──
    ('Valera', 'Caracas'): 25,
    ('Valera', 'Valencia'): 25,
    ('Valera', 'Maracay'): 25,

    # ── OFICINA TRUJILLO ──
    ('Trujillo', 'Caracas'): 25,
    ('Trujillo', 'Valencia'): 25,
    ('Trujillo', 'Maracay'): 25,

    # ── OFICINA EL CRUCE ──
    ('El Cruce', 'Caracas'): 25,
    ('El Cruce', 'Valencia'): 25,
    ('El Cruce', 'Maracay'): 25,

    # ── OFICINA MONAY ──
    ('Monay', 'Caracas'): 25,
    ('Monay', 'Valencia'): 25,
    ('Monay', 'Maracay'): 25,

    # ── OFICINA MÉRIDA ──
    ('Mérida', 'Caracas'): 30,
    ('Mérida', 'Valencia'): 25,
    ('Mérida', 'Maracay'): 25,
    ('Mérida', 'Los Teques'): 30,
    ('Mérida', 'Barquisimeto'): 25,
    ('Mérida', 'Maracaibo'): 25,  # actualizado (estaba en seed como 25)

    # ── OFICINA EL VIGÍA ──
    ('El Vigía', 'Caracas'): 30,
    ('El Vigía', 'Valencia'): 30,
    ('El Vigía', 'Maracay'): 30,

    # ── OFICINA CAÑO ZANCUDO ──
    ('Caño Zancudo', 'Caracas'): 25,
    ('Caño Zancudo', 'Valencia'): 25,
    ('Caño Zancudo', 'Maracay'): 25,

    # ── OFICINA TUCANÍ ──
    ('Tucaní', 'Caracas'): 25,
    ('Tucaní', 'Valencia'): 25,
    ('Tucaní', 'Maracay'): 25,
    ('Tucani', 'Caracas'): 25,
    ('Tucani', 'Valencia'): 25,
    ('Tucani', 'Maracay'): 25,

    # ── OFICINA ARAPUEY ──
    ('Arapuey', 'Caracas'): 20,
    ('Arapuey', 'Valencia'): 20,
    ('Arapuey', 'Maracay'): 20,

    # ── OFICINA CAJA SECA ──
    ('Caja Seca', 'Caracas'): 25,
    ('Caja Seca', 'Valencia'): 25,
    ('Caja Seca', 'Maracay'): 25,
    ('Caja Seca', 'Barquisimeto'): 15,

    # ── OFICINA SAN ANTONIO ──
    ('San Antonio', 'Caracas'): 45,
    ('San Antonio', 'Valencia'): 45,
    ('San Antonio', 'Maracay'): 45,
    ('San Antonio', 'Puerto La Cruz'): 55,
    ('San Antonio', 'Barinas'): 30,
    ('San Antonio', 'Los Teques'): 45,
}


def normalizar(texto):
    """Normaliza texto para comparación flexible."""
    import unicodedata
    texto = texto.strip().lower()
    # Remover acentos
    nfkd = unicodedata.normalize('NFKD', texto)
    return ''.join(c for c in nfkd if not unicodedata.combining(c))


def buscar_precio(origen, destino):
    """Busca el precio para un par origen-destino usando coincidencia flexible."""
    origen_norm = normalizar(origen)
    destino_norm = normalizar(destino)

    for (key_origen, key_destino), precio in PRECIOS.items():
        ko = normalizar(key_origen)
        kd = normalizar(key_destino)

        # Coincidencia exacta primero
        if ko == origen_norm and kd == destino_norm:
            return precio

        # Coincidencia parcial (el origen/destino de la ruta CONTIENE la clave)
        if (ko in origen_norm or origen_norm in ko) and \
           (kd in destino_norm or destino_norm in kd):
            return precio

    # Intentar con "La Bandera" → "Caracas"
    if 'bandera' in origen_norm or 'caracas' in origen_norm:
        for (key_origen, key_destino), precio in PRECIOS.items():
            ko = normalizar(key_origen)
            kd = normalizar(key_destino)
            if ko == 'caracas' and (kd in destino_norm or destino_norm in kd):
                return precio

    if 'bandera' in destino_norm or 'caracas' in destino_norm:
        for (key_origen, key_destino), precio in PRECIOS.items():
            ko = normalizar(key_origen)
            kd = normalizar(key_destino)
            if (ko in origen_norm or origen_norm in ko) and kd == 'caracas':
                return precio

    return None


# ═══════════════════════════════════════════════════════════
# ACTUALIZAR PRECIOS DE TODOS LOS VIAJES
# ═══════════════════════════════════════════════════════════
print("=" * 60)
print("💰 ACTUALIZANDO PRECIOS - AERORUTAS DE VENEZUELA")
print("=" * 60)

viajes = Viaje.objects.select_related('ruta').all()
actualizados = 0
sin_precio = []

for viaje in viajes:
    origen = viaje.ruta.origen
    destino = viaje.ruta.destino
    precio_nuevo = buscar_precio(origen, destino)

    if precio_nuevo is not None:
        precio_anterior = float(viaje.precio_usd)
        if precio_anterior != float(precio_nuevo):
            viaje.precio_usd = precio_nuevo
            viaje.save(update_fields=['precio_usd'])
            actualizados += 1
            print(f"   ✅ {origen} → {destino}: ${precio_anterior:.2f} → ${precio_nuevo:.2f}")
        else:
            pass  # Ya tiene el precio correcto
    else:
        ruta_key = f"{origen} → {destino}"
        if ruta_key not in sin_precio:
            sin_precio.append(ruta_key)
            print(f"   ⚠️  Sin precio definido: {ruta_key} (precio actual: ${float(viaje.precio_usd):.2f})")

print(f"\n{'=' * 60}")
print(f"📊 RESUMEN")
print(f"{'=' * 60}")
print(f"   Total viajes en DB:  {viajes.count()}")
print(f"   Precios actualizados: {actualizados}")
if sin_precio:
    print(f"   Rutas sin precio definido: {len(sin_precio)}")
    for ruta in sin_precio:
        print(f"      - {ruta}")
print(f"{'=' * 60}")
print("🎉 ¡Actualización de precios completada!")
