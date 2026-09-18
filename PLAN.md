# Fragrance Collection Tracker — Implementation Plan

## Purpose and implementation guardrails

This plan covers a monorepo with sibling `backend/` and `frontend/` applications. It intentionally contains no implementation code. Work should begin only after the relevant milestone and its open decisions are approved.

The decided stack is:

- Backend: async FastAPI, SQLAlchemy 2.0, Alembic, and SQLite through `sqlite+aiosqlite`.
- Frontend: Next.js App Router, Tailwind CSS, shadcn/ui, and TanStack Query for server state.
- Client-only state: Zustand may hold only temporary Overall Favorites ranking-session state; persisted/server-owned data stays in TanStack Query.
- Authentication: Google OpenID Connect is the only sign-in method. The application stores no passwords and provides no local registration, password login, password reset, or password-recovery flow. After validating Google's authorization-code response, the backend issues its own short-lived JWT access token plus an httpOnly refresh cookie for the application session.

The product model is also fixed unless a conflict is found and explicitly raised:

- Collection ownership is only `full_bottle` or `decant`; there is no sample or finished status. An item is depleted when `volume_ml_remaining` reaches zero.
- Ratings contain exactly `dna_accuracy`, `longevity`, and `projection`.
- Elo belongs to an individual collection item, not the underlying fragrance.
- Head-to-head matchups are an immutable audit log and apply only to Overall Favorites.
- Fragrances are created only by automated scrapers. Admins may correct existing flagged rows but may never manually create fragrances.

## Approval gates that affect later work

1. **Ranking-mechanism gate (must be confirmed before Milestones 5–6):** Overall Favorites uses pairwise comparisons and per-item Elo. Most Accurate is a numeric descending sort on `dna_accuracy`. Best Longevity is a bucket sort using an explicit ordinal mapping (`0-2h < 2-4h < 4-6h < 6-8h < 8h+`), never alphabetical/string ordering. Accuracy and longevity do **not** get separate comparison flows.
2. **Designer-original sourcing gate (must be decided before Milestone 10 is complete):** the Montagne catalog can identify originals it clones but cannot, by itself, provide authoritative original-fragrance rows. The sourcing strategy must be selected from the options described in Milestone 10 (or another approved option).
3. **Security/deployment gate (needed before authentication is finalized):** confirm the frontend/backend production origins and hosting topology so cookie scope, CORS, CSRF protection, and secure-cookie behavior are correct.

---

## Milestone 1 — Domain contract and project foundations

**Delivers**

- Backend and frontend project structure, environment/config conventions, dependency locking, linting/formatting/type-checking, and test layout.
- A concise API/domain contract covering enums, identifiers, timestamps, pagination, validation errors, and ownership/authorization rules.
- Agreed behavior for depleted items, duplicate ownership records, nullable ratings, and ranking eligibility before those decisions become schema constraints.
- A documented boundary between server state (TanStack Query) and temporary ranking-session state (Zustand).

**Depends on**

- Approved stack and fixed core entities described above.

**Complexity/risk:** Routine, with careful review of domain rules.

**Open questions / decisions requiring input**

- May one user own multiple independently ranked collection items for the same fragrance and ownership type? The model strongly suggests yes, but the uniqueness rule must be explicit.
- Are depleted items (`volume_ml_remaining = 0`) retained in the active collection and eligible for all leaderboards/comparisons, or merely retained in history and excluded from future matchups?
- Are ratings optional until supplied, and should unrated items be omitted from Most Accurate/Best Longevity rather than sorted last?
- What API pagination convention is preferred (offset/limit or cursor)?

## Milestone 2 — SQLAlchemy schema and domain validation

**Delivers**

- SQLAlchemy 2.0 async models for `User`, `House`, `Fragrance`, `Note`, `FragranceNote`, `UserCollectionItem`, `ItemAttributeRating`, and `HeadToHeadMatchup`.
- Required enums and constraints, including:
  - ownership limited to `full_bottle | decant`;
  - `dna_accuracy` and `projection` limited to integers 1–10;
  - longevity limited to `0-2h | 2-4h | 4-6h | 6-8h | 8h+`;
  - total/remaining volume constraints, including nonnegative remaining volume and remaining volume not exceeding total volume;
  - self-references for clone houses and clone fragrances;
  - Elo and comparison counters stored on each collection item;
  - immutable matchup records sufficient to audit and recompute Elo.
- Indexes and relationship loading choices for collection views, leaderboards, scraper upserts, and review queues.
- Pydantic request/response schemas that prevent clients from setting protected fields such as Elo totals, scraper provenance, or admin status.

**Depends on**

- Milestone 1 domain decisions.

**Complexity/risk:** Needs careful review because constraints and audit fields are costly to change later.

**Open questions / decisions requiring input**

