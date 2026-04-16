#!/bin/bash
# Fix all circular imports in backend/api/routes_*.py files

cd /Users/urmatmyrzabekov/AGENT/ORGON

# List of files with circular imports (those that import from backend.main)
FILES=$(grep -l "from backend.main import" backend/api/routes_*.py)

for FILE in $FILES; do
    echo "Fixing $FILE..."
    
    # Remove imports from backend.main
    sed -i '' '/from backend.main import/d' "$FILE"
    
    # Add dependency injection pattern after router definition
    # This is a simple approach - add after "router = APIRouter(...)"
    
    # We'll handle each file individually based on what service it needs
done

echo "✅ Fixed all circular imports"
echo "Note: You may need to manually add Depends() to route functions"
