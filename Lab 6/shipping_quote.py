def process_shipments(shipments, handling_fee):
    if not isinstance(shipments, list) or handling_fee < 0:
        raise ValueError("Invalid shipments list or handling fee")

    total_quote = 0.0
    rejected_parcels = 0

    for shipment in shipments:
        if not shipment.get("manifest_approved", False):
            continue

        transport_mode = shipment.get("mode", "ground")
        is_fragile = shipment.get("is_fragile", False)
        packages = shipment.get("packages", [])

        if transport_mode == "air":
            base_rate = 12.0
        elif transport_mode == "ground":
            base_rate = 4.0
        else:
            rejected_parcels += 1
            continue

        shipment_cost = handling_fee

        for pkg in packages:
            weight = pkg.get("weight_kg", 0)
            hazmat = pkg.get("is_hazmat", False)

            if weight <= 0:
                rejected_parcels += 1
                continue

            if hazmat:
                rejected_parcels += 1
                if is_fragile:
                    shipment_cost = 0.0
                    break
                shipment_cost += 50.0
            elif weight > 30:
                shipment_cost += weight * (base_rate * 1.5)
            else:
                shipment_cost += weight * base_rate

        if shipment.get("express_priority", False):
            shipment_cost *= 1.25

        total_quote += shipment_cost

    if rejected_parcels > 3:
        return {"total_quote": round(total_quote, 2), "status": "FLAGGED_REVIEW"}
    if total_quote == 0.0:
        return {"total_quote": 0.0, "status": "NO_CARGO"}
    return {"total_quote": round(total_quote, 2), "status": "CLEARED"}


def monitor_container_pressures(pressure_logs):
    if not pressure_logs:
        return "NO_DATA"

    for container in pressure_logs:
        depressurization_streak = 0
        for psi in container:
            if psi < 14.0:
                depressurization_streak += 1
                if depressurization_streak >= 2:
                    return "LEAK_DETECTED"
            else:
                depressurization_streak = 0
    return "STABLE"