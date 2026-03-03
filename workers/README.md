# Governed Workers

This directory contains worker registrations for external projects that are governed by the bootstrap.

## B-Mode Integration

Workers registered here are:
- External projects maintaining their own structure
- Loaded by relative path resolved from the bootstrap repo root
- Governed through bootstrap execution context
- Subject to bootstrap gates (G1-G4)

## Worker Structure

Each worker is registered in its own subdirectory containing:
- `worker.yaml` - Worker metadata and configuration

## Registered Workers

### gmail_bill_intelligence
Gmail invoice extraction and bill scheduling worker.
- **Location (relative)**: `../gmail-bills`
- **Phases**: ingest, classify, parse_attachments, extract, persist, schedule, alerts
- **Language**: Python
