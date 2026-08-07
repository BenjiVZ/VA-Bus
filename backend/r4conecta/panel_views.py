"""Pantalla del back office para ver y autovalidar los pagos de Débito Inmediato (R4).

Lista las operaciones y, en cada carga, resuelve las que quedaron en espera
(AC00) consultándolas al banco. La página se refresca sola, así que las
operaciones "se validan solas".
"""
from backoffice.auth import staff_requerido
from django.shortcuts import render

from .models import OperacionDebitoOTP
from .operaciones import validar_pendientes


@staff_requerido
def panel_pagos(request):
    resumen = validar_pendientes()  # autovalida los AC00 en cada carga
    operaciones = OperacionDebitoOTP.objects.all()[:150]
    return render(request, 'backoffice/pagos_r4.html', {
        'seccion': 'pagos_r4',
        'titulo': 'Pagos R4 — débito inmediato',
        'subtitulo': 'Las operaciones en espera se consultan solas al banco',
        'operaciones': operaciones,
        'resumen': resumen,
        'refresco': 20,  # segundos entre autovalidaciones (meta refresh)
    })