- What initial Elo value and numeric precision should be stored (for example, integer/real with an initial value such as 1000 or 1500)?
- Does a comparison allow only a winner, or also a tie/skip? A skip should normally not create a scored matchup, but this must be specified.
- Which matchup snapshot fields are required for reproducible audits: pre/post scores, K-factor used, expected probabilities, algorithm version, and presentation timestamp?
- Should concentration and gender be strict enums now; if so, what exact allowed values and an unknown/unisex policy?
- Must fragrance names be unique within a house, and how should concentrations/flankers affect identity?

## Milestone 3 — Alembic migrations and database lifecycle

**Delivers**

- Alembic configured for the async SQLAlchemy metadata and SQLite connection.
- Reviewed initial migration creating tables, constraints, indexes, and enum-compatible SQLite columns/checks.
- Repeatable local database setup, upgrade, downgrade, and test-database procedures.
- Migration tests that upgrade an empty database and verify essential constraints.
- A documented SQLite evolution strategy, including batch migrations where SQLite cannot alter constraints directly.

**Depends on**

- Milestone 2 schema approval.

**Complexity/risk:** Routine, with careful review for SQLite constraint and batch-migration behavior.

**Open questions / decisions requiring input**

- Is SQLite the intended production database as well as local development database?
- Should the first admin user be created by a CLI/bootstrap command, environment-driven seed, or a one-time promotion workflow?
- Is downgrade support required for every migration in production, or is forward repair acceptable after the initial release?

## Milestone 4 — Authentication, authorization, and core CRUD API

**Delivers**

- Google-only OpenID Connect login using the server-side authorization-code flow with PKCE, `state`, and `nonce`; validation of Google's ID-token signature, issuer, audience, expiration, stable `sub` identifier, and verified email; short-lived application access-JWT issuance; refresh-token rotation/revocation; logout; and current-user endpoints.
- No local password column, password hashing, password registration, password login, password reset, or password-recovery endpoints.
- The refresh token in an httpOnly cookie with production-appropriate `Secure`/`SameSite` settings; access-token handling documented and implemented consistently on the frontend later.
- User-scoped collection CRUD, volume updates, and upsert/delete behavior for the one rating record associated with each collection item.
- Read-only catalog endpoints for houses, fragrances, notes, search/filtering, and fragrance details.
- Admin-only editing of existing fragrance rows, restricted to correcting scraper errors/review fields; no public or admin fragrance-create endpoint.
- Review-queue endpoints for `needs_review` rows and authorization tests preventing cross-user access or unauthorized catalog mutation.

**Depends on**

- Milestone 3 migrations and Milestone 1 API conventions.

**Complexity/risk:** Needs careful review because token rotation, cookie security, and object-level authorization are security-sensitive.

**Open questions / decisions requiring input**

- Should any verified Google account be allowed to create an application account on first login, or should access be limited to an email/domain allowlist?
- How should the first Google-authenticated user be promoted to administrator?
- What are the access/refresh lifetimes, and should refresh tokens be stored hashed in a dedicated session table to support rotation, logout, and device revocation? (Recommended, but it adds a supporting auth entity.)
- Will frontend and backend share a site/origin in production? This determines cookie, CORS, and CSRF details.
- Which fragrance fields may an admin correct, and does every correction need its own audit trail?
- Does deleting a collection item hard-delete its ratings/matchups, soft-delete the item, or forbid deletion once comparisons exist to preserve Elo auditability?

## Milestone 5 — Elo engine and immutable comparison transaction

**Delivers**

- A pure, unit-tested Elo calculation module with an explicit initial rating, K-factor policy, rounding/storage rules, and deterministic outputs.
- A transactional comparison service that validates both items belong to the current user, records one immutable `HeadToHeadMatchup`, updates both per-item Elo scores, and increments comparison counts atomically.
- Idempotency/concurrency protection so retries or double-clicks cannot score one shown matchup twice.
- An Elo recomputation/audit utility that can replay the immutable log and detect drift.
- Tests for expected-score math, upset results, repeated comparisons, invalid/cross-user input, replay, and rollback on failure.

**Depends on**

- Milestone 4 authenticated collection access and Milestone 2 audit fields.
- **Explicit approval of the ranking-mechanism gate:** only Overall Favorites uses pairwise Elo; accuracy and longevity remain sorted attribute views and get no comparison flows.

**Complexity/risk:** Needs careful review because correctness, concurrency, and audit reproducibility are central product behavior.

**Open questions / decisions requiring input**

- Confirm the ranking split exactly as stated in the approval gate.
- Choose initial Elo, K-factor (fixed or comparison-count tiers), and tie support.
- Should edits/deletion of historical collection items trigger recomputation, preserve a snapshot, or be restricted?
- What should an Elo reset mean: delete/archive matchup history, append a new ranking epoch, or recompute from the standard initial score?

