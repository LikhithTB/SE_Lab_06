import json
import math
import re

from hypothesis import given, strategies as st
from processor import calculate_dimensional_weight, format_tracking_label, parse_package_manifest

# Bad input is allowed to be rejected, but only with a deliberate, documented
# exception. Anything else (IndexError, KeyError, OverflowError, AttributeError,
# RecursionError, ...) is an unhandled crash and counts as a bug.
ACCEPTED_REJECTIONS = (ValueError, TypeError)

TRACKING_LABEL_RE = re.compile(r"[A-Z]-[0-9]{6}")

# Strings that look like "LxWxH" with a mix of digits, signs, letters and dots.
DIMS_LIKE = st.from_regex(r"[-+0-9.a-zA-Z ]{0,10}x[-+0-9.a-zA-Z ]{0,10}x[-+0-9.a-zA-Z ]{0,10}", fullmatch=True)

# Realistic, finite, positive dimensions.
POSITIVE_CM = st.floats(min_value=0.01, max_value=1000, allow_nan=False, allow_infinity=False)


@given(st.text() | st.none())
def test_calculate_dimensional_weight_no_crash(s):
    try:
        result = calculate_dimensional_weight(s)
    except Exception as e:
        assert isinstance(e, ACCEPTED_REJECTIONS), \
            f"calculate_dimensional_weight crashed on {s!r} with {type(e).__name__}: {e}"
    else:
        assert math.isfinite(result) and result > 0, \
            f"calculate_dimensional_weight({s!r}) returned non-physical value {result}"


@given(DIMS_LIKE)
def test_calculate_dimensional_weight_dims_like_strings(s):
    try:
        result = calculate_dimensional_weight(s)
    except Exception as e:
        assert isinstance(e, ACCEPTED_REJECTIONS), \
            f"calculate_dimensional_weight crashed on {s!r} with {type(e).__name__}: {e}"
    else:
        assert math.isfinite(result) and result > 0, \
            f"calculate_dimensional_weight({s!r}) returned non-physical value {result}"


# Numeric tokens that float() accepts but that are not physical dimensions.
ODD_NUMBER_TOKENS = st.sampled_from(
    ["0", "-1", "-0.5", "nan", "NaN", "inf", "-inf", "1e400", "1e-400", "1_000", " 20 ", "9" * 400]
)


@given(ODD_NUMBER_TOKENS, ODD_NUMBER_TOKENS, ODD_NUMBER_TOKENS)
def test_calculate_dimensional_weight_odd_numbers(a, b, c):
    s = f"{a}x{b}x{c}"
    try:
        result = calculate_dimensional_weight(s)
    except Exception as e:
        assert isinstance(e, ACCEPTED_REJECTIONS), \
            f"calculate_dimensional_weight crashed on {s!r} with {type(e).__name__}: {e}"
    else:
        assert math.isfinite(result) and result > 0, \
            f"calculate_dimensional_weight({s!r}) returned non-physical value {result}"


@given(POSITIVE_CM, POSITIVE_CM, POSITIVE_CM)
def test_calculate_dimensional_weight_matches_formula(l, w, h):
    expected = round((l * w * h) / 5000.0, 2)
    assert calculate_dimensional_weight(f"{l!r}x{w!r}x{h!r}") == expected


@given(st.text() | st.none())
def test_format_tracking_label_safe(s):
    try:
        label = format_tracking_label(s)
    except Exception as e:
        assert isinstance(e, ACCEPTED_REJECTIONS), \
            f"format_tracking_label crashed on {s!r} with {type(e).__name__}: {e}"
    else:
        assert TRACKING_LABEL_RE.fullmatch(label), \
            f"format_tracking_label({s!r}) produced malformed label {label!r}"


@given(st.from_regex(r"[A-Za-z][0-9]{1,6}", fullmatch=True))
def test_format_tracking_label_valid_codes(code):
    assert format_tracking_label(code) == f"{code[0].upper()}-{int(code[1:]):06d}"


ODD_TRACKING_CODES = st.sampled_from(
    ["E-5", "E+5", "E 12", "E1_000", "E1234567", "e0", "ß1", "٣١", "E\n12", " E12"]
)


@given(ODD_TRACKING_CODES)
def test_format_tracking_label_odd_codes(s):
    try:
        label = format_tracking_label(s)
    except Exception as e:
        assert isinstance(e, ACCEPTED_REJECTIONS), \
            f"format_tracking_label crashed on {s!r} with {type(e).__name__}: {e}"
    else:
        assert TRACKING_LABEL_RE.fullmatch(label), \
            f"format_tracking_label({s!r}) produced malformed label {label!r}"


@given(st.text() | st.none() | st.binary())
def test_parse_package_manifest_safe(s):
    try:
        weight = parse_package_manifest(s)
    except Exception as e:
        assert isinstance(e, ACCEPTED_REJECTIONS), \
            f"parse_package_manifest crashed on {s!r} with {type(e).__name__}: {e}"
    else:
        assert math.isfinite(weight) and weight >= 0, \
            f"parse_package_manifest({s!r}) returned non-physical weight {weight}"


# Structured JSON payloads: wrong types, missing keys, booleans, nulls, nested objects.
JSON_VALUES = st.recursive(
    st.none() | st.booleans() | st.integers() | st.floats() | st.text(),
    lambda children: st.lists(children) | st.dictionaries(st.text(), children),
    max_leaves=10,
)
MANIFEST_PAYLOADS = st.builds(json.dumps, st.dictionaries(st.sampled_from(["weight", "id", "dims"]), JSON_VALUES))


@given(MANIFEST_PAYLOADS)
def test_parse_package_manifest_structured_payloads(payload):
    try:
        weight = parse_package_manifest(payload)
    except Exception as e:
        assert isinstance(e, ACCEPTED_REJECTIONS), \
            f"parse_package_manifest crashed on {payload!r} with {type(e).__name__}: {e}"
    else:
        assert math.isfinite(weight) and weight >= 0, \
            f"parse_package_manifest({payload!r}) returned non-physical weight {weight}"


ODD_MANIFESTS = st.sampled_from([
    '{"weight": -1}', '{"weight": NaN}', '{"weight": Infinity}', '{"weight": 1e400}',
    '{"weight": true}', '{"weight": "12.5"}', '{"weight": null}', '{"weight": ' + "9" * 400 + '}',
    '[1, 2]', '"weight"', '{"weight": 1,}', '[' * 100000, '\xff', '',
])


@given(ODD_MANIFESTS)
def test_parse_package_manifest_odd_payloads(payload):
    try:
        weight = parse_package_manifest(payload)
    except Exception as e:
        assert isinstance(e, ACCEPTED_REJECTIONS), \
            f"parse_package_manifest crashed on {payload[:40]!r} with {type(e).__name__}: {e}"
    else:
        assert math.isfinite(weight) and weight >= 0, \
            f"parse_package_manifest({payload[:40]!r}) returned non-physical weight {weight}"


@given(st.floats(min_value=0, max_value=1e6, allow_nan=False, allow_infinity=False))
def test_parse_package_manifest_valid_weights_roundtrip(w):
    assert parse_package_manifest(json.dumps({"weight": w})) == w
