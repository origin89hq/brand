default:
    @just --list --unsorted

# Refresh the shared skills once at the start of a task.
skills-sync:
    python3 .origin89/sync-engineering.py

fmt:
    pnpm format

fmt-check:
    pnpm format:check

lint:
    pnpm lint

build:
    pnpm build

test:
    pnpm verify

check:
    pnpm check
