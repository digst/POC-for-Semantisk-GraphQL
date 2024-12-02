# DigstSGQL

Semantic GraphQL project for Digitaliseringsstyrelsen.
<https://redmine.magenta.dk/issues/62789>.

## Getting started

```sh
docker compose up -d --build
firefox http://localhost:8000/graphql
```

Load data into the database:

```graphql
mutation {
  loadData
}
```

# Semantic GraphQL

TODO

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
