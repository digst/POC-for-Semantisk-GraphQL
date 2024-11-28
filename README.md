# DigstSGQL

Semantic GraphQL project for Digitaliseringsstyrelsen.
<https://redmine.magenta.dk/issues/62789>.

## Getting started

```sh
docker compose up -d --build
firefox http://localhost:8000/graphql/
```

Make sure to load data into the database:

```graphql
mutation {
  loadData
}
```

# Semantic GraphQL

We are not allowed to add a `@context` entry to the response map as per the
[GraphQL spec](https://spec.graphql.org/draft/#sec-Response-Format). Perhaps we
could add it as HTTP header?
<https://www.w3.org/TR/json-ld11/#interpreting-json-as-json-ld>

## Configuration

Parameters without a default value are required when deploying outside the
compose development environment.

Available options:

- `DATABASE__USER`
- `DATABASE__PASSWORD`
- `DATABASE__HOST`
- `DATABASE__PORT=5432`
- `DATABASE__NAME`

See `digstsqgl/config.py` for detailed information.
