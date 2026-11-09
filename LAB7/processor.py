import json
import math
import re

# "LxWxH" in centimetres: three positive decimal numbers separated by x/X.
_DIMS_RE = re.compile(
    r"\s*([0-9]+(?:\.[0-9]+)?)\s*[xX]\s*([0-9]+(?:\.[0-9]+)?)\s*[xX]\s*([0-9]+(?:\.[0-9]+)?)\s*",
    re.ASCII,
)

# One ASCII letter followed by 1 to 6 ASCII digits, e.g. "E123".
_TRACKING_RE = re.compile(r"([A-Za-z])([0-9]{1,6})", re.ASCII)


def calculate_dimensional_weight(dimensions_str):
    if not isinstance(dimensions_str, str):
        raise TypeError("dimensions must be a string such as '20x30x10'")

    match = _DIMS_RE.fullmatch(dimensions_str)
    if match is None:
        raise ValueError("dimensions must look like LxWxH with positive numbers, e.g. 20x30x10")

    length, width, height = (float(part) for part in match.groups())
    if length <= 0 or width <= 0 or height <= 0:
        raise ValueError("dimensions must be greater than zero")

    volume = length * width * height
    if not math.isfinite(volume):
        raise ValueError("dimensions are too large")

    return round(volume / 5000.0, 2)


def format_tracking_label(raw_code):
    if not isinstance(raw_code, str):
        raise TypeError("raw code must be a string such as 'E123'")

    match = _TRACKING_RE.fullmatch(raw_code.strip())
    if match is None:
        raise ValueError("raw code must be one letter followed by 1 to 6 digits, e.g. E123")

    prefix, digits = match.groups()
    return f"{prefix.upper()}-{int(digits):06d}"


def parse_package_manifest(json_payload):
    if not isinstance(json_payload, (str, bytes, bytearray)):
        raise TypeError("manifest must be a JSON string")

    try:
        data = json.loads(json_payload)
    except (ValueError, RecursionError) as exc:
        # JSONDecodeError and UnicodeDecodeError are ValueError subclasses.
        raise ValueError("manifest is not valid JSON") from exc

    if not isinstance(data, dict):
        raise ValueError("manifest must be a JSON object")
    if "weight" not in data:
        raise ValueError("manifest is missing the 'weight' field")

    weight = data["weight"]
    if isinstance(weight, bool) or not isinstance(weight, (int, float)):
        raise ValueError("'weight' must be a number")

    try:
        weight = float(weight)
    except OverflowError as exc:
        raise ValueError("'weight' is too large") from exc

    if not math.isfinite(weight) or weight < 0:
        raise ValueError("'weight' must be a finite, non-negative number")
    return weight


def _ask(prompt, parser):
    """Read one line, run it through a parser, and report errors without crashing."""
    try:
        return parser(input(prompt))
    except (TypeError, ValueError) as exc:
        print(f"Invalid input: {exc}")
        return None


def main():
    print("==== Running calculate_dimensional_weight ====")
    dim_weight = _ask("Enter dimensions LxWxH in cm (e.g. 20x30x10): ", calculate_dimensional_weight)
    if dim_weight is not None:
        print("Dimensional Weight (kg):", dim_weight)

    print("\n==== Running format_tracking_label ====")
    label = _ask("Enter raw code (e.g. E123): ", format_tracking_label)
    if label is not None:
        print("Formatted Label:", label)

    print("\n==== Running parse_package_manifest ====")
    weight = _ask('Enter manifest JSON (e.g. {"weight": 12.5}): ', parse_package_manifest)
    if weight is not None:
        print("Manifest Weight:", weight)


if __name__ == "__main__":
    main()
