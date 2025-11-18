#!/usr/bin/env python3
"""
PostgreSQL Setup Verification Script

Verifies that PostgreSQL is properly configured and ready for migration.
"""

import sys
import os
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def check_docker():
    """Check if Docker is running"""
    print("1. Checking Docker...")

    import subprocess

    try:
        result = subprocess.run(['docker', '--version'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"   [OK] {result.stdout.strip()}")
            return True
        else:
            print("   [ERROR] Docker not found")
            return False
    except FileNotFoundError:
        print("   [ERROR] Docker not installed or not in PATH")
        return False
    except subprocess.TimeoutExpired:
        print("   [ERROR] Docker command timed out")
        return False


def check_docker_compose():
    """Check if docker-compose is available"""
    print("\n2. Checking Docker Compose...")

    import subprocess

    try:
        result = subprocess.run(['docker-compose', '--version'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"   [OK] {result.stdout.strip()}")
            return True
        else:
            print("   [ERROR] docker-compose not found")
            return False
    except FileNotFoundError:
        print("   [ERROR] docker-compose not installed")
        return False


def check_containers():
    """Check if PostgreSQL containers are running"""
    print("\n3. Checking PostgreSQL containers...")

    import subprocess

    try:
        result = subprocess.run(
            ['docker-compose', 'ps'],
            capture_output=True,
            text=True,
            timeout=10
        )

        if 'gex_postgres' in result.stdout:
            if 'Up' in result.stdout or 'running' in result.stdout.lower():
                print("   [OK] PostgreSQL container is running")
                postgres_running = True
            else:
                print("   [WARNING] PostgreSQL container exists but not running")
                print("   Run: docker-compose up -d")
                postgres_running = False
        else:
            print("   [WARNING] PostgreSQL container not found")
            print("   Run: docker-compose up -d")
            postgres_running = False

        if 'gex_pgadmin' in result.stdout:
            print("   [OK] pgAdmin container found")
        else:
            print("   [WARNING] pgAdmin container not found")

        return postgres_running

    except Exception as e:
        print(f"   [ERROR] {e}")
        return False


def check_postgres_connection():
    """Check if can connect to PostgreSQL"""
    print("\n4. Testing PostgreSQL connection...")

    try:
        from src.config import Config
        from src.database import DatabaseConnection

        load_dotenv()
        config = Config()

        try:
            db = DatabaseConnection(
                db_type='postgresql',
                host=config.postgres_host,
                port=config.postgres_port,
                database=config.postgres_db,
                user=config.postgres_user,
                password=config.postgres_password
            )

            # Test query
            result = db.read_sql('SELECT version()')
            print(f"   [OK] Connected to PostgreSQL")
            print(f"   Version: {result['version'].iloc[0][:50]}...")

            db.close()
            return True

        except Exception as e:
            print(f"   [ERROR] Connection failed: {e}")
            print("   Check your .env file has correct PostgreSQL credentials")
            return False

    except ImportError as e:
        print(f"   [ERROR] Missing dependencies: {e}")
        print("   Run: pip install -r requirements.txt")
        return False


def check_table_exists():
    """Check if gex_table exists in PostgreSQL"""
    print("\n5. Checking database schema...")

    try:
        from src.config import Config
        from src.database import DatabaseConnection

        load_dotenv()
        config = Config()

        db = DatabaseConnection(
            db_type='postgresql',
            host=config.postgres_host,
            port=config.postgres_port,
            database=config.postgres_db,
            user=config.postgres_user,
            password=config.postgres_password
        )

        if db.table_exists('gex_table'):
            print("   [OK] Table 'gex_table' exists")

            # Check row count
            count = db.get_row_count('gex_table')
            print(f"   Current rows: {count:,}")

            # Check columns
            info = db.get_table_info('gex_table')
            print(f"   Columns: {len(info)}")

            db.close()
            return True
        else:
            print("   [ERROR] Table 'gex_table' not found")
            print("   The init.sql script should have created it")
            print("   Try recreating containers: docker-compose down && docker-compose up -d")
            db.close()
            return False

    except Exception as e:
        print(f"   [ERROR] {e}")
        return False


def check_sqlite_database():
    """Check SQLite database for migration"""
    print("\n6. Checking SQLite database...")

    db_path = 'data/gex_data.db'

    if not os.path.exists(db_path):
        print(f"   [ERROR] SQLite database not found at {db_path}")
        return False

    size_gb = os.path.getsize(db_path) / (1024**3)
    print(f"   [OK] Found SQLite database ({size_gb:.2f} GB)")

    try:
        from src.database import DatabaseConnection

        db = DatabaseConnection(db_type='sqlite', db_path=db_path)
        count = db.get_row_count('gex_table')
        print(f"   Records to migrate: {count:,}")

        max_ts = db.get_max_timestamp()
        if max_ts:
            print(f"   Latest timestamp: {max_ts}")

        db.close()
        return True

    except Exception as e:
        print(f"   [ERROR] {e}")
        return False


def check_environment():
    """Check environment configuration"""
    print("\n7. Checking environment configuration...")

    load_dotenv()

    required_vars = [
        'POSTGRES_HOST',
        'POSTGRES_PORT',
        'POSTGRES_DB',
        'POSTGRES_USER',
        'POSTGRES_PASSWORD',
    ]

    all_set = True

    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Mask password
            if 'PASSWORD' in var:
                display_value = '*' * len(value)
            else:
                display_value = value
            print(f"   [OK] {var}={display_value}")
        else:
            print(f"   [ERROR] {var} not set")
            all_set = False

    if not all_set:
        print("\n   Add missing variables to your .env file")
        print("   See .env.postgres.example for template")

    return all_set


def main():
    """Run all verification checks"""
    print("=" * 80)
    print("PostgreSQL Setup Verification")
    print("=" * 80)

    checks = [
        ("Docker", check_docker),
        ("Docker Compose", check_docker_compose),
        ("Environment Variables", check_environment),
        ("Containers Running", check_containers),
        ("PostgreSQL Connection", check_postgres_connection),
        ("Database Schema", check_table_exists),
        ("SQLite Database", check_sqlite_database),
    ]

    results = []

    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"\n   [ERROR] {e}")
            results.append((check_name, False))

    # Summary
    print("\n" + "=" * 80)
    print("VERIFICATION SUMMARY")
    print("=" * 80)

    all_passed = True
    for check_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {check_name}")
        if not result:
            all_passed = False

    print("\n" + "=" * 80)

    if all_passed:
        print("[SUCCESS] All checks passed!")
        print("\nReady to migrate. Run:")
        print("  python scripts/migrate_to_postgres.py")
    else:
        print("[WARNING] Some checks failed")
        print("\nFix the issues above before migrating")
        print("\nCommon fixes:")
        print("- Install Docker Desktop and restart computer")
        print("- Run: docker-compose up -d")
        print("- Run: pip install -r requirements.txt")
        print("- Copy .env.postgres.example to .env and update credentials")

    print("=" * 80)

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