## Milestone 6 — Matchup selector and leaderboard queries

**Delivers**

- A server-side selector that proposes two eligible collection items for Overall Favorites without scoring merely displayed/skipped pairs.
- Selection rules that reduce immediate repeats, improve coverage for low-comparison items, and remain useful for small collections.
- Three user-scoped leaderboard endpoints:
  - **Overall Favorites:** descending per-item Elo with deterministic tie-breakers.
  - **Most Accurate:** descending numeric `dna_accuracy`, with deterministic tie-breakers.
  - **Best Longevity:** descending semantic duration using an explicit ordinal `CASE WHEN` mapping (or equivalent) for `0-2h < 2-4h < 4-6h < 6-8h < 8h+`; it must **not** use default enum/string/alphabetical sorting.
- Eligibility, null-handling, pagination, and tests for all rankings, including a regression test proving longevity order is ordinal.

**Depends on**

- Milestone 5 comparison engine and approved eligibility rules from Milestone 1.
- The same ranking-mechanism approval: no accuracy or longevity matchup selector/flow.

**Complexity/risk:** Needs careful review for selector fairness, repeat avoidance, and exact ordering semantics.

**Open questions / decisions requiring input**

- What minimum collection size and rating completeness make an item eligible for Overall Favorites?
- Should selector priority be random-with-weights, least-compared first, uncertainty-based, or a simpler coverage heuristic for version one?
- May the same pair reappear after a cooldown; if so, should cooldown use number of intervening matchups or elapsed time?
- What are deterministic secondary sorts for equal accuracy/longevity/Elo (for example Elo, name, creation date, or stable ID)?
- Confirm unrated/depleted item inclusion rules decided in Milestone 1.

## Milestone 7 — Frontend application shell and API integration

**Delivers**

- Next.js App Router structure, Tailwind theme, shadcn/ui foundations, responsive navigation, loading/error/empty-state patterns, and accessibility baseline.
- Typed API client, authentication bootstrap/refresh flow, protected routes, and consistent backend error display.
- TanStack Query provider, query-key conventions, cache invalidation rules, and mutations for server-owned data.
- Zustand limited to ephemeral Overall Favorites session concerns such as the currently displayed pair or local transition state; collection/catalog/rating/leaderboard data remains in TanStack Query.

**Depends on**

- Stable Milestone 4 authentication/API contracts and Milestone 6 endpoint shapes.

**Complexity/risk:** Routine, with careful review of SSR/client boundaries and refresh-token behavior.

**Open questions / decisions requiring input**

- What visual direction, application name, and mobile/desktop priorities should guide the shell?
- Where should the access token live (recommended: memory, restored through the refresh endpoint), and is cross-tab session synchronization required?
- Is server-side rendering of authenticated pages important, or may protected collection screens be client-driven?

## Milestone 8 — Collection management and rating UI

**Delivers**

- Catalog browsing/search and fragrance-detail views.
- Add-to-collection flow limited to `full_bottle` and `decant`, with total/remaining volume capture.
- Collection list/detail/edit/remove experiences, depletion represented solely by zero remaining volume.
- Rating editor with only the three approved attributes: 1–10 DNA accuracy, one longevity bucket, and 1–10 projection.
- Optimistic updates only where safe, followed by authoritative query invalidation/refetch.
- Responsive, keyboard-accessible validation and empty/error states.

**Depends on**

- Milestone 7 shell/integration and Milestone 4 CRUD endpoints.

**Complexity/risk:** Routine.

**Open questions / decisions requiring input**

- Should volume accept decimals, and what display/input precision and units are required?
- Is the initial `volume_ml_remaining` always equal to total volume, or may a partially used bottle/decant be entered immediately?

## Milestone 9 — Ranking and leaderboard UI

**Delivers**

- Overall Favorites comparison experience: request a server-selected pair, choose the preferred owned item, submit once, show progress/feedback, and fetch the next pair.
- Protection against double submission, stale pairs, refresh/navigation loss, and session-only UI state leaking into persisted state.
- Separate leaderboard views/tabs for Overall Favorites, Most Accurate, and Best Longevity.
- Clear copy explaining that Overall is learned from pairwise choices, while accuracy and longevity are direct attribute sorts.
- Longevity labels displayed in semantic best-to-worst order consistent with the backend ordinal mapping.
- Accessibility, responsive layouts, loading/empty/error states, and frontend tests for the ranking split.

**Depends on**

- Milestone 6 endpoints, Milestone 7 state architecture, and Milestone 8 collection/rating flows.
- Final confirmation that only Overall Favorites is pairwise.

**Complexity/risk:** Needs careful review because mutation idempotency and clear ranking semantics directly affect user trust.

**Open questions / decisions requiring input**

