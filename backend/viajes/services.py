import requests
from django.utils import timezone


def actualizar_tasa_bcv():
    """Obtiene la tasa de cambio BCV desde la API y actualiza la configuración."""
    from .models import ConfiguracionGeneral

    try:
        response = requests.get(
            'https://ve.dolarapi.com/v1/dolares/oficial',
            timeout=3
        )
        response.raise_for_status()
        data = response.json()
        tasa = data.get('promedio', 0)

        if tasa and tasa > 0:
            config = ConfiguracionGeneral.load()
            config.tasa_bcv = tasa
            config.tasa_actualizada = timezone.now()
            config.save()
            return True, f"Tasa actualizada: {tasa} Bs/$"
        else:
            return False, "La API no devolvió una tasa válida."
    except requests.exceptions.RequestException as e:
        return False, f"Error al conectar con la API: {str(e)}"
    except (ValueError, KeyError) as e:
        return False, f"Error al procesar la respuesta: {str(e)}"
