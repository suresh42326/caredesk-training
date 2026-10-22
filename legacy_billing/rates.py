from legacy_billing import config


def rate_for(code: str) -> int:
    if code not in config.RATES:
        raise KeyError(f"unknown service code: {code}")
    return config.RATES[code]


def is_exempt(code: str) -> bool:
    return code in config.TAX_EXEMPT
