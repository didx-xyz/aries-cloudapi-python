#!/bin/bash
set -e

#------------------------------------------------------------------------------
# Main Program
#------------------------------------------------------------------------------

usage() {
  cat <<EOF
Usage: $0 [option]
  -o,   --owner <owner>               Set database owner
  -d,   --drop-db                     Drop databases
  -l,   --list-db                     List databases
  -h,   --help                        Display this help and exit

  NOTE:

EOF
}

main() {
  #source vars.sh
  while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
    -o | --owner)
      owner="$2"
      shift
      shift
      ;;
    -d | --drop-db)
      operation="drop"
      shift
      ;;
    -l | --list-db)
      operation="list"
      shift
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      usage
      exit 1
      ;;
    esac
  done

  if [[ -z $owner ]]; then
    echo "Error: Owner is not set."
    usage
    exit 1
  fi

  case $operation in
  "drop")
    drop_db_function "$owner"
    ;;
  "list")
    list_db_function "$owner"
    ;;
  *)
    echo "Error: No operation selected (-d, --drop-db or -l, --list-db)."
    usage
    exit 1
    ;;
  esac
}

#------------------------------------------------------------------------------

# A function to print out error, log and warning messages along with other status information
# Copied from https://google-styleguide.googlecode.com/svn/trunk/shell.xml#STDOUT_vs_STDERR
err() {
  echo "[$(date +'%Y-%m-%dT%H:%M:%S%z')]: ERROR: $@" >&2
  exit
}

log() {
  echo "[$(date +'%Y-%m-%dT%H:%M:%S%z')]: INFO: $@" >&1
}

wrn() {
  echo "[$(date +'%Y-%m-%dT%H:%M:%S%z')]: WARNING: $@" >&1
}

# Export print function definitions to sub-shell

export -f err
export -f log
export -f wrn

drop_db_function() {
  local DB_OWNER="$1"
  local STEP="drop-db"
  log "$STEP: in progress"
  DB_LIST=$(PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -t \
    -c "SELECT datname FROM pg_database JOIN pg_user ON (pg_database.datdba = pg_user.usesysid) \
    WHERE pg_user.usename = '$DB_OWNER' AND datname NOT IN ('postgres', $(echo $DB_EXCLUDE \
    | sed "s/,/','/g" \
    | sed "s/\(.*\)/'\1'/"));")
  for DB in $DB_LIST; do
    (
      log "Dropping database: $DB"
      PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -c "DROP DATABASE \"$DB\""
    ) &
  done
  wait
  log "$STEP: done"
  echo ""
}

list_db_function() {
  local DB_OWNER="$1"
  local STEP="list-db"
  log "$STEP: in progress"
  DB_LIST=$(PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -t \
    -c "SELECT datname FROM pg_database JOIN pg_user ON (pg_database.datdba = pg_user.usesysid) \
    WHERE pg_user.usename = '$DB_OWNER' AND datname NOT IN ('postgres', $(echo $DB_EXCLUDE \
    | sed "s/,/','/g" \
    | sed "s/\(.*\)/'\1'/"));")
  for DB in $DB_LIST; do
    log "Listing database: $DB"
    # DB_PASSWORD=$PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -c "DROP DATABASE \"$DB\""
  done
  log "$STEP: done"
  echo ""
}

main "$@"
