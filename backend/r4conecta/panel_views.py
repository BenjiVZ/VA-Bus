"""Panel del admin para ver y autovalidar los pagos de Débito Inmediato (R4).

Lista las operaciones y, en cada carga, resuelve las que quedaron en espera
(AC00) consultándolas al banco. La página se refresca sola, así que las
operaciones "se validan solas".
"""
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render

from .models import OperacionDebitoOTP
from .operaciones import validar_pendientes


@staff_member_required
def panel_pagos(request):
    resumen = validar_pendientes()  # autovalida los AC00 en cada carga
    operaciones = OperacionDebitoOTP.objects.all()[:150]
    return render(request, 'r4conecta/panel_pagos.html', {
        'operaciones': operaciones,
        'resumen': resumen,
        'refresco': 20,  # segundos entre autovalidaciones (meta refresh)
    })
