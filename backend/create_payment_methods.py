from pagos.models import MetodoPago, DatoMetodoPago

MetodoPago.objects.all().delete()

m1 = MetodoPago.objects.create(
    nombre="Pago Movil Ejemplo",
    tipo="pago_movil",
    moneda="BS",
    descripcion="Pago movil banco de ejemplo",
    requiere_foto_billete=False,
    activo=True,
    orden=1
)
DatoMetodoPago.objects.create(metodo_pago=m1, etiqueta="Banco", valor="Banco de Ejemplo", orden=1)
DatoMetodoPago.objects.create(metodo_pago=m1, etiqueta="Telefono", valor="0414-0000000 (Ejemplo)", orden=2)
DatoMetodoPago.objects.create(metodo_pago=m1, etiqueta="Cedula", valor="V-0000000 (Ejemplo)", orden=3)

m2 = MetodoPago.objects.create(
    nombre="Zelle Ejemplo",
    tipo="zelle",
    moneda="USD",
    descripcion="Transferencia Zelle de ejemplo",
    requiere_foto_billete=False,
    activo=True,
    orden=2
)
DatoMetodoPago.objects.create(metodo_pago=m2, etiqueta="Correo", valor="ejemplo@zelle.com", orden=1)
DatoMetodoPago.objects.create(metodo_pago=m2, etiqueta="Titular", valor="Empresa Ejemplo LLC", orden=2)

m3 = MetodoPago.objects.create(
    nombre="Binance Pay Ejemplo",
    tipo="binance",
    moneda="USD",
    descripcion="Pago por Binance de ejemplo",
    requiere_foto_billete=False,
    activo=True,
    orden=3
)
DatoMetodoPago.objects.create(metodo_pago=m3, etiqueta="Pay ID", valor="123456789 (Ejemplo)", orden=1)
DatoMetodoPago.objects.create(metodo_pago=m3, etiqueta="Correo", valor="binance@ejemplo.com", orden=2)

m4 = MetodoPago.objects.create(
    nombre="Transferencia Bs Ejemplo",
    tipo="transferencia",
    moneda="BS",
    descripcion="Transferencia bancaria de ejemplo",
    requiere_foto_billete=False,
    activo=True,
    orden=4
)
DatoMetodoPago.objects.create(metodo_pago=m4, etiqueta="Banco", valor="Banco Ejemplo", orden=1)
DatoMetodoPago.objects.create(metodo_pago=m4, etiqueta="Cuenta", valor="0102 0000 0000 0000 0000 (Ejemplo)", orden=2)
DatoMetodoPago.objects.create(metodo_pago=m4, etiqueta="Titular", valor="Inversiones Ejemplo", orden=3)
DatoMetodoPago.objects.create(metodo_pago=m4, etiqueta="RIF/Cedula", valor="J-00000000-0 (Ejemplo)", orden=4)

m5 = MetodoPago.objects.create(
    nombre="Divisas en Efectivo Ejemplo",
    tipo="divisas",
    moneda="USD",
    descripcion="Entregar billetes de ejemplo en oficina",
    requiere_foto_billete=True,
    activo=True,
    orden=5
)
DatoMetodoPago.objects.create(metodo_pago=m5, etiqueta="Instrucciones", valor="Dirijase a la oficina de ejemplo para entregar.", orden=1)

print("Metodos de pago de ejemplo creados exitosamente.")
