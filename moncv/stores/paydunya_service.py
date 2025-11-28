import os
import paydunya
from django.conf import settings


def configure_paydunya():
    """Configure la librairie PayDunya en Python.

    La SDK attend un dictionnaire PAYDUNYA_ACCESS_TOKENS et un booléen paydunya.debug,
    pas un appel de fonction api_keys (qui provoquait "'dict' object is not callable").
    """

    master_key = os.getenv("PAYDUNYA_MASTER_KEY", getattr(settings, "PAYDUNYA_MASTER_KEY", ""))
    private_key = os.getenv("PAYDUNYA_PRIVATE_KEY", getattr(settings, "PAYDUNYA_PRIVATE_KEY", ""))
    token = os.getenv("PAYDUNYA_TOKEN", getattr(settings, "PAYDUNYA_TOKEN", ""))

    paydunya.PAYDUNYA_ACCESS_TOKENS = {
        'PAYDUNYA-MASTER-KEY': master_key,
        'PAYDUNYA-PRIVATE-KEY': private_key,
        'PAYDUNYA-TOKEN': token,
    }

    mode = os.getenv("PAYDUNYA_MODE", getattr(settings, "PAYDUNYA_MODE", "test"))
    paydunya.debug = False if mode == "live" else True
