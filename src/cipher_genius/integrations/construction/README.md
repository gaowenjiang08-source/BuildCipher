# BuildTrust construction integrations

This package defines production-facing boundaries without pretending that a local adapter is a commercial platform integration.

- `ConstructionCDEConnector`: provider-neutral read-only package contract.
- `LocalDirectoryCDEConnector`: filesystem reference implementation for integration tests and controlled imports.
- `inspect_ifc_bytes`: structural IFC STEP inspection with SHA-256 and entity metadata.
- `SQLiteConstructionIoTReplayState`: single-host persistent registry/replay state; stores credential references, never key bytes.
- `ConstructionMACProvider` / `ConstructionSignatureProvider`: provider-side operation contracts with no key-export method.
- `SQLiteCredentialGovernanceStore`: credential lifecycle, rotation, certificate inventory, and secret-free operation receipts.
- `LocalReferenceHMACProvider`: in-process localhost provider for IoT MAC and BIM manifest signing; not a production KMS/HSM.

Not included: cloud/HSM adapters, vendor CDE authentication, remote approval/locking/upload workflows, full IFC geometry/schema evaluation, or distributed replay consensus.
