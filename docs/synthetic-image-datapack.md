# Research image datapack

Governs the fixture image catalog used by Reports. It is a research corpus,
not a training release and not an open datapack for redistribution.

The product owner confirmed on 23 August 2026 that sourced Islamophobic
memes belong in this corpus because the product is a research tool. That
deviation is recorded in `docs/adr/0007-research-image-corpus.md`.

## What is in the repository

- Manifest: `apps/web/src/fixtures/meme-datapack/manifest.json`
- Rows: `apps/web/src/fixtures/meme-datapack/items.json`
- Checksums for later seed: `apps/web/src/fixtures/meme-datapack/checksums.json`
- Image files: `apps/web/public/media/fixtures/memes/img-ex-*.png|jpg`

Each row stores a **dataset annotation** (the label from the labeling brief)
and enough fields for a **fixture prediction**. Those two stay separate, per
spec §10.3: an original label is never silently treated as an Amanah
prediction or a human review.

Titles and alt text describe form. They do not quote slogans. The image
itself is the research artifact and stays blurred until revealed.

## Do not store images as base64 in Postgres

Base64 in a row:

- inflates backups and WAL by about a third;
- cannot be cached by a CDN;
- cannot be blurred or replaced without rewriting the row;
- leaks into logs if a row is ever printed.

The contract the frontend already uses is filename and byte size only.
Pixels never cross `src/api/`.

## Storage that will survive a backend

1. **Object storage** (Supabase Storage, private bucket) holds the bytes.
2. **Postgres** holds the row: `id`, `storage_path`, `sha256`, `mime`,
   `byte_size`, `manifest_id`, `dataset_row_id`, annotation JSON, prediction
   JSON, `taxonomy_version`, `model_name`, `model_version`, `review_state`.
3. The API returns a **short-lived signed URL** plus the classification
   object. The browser never sees a permanent public link to harmful media
   once live mode is on. Fixture mode serves the repo path.
4. The UI blurs the image until a person reveals it.

## How to seed later

When the backend importer (B-S9A) is ready:

1. Keep this manifest. Add a real `file_sha256` of the JSONL export.
2. Upload each `img-ex-*` file to the private bucket. Use
   `checksums.json` to verify bytes.
3. Insert one content row per `id` with `source_kind = open_datapack` and
   public `source/platform = N/A`.
4. Store `dataset_annotation` in the annotation column. Run classification
   as a separate write. Do not copy the annotation into the prediction
   column and call it a model result.
5. Do not treat this pack as redistributable. A later public datapack still
   needs a reviewed licence, hash, and approval state.

## Image checking on Reports

`POST /v1/evidence/classifications` is the live shape. The request is
`image_filename`, `image_byte_size`, and an optional `example_id`. The
response is spec §9.5: relevance, stance, types, severity, narrative tags,
score, confidence tier, rationale, model version, review required.

Fixture mode picks a catalog row from the filename (or `example_id`) and
does not read pixels. Live mode should accept a multipart upload on the
API, write the object, hash it, classify behind FastAPI, and return this
same JSON. Gemini stays on the server. The browser does not call Gemini.
