#!/bin/bash
# Test script to verify Python imports work correctly

set -e

cd apps/seed-planter-api/src

echo "🧪 Testing Python imports..."

# Test each module can be imported
python3 -c "import config; print('✅ config imported')"
python3 -c "import database; print('✅ database imported')"
python3 -c "import db_models; print('✅ db_models imported')"
python3 -c "import auth; print('✅ auth imported')"
python3 -c "import auth_models; print('✅ auth_models imported')"
python3 -c "import usage_metering; print('✅ usage_metering imported')"
python3 -c "import billing_service; print('✅ billing_service imported')"
python3 -c "import auth_routes; print('✅ auth_routes imported')"
python3 -c "import billing_routes; print('✅ billing_routes imported')"

echo ""
echo "✅ All imports successful!"
