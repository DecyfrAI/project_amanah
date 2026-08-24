# Amanah synthetic demo datapack v1

## Purpose

Provide a deterministic, redistributable datapack that demonstrates Amanah's
reviewed open-datapack import, provenance, classification, metrics, filters, and
review flow when an external research dataset is unnecessary or not yet
licensed for the demo.

## Origin and licence

- Creator/provider: Project Amanah
- Version: 1.0.0
- Created: 24 August 2026
- Licence: CC0-1.0
- Permitted uses: public demos, testing, research, modification, and
  redistribution
- Approval basis: the project owner requested a synthetic demo datapack on
  24 August 2026

Every row was written for this repository. No row was copied from a platform,
publication, person, or external dataset.

## Contents

The 12 English rows cover Canada, the United States, and the United Kingdom.
They deliberately include benign Muslim speech, neutral reporting,
counterspeech/quotation, policy criticism, missing context, unrelated speech,
and synthetic examples of exclusion or collective blame. There are no author
identifiers or source URLs.

The `expected_*` columns are original dataset annotations used to explain the
intended scenario. They are not Amanah predictions, review decisions, accuracy
claims, or ground truth for real-world prevalence.

## Limitations

- This is fixture data, not live monitoring and not a representative sample.
- Counts and rates derived from it must remain labelled fixture/demo.
- It cannot support claims about a platform, country, population, or trend.
- The sample is intentionally tiny and class-balanced for demonstration value.
- Model output may differ from the annotations and still requires human review.
- The pack contains text only; it does not demonstrate image upload or image
  classification.

## Reproduction

The reviewed CSV is `datapacks/data/amanah-synthetic-demo-v1.csv`. Its exact
SHA-256 is recorded in `datapacks/manifests/amanah-synthetic-demo-v1.yml` and is
verified before any database write.
