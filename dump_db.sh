#!/bin/bash

export $(grep -v '^#' .env | xargs)

DUMP_DIR="./mongo_dump"
mkdir -p "$DUMP_DIR"

TIMESTAMP=$(date +%F_%H-%M-%S)
ARCHIVE_NAME="svitlo-power-$TIMESTAMP.gz"

docker compose exec svitlo-power-mongo mkdir -p /dump

docker compose exec svitlo-power-mongo \
  mongodump \
  --username "$MONGO_INITDB_ROOT_USERNAME" \
  --password "$MONGO_INITDB_ROOT_PASSWORD" \
  --authenticationDatabase "admin" \
  --db "$MONGO_DB" \
  --archive="/dump/$ARCHIVE_NAME" \
  --gzip

docker cp svitlo-power-mongo:/dump/$ARCHIVE_NAME $DUMP_DIR/

docker compose exec svitlo-power-mongo rm /dump/$ARCHIVE_NAME

echo "MongoDB dump completed: $DUMP_DIR/$ARCHIVE_NAME"
