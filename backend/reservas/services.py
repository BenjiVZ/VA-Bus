"""
Servicio de generación de PDF y envío de email para tickets de reserva.
"""
import io
import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from django.core.mail import EmailMessage
from django.conf import settings


# ── COLOR PALETTE ──
PRIMARY = HexColor('#2563eb')
PRIMARY_DARK = HexColor('#1e40af')
DARK_BG = HexColor('#1e293b')
LIGHT_TEXT = HexColor('#f8fafc')
MUTED = HexColor('#94a3b8')
WHITE = colors.white
BLACK = colors.black


def generar_qr_image(data, size=120):
    """Genera un QR code como ImageReader para ReportLab."""
    qr = qrcode.QRCode(version=1, box_size=10, border=1)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return ImageReader(buffer)


def generar_ticket_pdf(reservas, viaje, config, base_url=''):
    """
    Genera un PDF con los tickets de las reservas.
    Retorna un BytesIO con el PDF.
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    empresa = config.nombre_empresa if config else 'VA-Bus'
    rif = config.rif if config else ''

    for i, reserva in enumerate(reservas):
        if i > 0:
            c.showPage()

        # ── Page Background ──
        c.setFillColor(WHITE)
        c.rect(0, 0, width, height, fill=1, stroke=0)

        # ── Ticket Card (centered) ──
        card_w = 160 * mm
        card_h = 220 * mm
        card_x = (width - card_w) / 2
        card_y = (height - card_h) / 2

        # Card shadow
        c.setFillColor(HexColor('#e2e8f0'))
        c.roundRect(card_x + 2, card_y - 2, card_w, card_h, 10, fill=1, stroke=0)

        # Card background
        c.setFillColor(WHITE)
        c.roundRect(card_x, card_y, card_w, card_h, 10, fill=1, stroke=0)

        # Card border
        c.setStrokeColor(HexColor('#e2e8f0'))
        c.setLineWidth(0.5)
        c.roundRect(card_x, card_y, card_w, card_h, 10, fill=0, stroke=1)

        # ── Top accent bar ──
        c.setFillColor(PRIMARY)
        c.roundRect(card_x, card_y + card_h - 8 * mm, card_w, 8 * mm, 10, fill=1, stroke=0)
        c.rect(card_x, card_y + card_h - 12 * mm, card_w, 8 * mm, fill=1, stroke=0)

        # ── Header: Company ──
        y = card_y + card_h - 22 * mm
        c.setFillColor(DARK_BG)
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(width / 2, y, empresa)

        if rif:
            y -= 5 * mm
            c.setFont("Helvetica", 8)
            c.setFillColor(MUTED)
            c.drawCentredString(width / 2, y, f"RIF: {rif}")

        # ── Boleto Number ──
        y -= 8 * mm
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(PRIMARY)
        c.drawCentredString(width / 2, y, f"BOLETO #{reserva.id}")

        # ── Route ──
        y -= 12 * mm
        c.setFont("Helvetica-Bold", 14)
        c.setFillColor(DARK_BG)
        origen = viaje.ruta.origen
        destino = viaje.ruta.destino
        arrow = " ⇄ " if viaje.tipo_viaje == 'ida_vuelta' else " → "
        c.drawCentredString(width / 2, y, f"{origen}{arrow}{destino}")

        if viaje.tipo_viaje == 'ida_vuelta':
            y -= 5 * mm
            c.setFont("Helvetica-Bold", 7)
            c.setFillColor(PRIMARY)
            c.drawCentredString(width / 2, y, "IDA Y VUELTA")

        # ── Divider ──
        y -= 6 * mm
        c.setStrokeColor(HexColor('#e2e8f0'))
        c.setDash(3, 3)
        c.line(card_x + 10 * mm, y, card_x + card_w - 10 * mm, y)
        c.setDash()

        # ── Details Grid ──
        y -= 10 * mm
        left_col = card_x + 15 * mm
        right_col = card_x + card_w / 2 + 5 * mm

        def draw_field(x, y_pos, label, value):
            c.setFont("Helvetica", 7)
            c.setFillColor(MUTED)
            c.drawString(x, y_pos + 4 * mm, label.upper())
            c.setFont("Helvetica-Bold", 10)
            c.setFillColor(DARK_BG)
            c.drawString(x, y_pos, value)

        # Row 1
        from datetime import datetime
        fecha_str = ''
        try:
            fecha_obj = datetime.strptime(str(viaje.fecha_salida), '%Y-%m-%d')
            fecha_str = fecha_obj.strftime('%d/%m/%Y')
        except Exception:
            fecha_str = str(viaje.fecha_salida)

        hora_str = str(viaje.hora_salida)[:5] if viaje.hora_salida else ''

        draw_field(left_col, y, "Fecha de Salida", fecha_str)
        draw_field(right_col, y, "Hora", hora_str)

        # Row 2
        y -= 16 * mm
        draw_field(left_col, y, "Autobús", viaje.autobus.nombre)
        draw_field(right_col, y, "Asiento", f"#{reserva.numero_asiento} - Piso {reserva.piso_asiento}")

        # Row 3 - Return date if applicable
        if viaje.tipo_viaje == 'ida_vuelta' and viaje.fecha_vuelta:
            y -= 16 * mm
            fecha_vuelta_str = ''
            try:
                fv = datetime.strptime(str(viaje.fecha_vuelta), '%Y-%m-%d')
                fecha_vuelta_str = fv.strftime('%d/%m/%Y')
            except Exception:
                fecha_vuelta_str = str(viaje.fecha_vuelta)
            hora_vuelta_str = str(viaje.hora_vuelta)[:5] if viaje.hora_vuelta else ''
            draw_field(left_col, y, "Fecha de Vuelta", fecha_vuelta_str)
            draw_field(right_col, y, "Hora Vuelta", hora_vuelta_str)

        # Row: Price
        y -= 16 * mm
        draw_field(left_col, y, "Precio", f"${float(viaje.precio_usd):.2f}")

        # ── Divider ──
        y -= 8 * mm
        c.setStrokeColor(HexColor('#e2e8f0'))
        c.setDash(3, 3)
        c.line(card_x + 10 * mm, y, card_x + card_w - 10 * mm, y)
        c.setDash()

        # ── Passenger - Buyer ──
        y -= 10 * mm
        c.setFont("Helvetica", 7)
        c.setFillColor(MUTED)
        c.drawString(left_col, y + 4 * mm, "COMPRADOR")
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(DARK_BG)
        c.drawString(left_col, y, reserva.nombre_pasajero or 'Sin nombre')

        if reserva.cedula_pasajero:
            y -= 5 * mm
            c.setFont("Helvetica", 9)
            c.setFillColor(MUTED)
            c.drawString(left_col, y, f"C.I. {reserva.cedula_pasajero}")

        # ── Assigned person (if applicable) ──
        if reserva.para_otra_persona and reserva.nombre_asignado:
            y -= 10 * mm
            c.setFont("Helvetica", 7)
            c.setFillColor(PRIMARY)
            c.drawString(left_col, y + 4 * mm, "ASIGNADO A")
            c.setFont("Helvetica-Bold", 11)
            c.setFillColor(DARK_BG)
            c.drawString(left_col, y, reserva.nombre_asignado)
            if reserva.cedula_asignado:
                y -= 5 * mm
                c.setFont("Helvetica", 9)
                c.setFillColor(MUTED)
                c.drawString(left_col, y, f"C.I. {reserva.cedula_asignado}")

        # ── Minor badge ──
        if reserva.es_menor_edad:
            y -= 7 * mm
            c.setFont("Helvetica-Bold", 7)
            c.setFillColor(HexColor('#92400e'))
            c.drawString(left_col, y, "👶 MENOR DE EDAD")

        # ── Tear line (semicircles) ──
        y -= 10 * mm
        c.setStrokeColor(HexColor('#cbd5e1'))
        c.setDash(4, 4)
        c.line(card_x + 10 * mm, y, card_x + card_w - 10 * mm, y)
        c.setDash()

        # ── QR Code ──
        y -= 5 * mm
        qr_size = 30 * mm
        qr_url = f"{base_url}/verificar/{reserva.codigo_ticket}" if base_url else reserva.codigo_ticket
        qr_img = generar_qr_image(qr_url, size=150)
        qr_x = (width - qr_size) / 2
        c.drawImage(qr_img, qr_x, y - qr_size, qr_size, qr_size)

        # Ticket code below QR
        y_code = y - qr_size - 4 * mm
        c.setFont("Courier-Bold", 12)
        c.setFillColor(DARK_BG)
        c.drawCentredString(width / 2, y_code, reserva.codigo_ticket or '')

        y_hint = y_code - 4 * mm
        c.setFont("Helvetica", 7)
        c.setFillColor(MUTED)
        c.drawCentredString(width / 2, y_hint, "Escanea para verificar tu boleto")

    c.save()
    buffer.seek(0)
    return buffer


def enviar_email_ticket(reservas, viaje, config, usuario, base_url=''):
    """
    Envía email al usuario con el ticket PDF adjunto.
    """
    if not usuario.email:
        return False

    empresa = config.nombre_empresa if config else 'VA-Bus'

    # Generate PDF
    pdf_buffer = generar_ticket_pdf(reservas, viaje, config, base_url)

    asientos = ', '.join([f'#{r.numero_asiento}' for r in reservas])
    subject = f'🎫 Tu boleto - {viaje.ruta.origen} → {viaje.ruta.destino} | {empresa}'

    body = f"""¡Hola {usuario.get_full_name() or usuario.username}!

Tu reserva ha sido CONFIRMADA. Aquí tienes los detalles:

🚌 Ruta: {viaje.ruta.origen} → {viaje.ruta.destino}
📅 Fecha: {viaje.fecha_salida}
🕐 Hora: {str(viaje.hora_salida)[:5]}
💺 Asiento(s): {asientos}
🚍 Autobús: {viaje.autobus.nombre}
💰 Precio: ${float(viaje.precio_usd):.2f}

Adjuntamos tu boleto en PDF. Puedes imprimirlo o mostrarlo desde tu teléfono al abordar.

¡Buen viaje!
{empresa}
"""

    email = EmailMessage(
        subject=subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[usuario.email],
    )

    filename = f'boleto_{viaje.ruta.origen}_{viaje.ruta.destino}_{viaje.fecha_salida}.pdf'
    email.attach(filename, pdf_buffer.read(), 'application/pdf')

    try:
        email.send()
        return True
    except Exception as e:
        print(f"Error enviando email: {e}")
        return False
