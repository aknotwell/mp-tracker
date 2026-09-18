# Frontend state ownership

Use the narrowest owner appropriate for each kind of state.

## TanStack Query: server-owned state

TanStack Query is the source of truth for data read from or persisted to the API, including:

- the current user and authentication bootstrap result;
- catalog houses, fragrances, notes, search, and filters sent to the server;
- collection items, volumes, and attribute ratings;
- all leaderboard results and comparison counts;
- the server-selected matchup pair and the result of submitting a choice.

Mutations invalidate or update well-defined query keys. Zustand must never mirror these resources.

## Zustand: ephemeral ranking-session UI state only

Zustand may hold temporary interaction state that has no durable server meaning, such as:

- whether the current matchup card is animating;
- a locally dismissed/temporarily skipped pair for the current browser session;
- presentation progress within a ranking session;
- transient keyboard-selection or transition state shared across ranking components.

Refreshing the page may safely discard this state. Any state that must survive refresh, affect ranking results, or be shared across devices belongs on the server and is accessed through TanStack Query.

## Local component and URL state

- Component state owns isolated form inputs and open/closed controls.
- URL search parameters own shareable navigation state such as search terms, filters, sort, pagination, and selected leaderboard tab.
- Do not introduce a global store merely to avoid passing props through one or two component levels.
