# s3-file-uploader

> Content-addressed object-storage uploader with SHA-256 integrity verification and deduplication by digest.

### What it is

Content-addressed object-storage uploader with integrity verification.

Real, working Python for the Retsumdk ecosystem with an executable test suite.

## Getting started

```bash
pip install -r requirements.txt
pytest -q
```

## Features

- **Content addressing** — every uploaded buffer is keyed by its SHA-256 digest, so identical
  bytes always resolve to the same object.
- **Deduplication** — a repeated upload is reported with `"new": false` and counted in
  `uploader.duplicates` instead of being stored twice.
- **Integrity verification** — `verify()` re-hashes the candidate bytes and compares them
  against both the stored digest and the stored payload, so truncation or corruption fails closed.
- **Pluggable storage** — `LocalObjectStore` is a plain digest-keyed mapping; point `Uploader`
  at any object implementing `exists()`, `get()`, and the bucket write to move to a real backend.
- **Zero runtime dependencies** — the module is standard-library only (`hashlib`, `dataclasses`).

## Usage

```python
from s3_file_uploader import LocalObjectStore, Uploader

store = LocalObjectStore()
uploader = Uploader(store)

first = uploader.upload(b"quarterly report v1")
second = uploader.upload(b"quarterly report v1")

first["new"]   # True  — stored under its SHA-256 digest
second["new"]  # False — deduplicated
uploader.saved       # 1
uploader.duplicates  # 1

uploader.verify(first["digest"], b"quarterly report v1")  # True
uploader.verify(first["digest"], b"tampered")             # False
```

`upload()` returns a receipt dict:

| Key | Type | Meaning |
|---|---|---|
| `digest` | `str` | Hex SHA-256 of the uploaded bytes (the object key). |
| `size` | `int` | Length of the uploaded payload in bytes. |
| `new` | `bool` | `True` when this upload created the object; `False` on a dedupe hit. |
| `verified` | `bool` | `True` once the digest has been computed over the posted bytes. |

## Architecture

```
        caller bytes
             │
             ▼
   ┌───────────────────┐   sha256(data)   ┌──────────────────────────┐
   │     Uploader      │ ───────────────► │     LocalObjectStore     │
   │                   │                  │  { digest: StoredObject }│
   │  saved            │ ◄─── exists() ── │                          │
   │  duplicates       │      get()       │  StoredObject(           │
   └───────────────────┘                  │    digest, size, bytes)  │
             │                            └──────────────────────────┘
             │ verify(digest, data)
             ▼
   re-hash + byte-compare → bool
```

`Uploader` owns the dedupe policy and the counters; `LocalObjectStore` owns the bytes. Splitting
them means a production S3 (or GCS/R2) client can replace the store without changing call sites.

## API reference

### `LocalObjectStore`

| Method | Returns | Description |
|---|---|---|
| `exists(digest)` | `bool` | Whether an object with this digest has been stored. |
| `get(digest)` | `StoredObject` | Retrieves the object; raises `KeyError` when absent. |

### `Uploader(store)`

| Member | Description |
|---|---|
| `upload(data)` | Hashes `data`, stores it when new, returns the receipt dict. |
| `verify(digest, data)` | `True` only when `data` re-hashes to `digest` **and** matches the stored bytes. |
| `saved` | Count of objects created by this uploader. |
| `duplicates` | Count of deduplicated uploads seen by this uploader. |

## Real-world use case

An agent fleet writes the same artifacts repeatedly — a shared prompt bundle, a serialized tool
schema, a model checkpoint chunk. Hashing on the way in lets the storage tier collapse those
repeat writes into one object and hand every worker the same digest, while `verify()` gives the
consumer a cheap way to prove the bytes it read back are the bytes the producer wrote. The same
two calls are the entire contract, so the pattern drops into an existing upload path without a
rewrite.

## Configuration

No environment variables and no credentials are read by this module — it is a local,
in-process reference implementation of the digest/dedupe/verify contract.
`requirements.txt` pulls only `pytest` for the test suite.

## Testing

```bash
pip install -r requirements.txt
pytest -q
```

Three tests cover digest-keyed deduplication, verification round-trips, and rejection of an
unknown/corrupt digest. The suite has no network or filesystem dependencies.

## License

[MIT](LICENSE) © Retsumdk
