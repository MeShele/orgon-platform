#!/usr/bin/env python3
"""
Automatically fix circular imports in all routes files.
Replaces imports from backend.main with imports from backend.services and adds dependency injection.
"""

import re
from pathlib import Path

# Mapping of getter functions to their services
SERVICE_MAPPING = {
    'get_audit_service': ('AuditService', 'audit_service'),
    'get_auth_service': ('AuthService', 'auth_service'),
    'get_dashboard_service': ('DashboardService', 'dashboard_service'),
    'get_wallet_service': ('WalletService', 'wallet_service'),
    'get_transaction_service': ('TransactionService', 'transaction_service'),
    'get_network_service': ('NetworkService', 'network_service'),
    'get_signature_service': ('SignatureService', 'signature_service'),
    'get_user_service': ('UserService', 'user_service'),
    'get_balance_service': ('BalanceService', 'balance_service'),
    'get_sync_service': ('SyncService', 'sync_service'),
}

def snake_to_pascal(snake_str):
    """Convert snake_case to PascalCase."""
    return ''.join(word.capitalize() for word in snake_str.split('_'))

def fix_file(file_path):
    """Fix circular imports in a single file."""
    print(f"Processing {file_path}...")
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Find what services this file imports
    import_pattern = r'from backend\.main import (.+)'
    match = re.search(import_pattern, content)
    
    if not match:
        print(f"  No imports from backend.main found, skipping.")
        return
    
    imported_items = [item.strip() for item in match.group(1).split(',')]
    
    # Build new imports and dependency injection helpers
    service_imports = []
    dependency_helpers = []
    
    for item in imported_items:
        if item in SERVICE_MAPPING:
            service_class, attr_name = SERVICE_MAPPING[item]
            service_imports.append(f"from backend.services.{attr_name} import {service_class}")
            
            # Create dependency injection helper
            helper = f"""
async def {item}(request: Request) -> {service_class}:
    \"\"\"Get {service_class} from app state.\"\"\"
    return request.app.state.{attr_name}
"""
            dependency_helpers.append(helper.strip())
    
    # Remove old import
    content = re.sub(import_pattern, '', content)
    
    # Add Request and Depends to fastapi imports if not already there
    if 'from fastapi import' in content:
        # Find the fastapi import line
        fastapi_import_pattern = r'from fastapi import ([^\\n]+)'
        fastapi_match = re.search(fastapi_import_pattern, content)
        if fastapi_match:
            imports = fastapi_match.group(1)
            imports_list = [i.strip() for i in imports.split(',')]
            if 'Request' not in imports_list:
                imports_list.append('Request')
            if 'Depends' not in imports_list:
                imports_list.append('Depends')
            new_imports = ', '.join(imports_list)
            content = re.sub(fastapi_import_pattern, f'from fastapi import {new_imports}', content)
    
    # Add service imports after other imports
    if service_imports:
        # Find the last import statement
        import_section_end = 0
        for match in re.finditer(r'^(from |import )', content, re.MULTILINE):
            import_section_end = match.end()
        
        # Find the end of that line
        newline_pos = content.find('\\n', import_section_end)
        if newline_pos != -1:
            insert_pos = newline_pos + 1
            content = content[:insert_pos] + '\\n' + '\\n'.join(service_imports) + '\\n' + content[insert_pos:]
    
    # Add dependency injection helpers after router definition
    router_pattern = r'(router = APIRouter\([^)]*\))'
    if dependency_helpers and re.search(router_pattern, content):
        helpers_text = '\\n\\n# Dependency injection\\n' + '\\n\\n'.join(dependency_helpers)
        content = re.sub(router_pattern, r'\\1' + helpers_text, content)
    
    # Remove all occurrences of "service = get_*_service()"
    content = re.sub(r'^\\s*service = (get_\\w+_service)\\(\\)\\s*$', '', content, flags=re.MULTILINE)
    
    # Write back
    with open(file_path, 'w') as f:
        f.write(content)
    
    print(f"  ✅ Fixed {file_path}")

def main():
    # Find all routes files with imports from backend.main
    routes_dir = Path('/Users/urmatmyrzabekov/AGENT/ORGON/backend/api')
    
    for file_path in routes_dir.glob('routes_*.py'):
        fix_file(file_path)
    
    print("\\n✅ All circular imports fixed!")
    print("⚠️  Note: You still need to add `service: ServiceClass = Depends(get_service)` to route functions manually.")

if __name__ == "__main__":
    main()
