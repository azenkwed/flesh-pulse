#!/usr/bin/env python3
"""Check if PostgreSQL is ready and accepting connections."""
import asyncio
import sys
from urllib.parse import urlparse

try:
    import asyncpg
except ImportError:
    print("[!] asyncpg not installed. Install with: pip install asyncpg")
    sys.exit(1)


async def check_postgres_ready(database_url: str, timeout: float = 2.0) -> bool:
    """Check if PostgreSQL is ready by attempting to connect."""
    try:
        # Parse the database URL
        parsed = urlparse(database_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 5432
        user = parsed.username or "postgres"
        password = parsed.password or "postgres"
        database = parsed.path.lstrip("/") or "postgres"

        # Try to connect
        conn = await asyncio.wait_for(
            asyncpg.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database,
                timeout=timeout,
            ),
            timeout=timeout,
        )
        await conn.close()
        return True
    except Exception:
        return False


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("[!] Usage: check_postgres.py <DATABASE_URL>")
        sys.exit(1)

    database_url = sys.argv[1]
    timeout = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0

    try:
        result = asyncio.run(check_postgres_ready(database_url, timeout))
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        sys.exit(1)
    except Exception as e:
        print(f"[!] Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
