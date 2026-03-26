"""
X12 820 Payment Order/Remittance Advice Parser

Parses X12 820 (005010X218) transactions for Medicaid/Medicare capitation and
premium payments. Designed for California DHCS PACE capitation remittances but
handles the general 820 format used by state Medicaid agencies.

Key segments parsed:
  ISA/GS  - Interchange and group headers (source ID, report date)
  BPR     - Payment amount and effective date
  TRN     - EFT/check trace number
  N1/N3/N4 - Payer and payee name and address
  ENT     - Per-member entity loop start
  NM1     - Member name and ID
  RMR     - Remittance line item (reference number, payment amount)
  REF*18  - Rate code (e.g., "957" = PACE rate)
  REF*ZZ  - Aid code/plan type composite and description
  DTM*582 - Coverage period date range
  ADX     - Adjustment amount and reason code

Typical loop structure within an 820:
  Header: ISA > GS > ST > BPR > TRN > N1(PE) > N1(PR)
  Per-member: ENT > NM1 > [RMR > REF*18 > REF*ZZ > REF*ZZ > DTM*582 > ADX?]+
  Trailer: SE > GE > IEA
"""

from typing import Optional
from .datamodels import PaymentData, PaymentDetail, RemittanceEntry


def _get(elements: list, index: int, default: str = "") -> str:
    """Safely retrieve a segment element by index."""
    try:
        return elements[index] if index < len(elements) else default
    except IndexError:
        return default


def _parse_date(date_str: str) -> Optional[str]:
    """Convert YYYYMMDD to ISO YYYY-MM-DD. Returns None for invalid input."""
    s = date_str.strip() if date_str else ""
    if len(s) != 8 or not s.isdigit():
        return None
    return f"{s[:4]}-{s[4:6]}-{s[6:8]}"


def _parse_amount(amount_str: str) -> Optional[float]:
    """Convert a string to float. Returns None for empty or invalid input."""
    s = amount_str.strip() if amount_str else ""
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _parse_rd8_range(period_str: str) -> tuple[Optional[str], Optional[str]]:
    """
    Parse a DTM RD8 date range string (YYYYMMDD-YYYYMMDD) into (start, end).

    Returns (None, None) if the format is unrecognised.
    """
    s = period_str.strip() if period_str else ""
    if "-" not in s:
        return None, None
    parts = s.split("-", 1)
    return _parse_date(parts[0]), _parse_date(parts[1]) if len(parts) > 1 else None


