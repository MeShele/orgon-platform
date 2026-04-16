#!/usr/bin/env python3
"""
Fix circular import in routes_analytics.py by adding Depends to all route functions.
"""

import re

def fix_route_functions(file_path):
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Pattern to match route functions that DON'T have service parameter
    # Matches: @router.{method}(...)\nasync def function_name(\n    param: type = default,\n    ...
    # But NOT if "service:" already in parameters
    
    pattern = r'(@router\.\w+\([^\)]*\)\s*\nasync def \w+\([^)]*?)(\):)'
    
    def add_service_param(match):
        decorator_and_func = match.group(1)
        closing_paren = match.group(2)
        
        # Check if 'service:' already in parameters
        if 'service:' in decorator_and_func or 'service =' in decorator_and_func:
            return match.group(0)  # Already has service parameter
        
        # Check if function has any parameters
        # If last character before ')' is '(', no parameters yet
        if decorator_and_func.strip().endswith('('):
            # No parameters, add service as first param
            return f"{decorator_and_func}\n    service: AnalyticsService = Depends(get_address_book_service){closing_paren}"
        else:
            # Has parameters, add service as last param with comma
            return f"{decorator_and_func},\n    service: AnalyticsService = Depends(get_address_book_service){closing_paren}"
    
    # Apply the pattern
    fixed_content = re.sub(pattern, add_service_param, content)
    
    # Write back
    with open(file_path, 'w') as f:
        f.write(fixed_content)
    
    print(f"✅ Fixed {file_path}")

if __name__ == "__main__":
    fix_route_functions('/Users/urmatmyrzabekov/AGENT/ORGON/backend/api/routes_analytics.py')
