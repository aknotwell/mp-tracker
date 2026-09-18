# API and domain contract

This document establishes the shared API conventions. The former Milestone 1 proposals below were adopted as Milestone 2 defaults when implementation was authorized; they can still be revised before the initial Alembic migration is approved.

## Shared API conventions

- API routes will be versioned beneath `/api/v1`; `/health` is an unversioned operational endpoint.
- Resource identifiers will be opaque UUIDs serialized as lowercase hyphenated strings. Clients must not infer ordering or meaning from them.
- Timestamps will be stored in UTC and returned as ISO 8601 strings with a `Z` suffix. API requests must include an offset when accepting a timestamp.
- JSON field names use `snake_case` to match the Python domain model.
- A successful delete returns `204 No Content`. Creation returns `201 Created`. Reads and updates return `200 OK`.
- Authentication failures use `401`; authenticated users lacking permission use `403`; absent resources use `404`; conflicts use `409`; validation failures use `422`.
- Validation errors use one stable envelope:

  ```json
  {
    "error": {
      "code": "validation_error",
      "message": "Request validation failed.",
      "details": [
        { "field": "ownership_status", "message": "Must be full_bottle or decant." }
      ]
    }
  }
  ```

- Unexpected errors use a generic message and correlation ID; stack traces and secrets are never returned.

## Pagination

Use offset pagination for the initial API: `limit` defaults to 25 and is capped at 100; `offset` defaults to 0. Collection responses use `{ "items": [], "total": 0, "limit": 25, "offset": 0 }`. Offset pagination is simple and sufficient for a personal-scale collection. A future high-churn endpoint may adopt cursors without changing existing routes.

## Fixed enums and rating rules

- `ownership_status`: `full_bottle | decant` only.
- `longevity`: `0-2h | 2-4h | 4-6h | 6-8h | 8h+`.
- `data_source`: `official_site | manual`.
- `dna_accuracy` and `projection` are integers from 1 through 10.
- Ratings contain exactly `dna_accuracy`, `longevity`, and `projection`; no value rating or maceration status is part of this product.
- Longevity is ordinal. Sorting best-to-worst must map `8h+`, `6-8h`, `4-6h`, `2-4h`, `0-2h` explicitly and must never rely on string ordering.

## Ownership and lifecycle

- Every user-owned resource is scoped to its owner on the server. A client-supplied user ID never grants access.
- Regular users cannot create or edit catalog records.
- Fragrances are created only by an automated scraper. An admin may edit an existing row to correct scraper errors but cannot manually create one.
- Collection items record only `full_bottle` or `decant`; the application does not track volume or depletion.
- Allow multiple independently ranked collection items for the same user, fragrance, and ownership status. This supports distinct fresh bottles and aged decants; no uniqueness constraint collapses them.
- Ratings are optional as a whole while an item is unrated. Once created, all three fields are required. Unrated items are omitted from Most Accurate and Best Longevity instead of being sorted last.

## Ranking boundaries

- Overall Favorites alone uses head-to-head choices and per-collection-item Elo.
- Most Accurate is a numeric sort over `dna_accuracy`.
- Best Longevity is an explicit ordinal sort over the longevity buckets.
- Accuracy and longevity never get pairwise comparison flows.
- Elo is attached to a collection item rather than a fragrance so separately owned instances rank independently.
- A `HeadToHeadMatchup` is an immutable audit record. Its exact snapshot fields and Elo parameters remain a Milestone 2/5 decision.

## Ranking eligibility proposal

Apply these initial eligibility rules:

- Overall Favorites matchup pool: owned by the current user and not deleted/archived. Attribute ratings are not required because favorite is independent of the three rating fields.
- Overall Favorites leaderboard: all non-deleted items with an Elo score, including items with zero comparisons.
- Most Accurate: only items with a complete attribute rating.
- Best Longevity: only items with a complete attribute rating.

## Authorization summary

| Capability | Anonymous | User | Admin |
| --- | --- | --- | --- |
| Read public catalog | Planned | Yes | Yes |
| Manage own collection and ratings | No | Yes | Yes |
| Read another user's private collection | No | No | No by default |
| Create a fragrance manually | No | No | No |
| Correct an existing scraper-created fragrance | No | No | Yes |
| Run scraper/import operations | No | No | To be decided |

Whether the catalog is readable without authentication will be finalized with the Milestone 4 endpoint contract.
