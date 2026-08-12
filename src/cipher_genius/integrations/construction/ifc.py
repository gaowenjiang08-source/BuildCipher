"""Dependency-free inspection of IFC STEP physical files.

This inspector reads file structure and entity records. It is not a geometric,
coordination, rule-checking, or full IFC schema engine.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter

from cipher_genius.models.construction import IFCInspectionResult


_SCHEMA_PATTERN = re.compile(
    r"FILE_SCHEMA\s*\(\s*\(\s*'([^']+)'",
    re.IGNORECASE,
)
_FILE_NAME_PATTERN = re.compile(r"FILE_NAME\s*\(\s*'((?:''|[^'])*)'", re.IGNORECASE)
_ENTITY_PATTERN = re.compile(
    r"^\s*#(\d+)\s*=\s*([A-Z][A-Z0-9_]*)\s*\((.*)\)\s*;\s*$",
    re.IGNORECASE | re.DOTALL,
)
_FIRST_STRING_PATTERN = re.compile(r"^\s*'((?:''|[^'])*)'")
_IFC_GLOBAL_ID_PATTERN = re.compile(r"^[0-9A-Za-z_$]{22}$")


def _decode_step(data: bytes) -> str:
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("latin-1")


def _split_step_statements(data_section: str) -> list[str]:
    statements: list[str] = []
    current: list[str] = []
    in_string = False
    index = 0
    while index < len(data_section):
        character = data_section[index]
        current.append(character)
        if character == "'":
            if in_string and index + 1 < len(data_section) and data_section[index + 1] == "'":
                current.append(data_section[index + 1])
                index += 1
            else:
                in_string = not in_string
        elif character == ";" and not in_string:
            statement = "".join(current).strip()
            if statement:
                statements.append(statement)
            current = []
        index += 1
    return statements


def inspect_ifc_bytes(data: bytes, *, source_ref: str = "memory") -> IFCInspectionResult:
    """Inspect an IFC STEP file and return stable, evidence-friendly metadata."""

    text = _decode_step(data)
    upper_text = text.upper()
    errors: list[str] = []
    if not upper_text.lstrip().startswith("ISO-10303-21;"):
        errors.append("missing_iso_10303_21_header")

    data_start = upper_text.find("DATA;")
    data_end = upper_text.find("ENDSEC;", data_start + 5) if data_start >= 0 else -1
    if data_start < 0 or data_end < 0:
        errors.append("missing_data_section")
        data_section = ""
    else:
        data_section = text[data_start + 5 : data_end]

    entity_ids: set[int] = set()
    entity_types: Counter[str] = Counter()
    global_ids: list[str] = []
    for statement in _split_step_statements(data_section):
        match = _ENTITY_PATTERN.match(statement)
        if match is None:
            if statement.startswith("#"):
                errors.append("malformed_entity_statement")
            continue
        entity_id = int(match.group(1))
        if entity_id in entity_ids:
            errors.append(f"duplicate_entity_id:{entity_id}")
        entity_ids.add(entity_id)
        entity_type = match.group(2).upper()
        entity_types[entity_type] += 1
        first_string = _FIRST_STRING_PATTERN.match(match.group(3))
        if first_string:
            candidate = first_string.group(1).replace("''", "'")
            if _IFC_GLOBAL_ID_PATTERN.fullmatch(candidate):
                global_ids.append(candidate)

    global_id_counts = Counter(global_ids)
    duplicate_global_ids = sorted(
        global_id for global_id, count in global_id_counts.items() if count > 1
    )
    errors.extend(f"duplicate_global_id:{global_id}" for global_id in duplicate_global_ids)
    file_name_match = _FILE_NAME_PATTERN.search(text)
    schema_identifiers = sorted({item.upper() for item in _SCHEMA_PATTERN.findall(text)})
    if not schema_identifiers:
        errors.append("missing_file_schema")
    if not entity_ids:
        errors.append("no_ifc_entities")

    return IFCInspectionResult(
        source_ref=source_ref,
        file_name=(
            file_name_match.group(1).replace("''", "'") if file_name_match else None
        ),
        content_sha256=hashlib.sha256(data).hexdigest(),
        byte_count=len(data),
        schema_identifiers=schema_identifiers,
        entity_count=len(entity_ids),
        entity_type_counts=dict(sorted(entity_types.items())),
        global_id_count=len(global_ids),
        duplicate_global_ids=duplicate_global_ids,
        parse_errors=errors,
        valid=not errors,
    )
