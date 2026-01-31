def build_contract_code(start_date: str, flat_number: str) -> str:
    """
    start_date: DD.MM.YYYY
    """
    return f"{start_date}/{flat_number}"
