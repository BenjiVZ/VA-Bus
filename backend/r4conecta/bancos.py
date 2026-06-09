"""
Listado centralizado de códigos de banco (R4 Conecta / SUDEBAN).
Fuente única de verdad: lo consumen la web y la app móvil vía GET /api/r4/bancos/.
"""

BANCOS = [
    {"codigo": "0102", "nombre": "Banco de Venezuela"},
    {"codigo": "0104", "nombre": "Banco Venezolano de Crédito"},
    {"codigo": "0105", "nombre": "Banco Mercantil"},
    {"codigo": "0108", "nombre": "Banco Provincial (BBVA)"},
    {"codigo": "0114", "nombre": "Banco del Caribe (Bancaribe)"},
    {"codigo": "0115", "nombre": "Banco Exterior"},
    {"codigo": "0128", "nombre": "Banco Caroní"},
    {"codigo": "0134", "nombre": "Banesco"},
    {"codigo": "0137", "nombre": "Banco Sofitasa"},
    {"codigo": "0138", "nombre": "Banco Plaza"},
    {"codigo": "0146", "nombre": "Banco de la Gente Emprendedora (Bangente)"},
    {"codigo": "0151", "nombre": "Banco Fondo Común (BFC)"},
    {"codigo": "0156", "nombre": "100% Banco"},
    {"codigo": "0157", "nombre": "DelSur Banco Universal"},
    {"codigo": "0163", "nombre": "Banco del Tesoro"},
    {"codigo": "0166", "nombre": "Banco Agrícola de Venezuela"},
    {"codigo": "0168", "nombre": "Bancrecer"},
    {"codigo": "0169", "nombre": "R4 Banco Microfinanciero"},
    {"codigo": "0171", "nombre": "Banco Activo"},
    {"codigo": "0172", "nombre": "Bancamiga"},
    {"codigo": "0173", "nombre": "Banco Internacional de Desarrollo"},
    {"codigo": "0174", "nombre": "Banplus"},
    {"codigo": "0175", "nombre": "Banco Digital de los Trabajadores"},
    {"codigo": "0177", "nombre": "Banco de la Fuerza Armada Nacional Bolivariana (BANFANB)"},
    {"codigo": "0178", "nombre": "N58 Banco Digital"},
    {"codigo": "0191", "nombre": "Banco Nacional de Crédito (BNC)"},
    {"codigo": "0601", "nombre": "Instituto Municipal de Crédito Popular"},
]

CODIGOS_VALIDOS = {b["codigo"] for b in BANCOS}
