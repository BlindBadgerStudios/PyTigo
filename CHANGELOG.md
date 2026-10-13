# Changelog

All notable changes to PyTigo are documented here. Versions follow the git tags (`vX.Y.Z`).

## 0.4.5 (2026-10-13)

### Fixed
- Local CCA: better HTTP error handling (`17ff6f2`, 2026-08-19). Responses are streamed and
  Content-Length enforcement is disabled after the status check, because some CCA firmware
  advertises a wrong length. HTTP/auth errors still surface as `HTTPError`, and a truncated
  body raises a clear `RuntimeError` instead of a misleading `ChunkedEncodingError`.
- `get_aggregate(level=...)` / `get_combined(agg=...)` type hints now match the cloud API:
  `Literal["minute", "min", "day"]` (`"min"` is kept as an alias and sent unchanged).
  Unsupported values such as `"hour"` (rejected by the API with HTTP 400) now raise
  `ValueError` before any request is made.
- Replaced deprecated `datetime.utcnow()` calls in the local client.
- Local client `_parse_iso` converts timezone-aware inputs to naive UTC instead of dropping
  the offset (previously `...+00:00` and `...-07:00` were treated as the same instant).
- mypy clean (`TigoCSVRow.values` is now typed as a `Mapping`).

### Added
- `pytigo.models.CLOUD_AGGREGATE_PARAMS` / `CloudAggregateParam` (`Pin`, `Vin`, `Iin`, `RSSI`,
  `Inv_AC`, `Inverter_AC`) and `CLOUD_AGGREGATE_LEVELS` / `AggregateLevel`.
- `TigoClient` logs a WARNING for aggregate params outside the allowed set (the request is
  still sent, so existing callers are unaffected). `TigoClient(..., strict_params=True)`
  raises `ValueError` instead.
- Docs: cloud panel temperature is not available (temperature params return HTTP 400).

### Changed
- Tests, README and examples use placeholder LAN addresses; tests use a dummy CCA password.

## 0.4.4 (2026-04-09)

- Last published release. See the git history for earlier changes.
