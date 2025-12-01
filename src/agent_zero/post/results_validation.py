"""Validation module for results bundles.

Validates timeseries, agent_states, summary.json, and manifest.yaml
against the results.schema.json specification.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import pandas as pd
import yaml


@dataclass
class ValidationIssue:
    """A validation issue (error or warning)."""

    level: Literal["error", "warning"]
    location: str
    message: str


def _load_schema() -> dict[str, Any]:
    """Load the results schema from results.schema.json."""
    schema_path = Path(__file__).parent / "results.schema.json"
    with open(schema_path, encoding="utf-8") as f:
        return json.load(f)


def _check_dtype(value: Any, expected_type: str) -> bool:
    """Check if a value matches the expected type string."""
    if expected_type == "int":
        return isinstance(value, (int, float)) and (isinstance(value, int) or value == int(value))
    elif expected_type == "float":
        return isinstance(value, (int, float))
    elif expected_type == "str":
        return isinstance(value, str)
    elif expected_type == "str_or_null":
        return value is None or isinstance(value, str)
    elif expected_type == "float_or_null":
        return value is None or isinstance(value, (int, float))
    elif expected_type == "int_or_null":
        return value is None or isinstance(value, int)
    elif expected_type == "object":
        return isinstance(value, dict)
    elif expected_type == "object_or_null":
        return value is None or isinstance(value, dict)
    elif expected_type == "list":
        return isinstance(value, list)
    return True


def validate_timeseries(df: pd.DataFrame, schema: dict[str, Any]) -> list[ValidationIssue]:
    """Validate timeseries DataFrame against schema."""
    issues: list[ValidationIssue] = []
    ts_schema = schema.get("timeseries", {})
    required_cols = ts_schema.get("required_columns", {})
    constraints = ts_schema.get("constraints", {})

    for col in required_cols:
        if col not in df.columns:
            issues.append(
                ValidationIssue("error", f"timeseries.{col}", f"Missing required column: {col}")
            )

    for col, constraint in constraints.items():
        if col in df.columns and "min" in constraint:
            min_val = constraint["min"]
            if (df[col] < min_val).any():
                issues.append(
                    ValidationIssue(
                        "error",
                        f"timeseries.{col}",
                        f"Values below minimum {min_val} found",
                    )
                )

    if "emissions" in df.columns and (df["emissions"] < 0).any():
        issues.append(
            ValidationIssue(
                "warning",
                "timeseries.emissions",
                "Negative emissions found (allowed for CCS scenarios)",
            )
        )

    return issues


def validate_agent_states(df: pd.DataFrame, schema: dict[str, Any]) -> list[ValidationIssue]:
    """Validate agent_states DataFrame against schema."""
    issues: list[ValidationIssue] = []
    as_schema = schema.get("agent_states", {})
    required_cols = as_schema.get("required_columns", {})
    constraints = as_schema.get("constraints", {})

    for col in required_cols:
        if col not in df.columns:
            issues.append(
                ValidationIssue("error", f"agent_states.{col}", f"Missing required column: {col}")
            )

    for col, constraint in constraints.items():
        if col in df.columns and "min" in constraint:
            min_val = constraint["min"]
            if (df[col] < min_val).any():
                issues.append(
                    ValidationIssue(
                        "error",
                        f"agent_states.{col}",
                        f"Values below minimum {min_val} found",
                    )
                )

    return issues


def validate_summary(summary: dict[str, Any], schema: dict[str, Any]) -> list[ValidationIssue]:
    """Validate summary.json dict against schema."""
    issues: list[ValidationIssue] = []
    sum_schema = schema.get("summary", {})
    required_fields = sum_schema.get("required_fields", {})

    for field, expected_type in required_fields.items():
        if field not in summary:
            issues.append(
                ValidationIssue("error", f"summary.{field}", f"Missing required field: {field}")
            )
        elif not _check_dtype(summary[field], expected_type):
            issues.append(
                ValidationIssue(
                    "error",
                    f"summary.{field}",
                    f"Expected type {expected_type}, got {type(summary[field]).__name__}",
                )
            )

    return issues


def validate_manifest(manifest: dict[str, Any], schema: dict[str, Any]) -> list[ValidationIssue]:
    """Validate manifest.yaml dict against schema."""
    issues: list[ValidationIssue] = []
    man_schema = schema.get("manifest", {})
    required_fields = man_schema.get("required_fields", {})

    for field, expected_type in required_fields.items():
        if field not in manifest:
            issues.append(
                ValidationIssue("error", f"manifest.{field}", f"Missing required field: {field}")
            )
        elif not _check_dtype(manifest[field], expected_type):
            issues.append(
                ValidationIssue(
                    "error",
                    f"manifest.{field}",
                    f"Expected type {expected_type}, got {type(manifest[field]).__name__}",
                )
            )

    return issues


def validate_bundle(run_dir: Path) -> list[ValidationIssue]:
    """Validate a complete results bundle in run_dir."""
    issues: list[ValidationIssue] = []
    schema = _load_schema()

    ts_path = run_dir / "timeseries.parquet"
    ts_csv = run_dir / "timeseries.csv"
    if ts_path.exists():
        ts_df = pd.read_parquet(ts_path)
        issues.extend(validate_timeseries(ts_df, schema))
    elif ts_csv.exists():
        ts_df = pd.read_csv(ts_csv)
        issues.extend(validate_timeseries(ts_df, schema))
    else:
        issues.append(
            ValidationIssue("error", "timeseries", "No timeseries.parquet or timeseries.csv found")
        )

    as_path = run_dir / "agent_states.parquet"
    as_csv = run_dir / "agent_states.csv"
    if as_path.exists():
        as_df = pd.read_parquet(as_path)
        issues.extend(validate_agent_states(as_df, schema))
    elif as_csv.exists():
        as_df = pd.read_csv(as_csv)
        issues.extend(validate_agent_states(as_df, schema))
    else:
        issues.append(
            ValidationIssue(
                "error",
                "agent_states",
                "No agent_states.parquet or agent_states.csv found",
            )
        )

    summary_path = run_dir / "summary.json"
    if summary_path.exists():
        with open(summary_path, encoding="utf-8") as f:
            summary = json.load(f)
        issues.extend(validate_summary(summary, schema))
    else:
        issues.append(ValidationIssue("error", "summary", "No summary.json found"))

    manifest_path = run_dir / "manifest.yaml"
    if manifest_path.exists():
        with open(manifest_path, encoding="utf-8") as f:
            manifest = yaml.safe_load(f)
        issues.extend(validate_manifest(manifest, schema))
    else:
        issues.append(ValidationIssue("error", "manifest", "No manifest.yaml found"))

    return issues