- Should users see live Elo numbers/comparison counts, only ordered ranks, or both?
- Is a “skip this pair” control desired, and should skipped pairs have a short session cooldown without creating a matchup log entry?
- Should users be able to undo the immediately previous choice? Supporting this safely changes the immutable-log/recompute design and must be decided before implementation.

## Milestone 10 — Montagne scraper, review workflow, and original-fragrance resolution

**Delivers**

- `app/services/scrapers/montagne_scraper.py` as the only Montagne fragrance creation path, with network fetching separated from deterministic parsing for testability.
- Idempotent catalog imports/upserts, stable source identifiers where available, source provenance (`official_site` or `manual`), logging, retry/rate-limit behavior, and fixture-based parser tests.
- Static `KNOWN_HOUSES` matching performed longest-prefix-first when parsing `INSPIRED BY X Y`.
- Successful matches create/link the relevant data normally. Failed house matches still create the Montagne product, set `needs_review = true`, and leave inspired-by fields null.
- Admin review UI/API integration that edits existing flagged rows only. There is no manual/admin create-fragrance flow.
- A documented, implemented policy for resolving the referenced designer/original fragrances.

**Depends on**

- Milestones 2–4 for schema, migrations, protected catalog operations, and review endpoints.
- **Designer-original sourcing gate:** a strategy must be approved before this milestone is considered complete.

**Complexity/risk:** Needs careful review because external markup changes, entity resolution, idempotency, provenance, and source terms can corrupt the shared catalog.

**Open questions / decisions requiring input**

- **Required decision: how are designer/original fragrance rows created when Montagne is not their source?** Candidate approaches:
  1. Add an approved second scraper/import source that creates and enriches canonical original House/Fragrance rows. This offers richer data but adds source reliability, matching, rate-limit, and terms-of-use risk.
  2. Let the automated Montagne import create lightweight placeholder House/Fragrance records from the parsed inspiration name, mark them for later automated enrichment/review, and never expose a manual creation endpoint. This keeps imports self-contained but risks duplicates and low-confidence identity matching.
  3. Stage unresolved inspiration references in a separate import-resolution queue and create/link canonical originals only when a later approved automated source resolves them. This preserves catalog quality but leaves clone links incomplete longer.
- Which option above is approved, and which external sources are legally and technically permitted? A source must not be added to `data_source` until its use and extraction method are approved.
- What exact Montagne page/region is authoritative, how is the scraper triggered (CLI, scheduled job, or admin-triggered job), and how often should it run?
- Does `manual` provenance mean only an admin correction to a scraper-created row, or may another automated import legitimately assign it? It must not become a manual creation loophole.
- When a known house is found but the exact original fragrance cannot be resolved, should the Montagne row be created and flagged, linked to a placeholder, or staged unresolved?
- How should products removed or renamed upstream be handled without deleting user-owned history?

## Milestone 11 — Integrated verification, operations, and release readiness

**Delivers**

- Backend unit/integration coverage for constraints, auth rotation, authorization, CRUD, Elo/replay, selection, ranking sorts, scraper idempotency, and admin restrictions.
- Frontend component/integration coverage for auth, collection/rating flows, ranking submissions, and all three leaderboards.
- End-to-end happy paths and important failure paths using an isolated database and deterministic scraper fixtures.
- CI checks for formatting, linting, types, tests, migration validity, and frontend production build.
- Operational documentation for configuration/secrets, migrations, backups/restores, admin bootstrap, scraper execution, failed-import recovery, and Elo audit/recompute.
- Security review covering Google OIDC code exchange and ID-token validation, PKCE/`state`/`nonce`, application JWT validation, refresh rotation, cookie/CSRF/CORS settings, rate limits, input validation, and log redaction.

**Depends on**

- All approved product milestones, especially the chosen catalog-source strategy.

**Complexity/risk:** Needs careful review; release confidence depends on realistic integration and recovery testing.

**Open questions / decisions requiring input**

- What is the target deployment platform/topology and production backup policy?
- What browser/device support and minimum automated coverage are release requirements?
- Is observability limited to structured logs initially, or are error tracking and metrics required for version one?

---

## Proposed implementation order and approval checkpoints

1. Approve the domain decisions in Milestone 1.
2. Implement and review schema (Milestone 2), then migrations (Milestone 3).
3. Implement auth and core CRUD (Milestone 4).
4. Reconfirm the ranking-mechanism gate, then implement Elo (Milestone 5) and matchup/leaderboard queries (Milestone 6).
5. Implement the frontend shell (Milestone 7), collection/rating UI (Milestone 8), and ranking UI (Milestone 9).
6. Decide the designer-original sourcing strategy, then complete the scraper and review workflow (Milestone 10).
7. Complete integrated verification and release preparation (Milestone 11).

No implementation should begin until this plan, or a specifically named milestone within it, is approved.