def _parse_820_transaction(segments: list[list[str]]) -> PaymentData:
    """
    Parse a list of already-split X12 segments into a PaymentData object.

    Args:
        segments: List of segment element lists, e.g. [["ISA","00",...], ["BPR","I",...]]

    Returns:
        Populated PaymentData object.
    """
    payment = PaymentData()
    members: list[PaymentDetail] = []

    # State tracking
    current_member: Optional[PaymentDetail] = None
    current_entry: Optional[RemittanceEntry] = None
    in_n1_pe = False  # Payee loop active
    in_n1_pr = False  # Payer loop active

    def _close_entry():
        """Append current_entry to current_member if both exist."""
        nonlocal current_entry
        if current_member is not None and current_entry is not None:
            current_member.remittance_entries.append(current_entry)
        current_entry = None

    def _close_member():
        """Finalise current member and append to members list."""
        nonlocal current_member
        _close_entry()
        if current_member is not None:
            members.append(current_member)
        current_member = None

    for elements in segments:
        if not elements:
            continue
        seg = elements[0].strip()

        # ── Interchange / group headers ──────────────────────────────────
        if seg == "ISA":
            payment.source = _get(elements, 6).strip()

        elif seg == "GS":
            date_str = _get(elements, 4)
            if len(date_str) == 8:
                payment.report_date = _parse_date(date_str)

        # ── Payment header ───────────────────────────────────────────────
        elif seg == "BPR":
            # BPR02 = total amount, BPR16 = EFT effective date
            payment.total_amount = _parse_amount(_get(elements, 2))
            payment.payment_date = _parse_date(_get(elements, 16))

        elif seg == "TRN":
            # TRN02 = EFT/check number
            payment.check_number = _get(elements, 2)

        # ── Payer / payee N1 loops ───────────────────────────────────────
        elif seg == "N1":
            entity_code = _get(elements, 1)
            name = _get(elements, 2)
            if entity_code == "PE":
                in_n1_pe, in_n1_pr = True, False
                payment.payee_name = name
            elif entity_code == "PR":
                in_n1_pr, in_n1_pe = True, False
                payment.payer_name = name
            else:
                in_n1_pe = in_n1_pr = False

        elif seg == "N3":
            addr = _get(elements, 1)
            if in_n1_pe:
                payment.payee_address_1 = addr
            elif in_n1_pr:
                payment.payer_address_1 = addr

        elif seg == "N4":
            city, state, zipcode = _get(elements, 1), _get(elements, 2), _get(elements, 3)
            if in_n1_pe:
                payment.payee_city = city
                payment.payee_state = state
                payment.payee_zip = zipcode
            elif in_n1_pr:
                payment.payer_city = city
                payment.payer_state = state
                payment.payer_zip = zipcode

        # ── ENT loop (per-member) ────────────────────────────────────────
        elif seg == "ENT":
            _close_member()
            in_n1_pe = in_n1_pr = False
            current_member = PaymentDetail(entity_number=_get(elements, 1))

        elif seg == "NM1" and current_member is not None:
            # NM1*IL = Insured/member
            current_member.last_name = _get(elements, 3) or None
            current_member.first_name = _get(elements, 4) or None
            current_member.middle_name = _get(elements, 5) or None
            member_id = _get(elements, 9)
            if member_id:
                current_member.member_id = member_id

        # ── RMR: start a new remittance line item ────────────────────────
        elif seg == "RMR" and current_member is not None:
            _close_entry()
            entry = RemittanceEntry()
            entry.reference_number = _get(elements, 2) or None

            # RMR elements[3] may be blank; amount is at [4], original at [5]
            amt = _parse_amount(_get(elements, 4))
            orig = _parse_amount(_get(elements, 5))
            entry.payment_amount = amt
            entry.original_amount = orig
            current_entry = entry

        # ── REF segments within an ENT loop ─────────────────────────────
        elif seg == "REF" and current_entry is not None:
            qualifier = _get(elements, 1)
            value = _get(elements, 2)

            if qualifier == "18":
                # Rate code (e.g., "957" = PACE)
                current_entry.rate_code = value or None

            elif qualifier == "ZZ":
                # Two REF*ZZ segments per RMR:
                #   First:  "{aid_code};{plan_type}"  (e.g. "1H;2", "M1;1")
                #   Second: description text          (e.g. "Primary Capitation Dual")
                if ";" in value:
                    parts = value.split(";", 1)
                    current_entry.aid_code = parts[0] or None
                    current_entry.plan_type = parts[1] or None
                else:
                    current_entry.description = value or None

        # ── DTM*582: coverage period date range ─────────────────────────
        elif seg == "DTM" and current_entry is not None:
            qualifier = _get(elements, 1)
            if qualifier == "582":
                # Format: DTM*582****RD8*YYYYMMDD-YYYYMMDD
                # elements[5] = "RD8", elements[6] = date range string
                fmt = _get(elements, 5)
                period = _get(elements, 6)
                if fmt == "RD8" and period:
                    start, end = _parse_rd8_range(period)
                    current_entry.coverage_period_start = start
                    current_entry.coverage_period_end = end

        # ── ADX: adjustment amount and reason code ───────────────────────
        elif seg == "ADX" and current_entry is not None:
            current_entry.adjustment_amount = _parse_amount(_get(elements, 1))
            reason = _get(elements, 2)
            current_entry.adjustment_reason = reason or None

        # ── Trailers – finalise if still open ────────────────────────────
        elif seg in ("SE", "GE", "IEA"):
            _close_member()

    # Catch any unclosed member (no trailer present)
    _close_member()

    payment.members = members
    return payment


def extract_payment_820(content: str) -> list[PaymentData]:
    """
    Parse one or more X12 820 transactions from raw EDI content.

    Handles both full interchange envelopes (starting with ISA) and bare
    transactions (starting with ST*820). Multiple ST*820...SE blocks within
    a single interchange are each returned as a separate PaymentData object.

    Args:
        content: Raw X12 820 EDI text. Segment terminator must be ``~``;
                 element separator must be ``*``.

    Returns:
        List of PaymentData objects, one per ST*820 transaction found.
        Returns an empty list if no 820 transactions are detected.

    Example::

        from hccinfhir import get_820_sample
        from hccinfhir.extractor_820 import extract_payment_820

        raw = get_820_sample(1)
        payments = extract_payment_820(raw)
        payment = payments[0]

        print(payment.payee_name)          # "myPlace South LA PACE Inc."
        print(payment.total_amount)        # 102139.46
        for member in payment.members:
            print(member.member_id, member.remittance_entries[0].payment_amount)
    """
    if not content or not content.strip():
        return []

    content = content.strip()
    if "ISA*" not in content and "ST*820" not in content:
        return []

    # Split into segments (strip whitespace around each)
    raw_segments = [s.strip() for s in content.split("~") if s.strip()]
    all_segments = [seg.split("*") for seg in raw_segments]

    # Collect ISA/GS context and find ST*820...SE blocks
    isa_seg: Optional[list[str]] = None
    gs_seg: Optional[list[str]] = None
    in_tx = False
    current_tx: list[list[str]] = []
    transactions: list[list[list[str]]] = []

    for elements in all_segments:
        if not elements:
            continue
        seg = elements[0].strip()

        if seg == "ISA":
            isa_seg = elements
        elif seg == "GS":
            gs_seg = elements
        elif seg == "ST" and len(elements) > 1 and elements[1] == "820":
            in_tx = True
            current_tx = []
            if isa_seg:
                current_tx.append(isa_seg)
            if gs_seg:
                current_tx.append(gs_seg)
            current_tx.append(elements)
        elif seg == "SE" and in_tx:
            current_tx.append(elements)
            transactions.append(current_tx)
            current_tx = []
            in_tx = False
        elif in_tx:
            current_tx.append(elements)

    return [_parse_820_transaction(tx) for tx in transactions]
