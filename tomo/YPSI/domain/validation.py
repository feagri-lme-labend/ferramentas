def run_validations(validations, ui_error):
    for condition, message in validations:
        if condition:
            ui_error(message)
            return False
    return True

def find_missing_times(propagation_paths):
    """
    Find propagation paths with missing or invalid times.
    """

    return [
        p for p in propagation_paths
        if p["time"] is None or p["time"] <= 0
    ]