# Reviewed datapacks

This directory contains small datapacks that the repository is permitted to
redistribute. A file is runnable only when all of the following agree:

1. `config/datapacks.example.yml` enables its stable manifest ID.
2. A manifest in `datapacks/manifests/` records its provenance, licence,
   permitted uses, exact SHA-256, schema mapping, and approval.
3. A dataset card in `datapacks/cards/` states its purpose and limitations.
4. The file hash still matches the reviewed artifact.

Large, restricted, personal, or externally licensed data must not be committed
here unless its exact licence and repository data-policy review permit
redistribution. The ETL importer never downloads arbitrary URLs.

## Included demo pack

`amanah-synthetic-demo-v1` is a small project-authored fixture for demonstrations
and pipeline rehearsal. It contains no copied posts, real people, author IDs, or
provider URLs. Its dataset annotations are test expectations only; the importer
does not turn them into Amanah predictions or human-review decisions.
