# Alembic Migrations

## Overview

This folder contains the migration scripts for the trust registry database.
These scripts are used to manage changes to the database schema in a consistent and version-controlled manner.

### Files and Directories

- `env.py`: This is the configuration file for Alembic, the database migration tool.
   It sets up the database connection and other settings required for migrations.
- `script.py.mako`: This is a template file used by Alembic to generate new migration scripts.
   It contains placeholders for the migration logic.
- `versions/`: This directory contains the individual migration scripts.
   Each script is named with a unique identifier and describes a specific change to the database schema.
