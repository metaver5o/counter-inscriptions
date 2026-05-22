.PHONY: default up down clean reset bootstrap bootstrap-force

# Default target runs the existing stack straight without wiping your data
default: up

up:
	@echo "🚀 Launching build configuration..."
	docker compose up --build

# Standalone container destruction
down:
	@echo "🛑 Bringing down the stack..."
	docker compose down

# Use this manually ONLY if you actually want to clear the databases out again
clean:
	@echo "🧹 Cleaning out data folders manually..."
	rm -f data/counterparty/counterparty.db*
	rm -f data/counterparty/state.db*

# Stop everything, wipe data fragments, and build fresh
reset: down clean up

# Bootstrap from compressed snapshots (skips if DB files exist)
bootstrap:
	@echo "📦 Bootstrapping from snapshots..."
	docker compose --profile bootstrap run --rm counterparty-bootstrap

# Force bootstrap by wiping existing DBs first
bootstrap-force: clean bootstrap