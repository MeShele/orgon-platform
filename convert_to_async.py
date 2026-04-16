#!/usr/bin/env python3
"""
Auto-convert ORGON services to async PostgreSQL.
Handles: imports, type hints, db calls, SQL placeholders.
"""

import re
from pathlib import Path
from typing import List, Tuple

SERVICES_DIR = Path("backend/services")
BACKUP_DIR = SERVICES_DIR / ".backup_sqlite"


def convert_sql_placeholders(content: str) -> str:
    """Convert SQLite ? placeholders to PostgreSQL $1, $2, ..."""
    
    def replace_in_sql_string(match):
        sql_string = match.group(0)
        quote_char = sql_string[0]  # ' or "
        
        # Count ? placeholders
        counter = 0
        def increment_counter(m):
            nonlocal counter
            counter += 1
            return f'${counter}'
        
        # Replace ? with $n
        result = re.sub(r'\?', increment_counter, sql_string)
        return result
    
    # Find SQL strings (triple quotes, single quotes, or double quotes)
    # Match multi-line strings
    patterns = [
        r'"""[^"]*"""',  # Triple double quotes
        r"'''[^']*'''",  # Triple single quotes
        r'"[^"]*"',      # Double quotes
        r"'[^']*'",      # Single quotes
    ]
    
    for pattern in patterns:
        content = re.sub(pattern, replace_in_sql_string, content, flags=re.DOTALL)
    
    return content


def convert_insert_or_replace(content: str) -> str:
    """Convert SQLite INSERT OR REPLACE to PostgreSQL UPSERT."""
    
    # Pattern: INSERT OR REPLACE INTO table_name (cols) VALUES (...)
    # Replace with: INSERT INTO table_name (cols) VALUES (...) ON CONFLICT DO UPDATE
    
    # This is complex, keeping simple version for now
    content = content.replace(
        "INSERT OR REPLACE INTO",
        "INSERT INTO"
    )
    
    # Add comment for manual review
    if "INSERT INTO" in content and "ON CONFLICT" not in content:
        content = "# TODO: Add ON CONFLICT clauses to INSERT statements\n" + content
    
    return content


def convert_service_to_async(service_path: Path) -> Tuple[bool, List[str]]:
    """Convert one service file to async PostgreSQL."""
    
    if not service_path.exists():
        return False, [f"File not found: {service_path}"]
    
    content = service_path.read_text()
    original = content
    warnings = []
    
    # 1. Import changes
    content = content.replace(
        "from backend.database.db import Database",
        "from backend.database.db_postgres import AsyncDatabase"
    )
    
    # 2. Type hints
    content = re.sub(
        r'\bdb: Database\b',
        'db: AsyncDatabase',
        content
    )
    
    # 3. Database method calls - add await
    # fetchall → fetch
    content = re.sub(
        r'(\s+)self\._db\.fetchall\(',
        r'\1await self._db.fetch(',
        content
    )
    
    # fetchone → fetchrow
    content = re.sub(
        r'(\s+)self\._db\.fetchone\(',
        r'\1await self._db.fetchrow(',
        content
    )
    
    # execute
    content = re.sub(
        r'(\s+)self\._db\.execute\(',
        r'\1await self._db.execute(',
        content
    )
    
    # executemany
    content = re.sub(
        r'(\s+)self\._db\.executemany\(',
        r'\1await self._db.executemany(',
        content
    )
    
    # 4. Convert SQL placeholders
    content = convert_sql_placeholders(content)
    
    # 5. Convert INSERT OR REPLACE
    if "INSERT OR REPLACE" in content:
        warnings.append("⚠️  Contains INSERT OR REPLACE - needs ON CONFLICT")
        content = convert_insert_or_replace(content)
    
    # 6. Check for non-async methods with await
    # Find methods with 'await self._db' but no 'async def'
    lines = content.split('\n')
    in_method = False
    method_is_async = False
    method_name = None
    
    for i, line in enumerate(lines):
        # Check for method definition
        if re.match(r'\s+def\s+\w+\(', line):
            in_method = True
            method_is_async = 'async def' in line
            match = re.search(r'def\s+(\w+)\(', line)
            method_name = match.group(1) if match else 'unknown'
        
        # Check for await in non-async method
        if in_method and not method_is_async and 'await self._db' in line:
            warnings.append(f"⚠️  Line {i+1}: Method '{method_name}' needs 'async' keyword")
            # Fix it
            lines[i-1] = lines[i-1].replace('def ', 'async def ', 1)
    
    content = '\n'.join(lines)
    
    # Check if anything changed
    if content == original:
        return False, ["No changes needed"]
    
    # Backup original
    BACKUP_DIR.mkdir(exist_ok=True)
    backup_path = BACKUP_DIR / service_path.name
    backup_path.write_text(original)
    
    # Write converted content
    service_path.write_text(content)
    
    return True, warnings


def main():
    print("🚀 ORGON Services → Async PostgreSQL Migration\n")
    
    services = list(SERVICES_DIR.glob("*_service.py"))
    print(f"📦 Found {len(services)} services\n")
    
    results = []
    for service in services:
        print(f"🔄 Converting {service.name}...")
        
        converted, warnings = convert_service_to_async(service)
        
        if converted:
            print(f"   ✅ Converted")
            if warnings:
                for warning in warnings:
                    print(f"      {warning}")
            results.append((service.name, True, warnings))
        else:
            print(f"   ⏭️  {warnings[0] if warnings else 'Skipped'}")
            results.append((service.name, False, warnings))
        print()
    
    print("\n" + "="*60)
    print("✅ Conversion complete!")
    print(f"📁 Backups saved to: {BACKUP_DIR}")
    print("\n📋 Summary:")
    
    converted_count = sum(1 for _, converted, _ in results if converted)
    print(f"   Converted: {converted_count}/{len(results)}")
    
    # Show files with warnings
    files_with_warnings = [(name, warns) for name, conv, warns in results if conv and warns]
    if files_with_warnings:
        print("\n⚠️  Manual review needed:")
        for name, warns in files_with_warnings:
            print(f"   • {name}")
            for warn in warns:
                print(f"     {warn}")
    
    print("\n✅ Next steps:")
    print("   1. Review converted files")
    print("   2. Test: python -m pytest backend/tests/")
    print("   3. Deploy: ./restart-all.sh")


if __name__ == "__main__":
    main()
