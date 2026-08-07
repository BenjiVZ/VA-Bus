"""Lógica de negocio de pagos, compartida por la API y el back office.

Vive aquí para que aprobar un comprobante haga exactamente lo mismo sin
importar desde dónde se apruebe: la misma actualización de reservas, el mismo
correo y el mismo aviso por WebSocket.
"""
from django.conf import settings as django_settings
from django.core.mail import send_mail
from django.utils import timezone

from reservas.models import Reserva


def validar_comprobante(comprobante, nuevo_estado, revisor, nota=''):
    """Aprueba o rechaza un comprobante y arrastra sus reservas.

    Devuelve el queryset de reservas afectadas.
    """
    if nuevo_estado not in ('aprobado', 'rechazado'):
        raise ValueError("El estado debe ser 'aprobado' o 'rechazado'.")

    comprobante.estado = nuevo_estado
    comprobante.revisado_por = revisor
    comprobante.fecha_revision = timezone.now()
    comprobante.nota_admin = nota or ''
    comprobante.save()

    reservas = Reserva.objects.filter(grupo_pago=comprobante.grupo_pago)
    if nuevo_estado == 'aprobado':
        # Se guardan una por una: el save() es el que genera el código de ticket.
        for r in reservas:
            r.estado = 'confirmado'
            r.save()
    else:
        reservas.update(estado='cancelado')
        # Al rechazar, los puestos vuelven a quedar libres para los demás.
        from viajes.ws_broadcast import broadcast_seat_change
        for r in reservas:
            broadcast_seat_change(
                viaje_id=r.viaje_id,
                numero=r.numero_asiento,
                piso=r.piso_asiento,
                estado='released',
            )

    enviar_email_validacion(comprobante, reservas, nuevo_estado)
    return reservas


def enviar_email_validacion(comprobante, reservas, estado):
    """Avisa al cliente el resultado de su comprobante. Nunca rompe el flujo."""
    usuario = comprobante.usuario
    email = getattr(usuario, 'email', '')
    if not email:
        return

    reservas_list = reservas.select_related('viaje__ruta', 'viaje__autobus')
    primera = reservas_list.first()

    if estado == 'aprobado':
        subject = '✅ Pago Aprobado — Aerorutas de Venezuela'
        asientos_info = ''
        for r in reservas_list:
            ticket = r.codigo_ticket or 'Pendiente'
            pasajero = r.nombre_pasajero or usuario.get_full_name() or usuario.username
            asientos_info += f'''
                <tr>
                    <td style="padding:8px 12px;border-bottom:1px solid #eee;">Asiento #{r.numero_asiento} (Piso {r.piso_asiento})</td>
                    <td style="padding:8px 12px;border-bottom:1px solid #eee;">{pasajero}</td>
                    <td style="padding:8px 12px;border-bottom:1px solid #eee;font-weight:700;color:#0052cc;">{ticket}</td>
                </tr>'''

        viaje_info = ''
        if primera and primera.viaje:
            v = primera.viaje
            viaje_info = f'{v.ruta.origen} → {v.ruta.destino} · {v.fecha_salida} · {v.hora_salida}'

        html = f'''
            <div style="font-family:Inter,Arial,sans-serif;max-width:600px;margin:0 auto;background:#fff;">
                <div style="background:linear-gradient(135deg,#0a1628,#1a365d);padding:24px;text-align:center;border-radius:12px 12px 0 0;">
                    <h1 style="color:#fff;margin:0;font-size:20px;">🚌 Aerorutas de Venezuela</h1>
                </div>
                <div style="padding:24px;border:1px solid #e2e8f0;border-top:none;border-radius:0 0 12px 12px;">
                    <h2 style="color:#22543d;margin-top:0;">✅ ¡Tu pago ha sido aprobado!</h2>
                    <p style="color:#4a5568;">Hola <strong>{usuario.first_name or usuario.username}</strong>, tu comprobante de pago fue verificado exitosamente.</p>

                    <div style="background:#f7fafc;border:1px solid #e2e8f0;border-radius:8px;padding:16px;margin:16px 0;">
                        <p style="margin:0 0 4px;font-size:13px;color:#718096;">VIAJE</p>
                        <p style="margin:0;font-weight:700;color:#1a365d;">{viaje_info}</p>
                    </div>

                    <table style="width:100%;border-collapse:collapse;margin:16px 0;">
                        <thead>
                            <tr style="background:#f7fafc;">
                                <th style="padding:8px 12px;text-align:left;font-size:13px;color:#718096;">Asiento</th>
                                <th style="padding:8px 12px;text-align:left;font-size:13px;color:#718096;">Pasajero</th>
                                <th style="padding:8px 12px;text-align:left;font-size:13px;color:#718096;">Código Ticket</th>
                            </tr>
                        </thead>
                        <tbody>{asientos_info}</tbody>
                    </table>

                    <p style="color:#4a5568;font-size:14px;">Presenta tu código de ticket al momento de abordar. ¡Buen viaje! 🎉</p>
                </div>
            </div>'''
    else:
        from html import escape
        subject = '❌ Comprobante Rechazado — Aerorutas de Venezuela'
        nota = escape(comprobante.nota_admin or 'No se proporcionó motivo.')
        html = f'''
            <div style="font-family:Inter,Arial,sans-serif;max-width:600px;margin:0 auto;background:#fff;">
                <div style="background:linear-gradient(135deg,#0a1628,#1a365d);padding:24px;text-align:center;border-radius:12px 12px 0 0;">
                    <h1 style="color:#fff;margin:0;font-size:20px;">🚌 Aerorutas de Venezuela</h1>
                </div>
                <div style="padding:24px;border:1px solid #e2e8f0;border-top:none;border-radius:0 0 12px 12px;">
                    <h2 style="color:#742a2a;margin-top:0;">❌ Comprobante Rechazado</h2>
                    <p style="color:#4a5568;">Hola <strong>{usuario.first_name or usuario.username}</strong>, lamentamos informarte que tu comprobante de pago no fue aprobado.</p>

                    <div style="background:#fff5f5;border:1px solid #fed7d7;border-radius:8px;padding:16px;margin:16px 0;">
                        <p style="margin:0 0 4px;font-size:13px;color:#718096;">MOTIVO</p>
                        <p style="margin:0;color:#742a2a;">{nota}</p>
                    </div>

                    <p style="color:#4a5568;font-size:14px;">Puedes intentar nuevamente realizando una nueva reserva y subiendo un comprobante válido.</p>
                </div>
            </div>'''

    try:
        send_mail(
            subject=subject,
            message='',  # respaldo en texto plano
            from_email=django_settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html,
            fail_silently=False,
        )
    except Exception as e:  # el correo nunca debe tumbar la validación
        print(f'[EMAIL ERROR] No se pudo enviar email a {email}: {e}')
