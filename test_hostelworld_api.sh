#!/bin/bash

# Test Hostelworld via API

echo "=== Step 1: Login ==="
LOGIN_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}')

echo "$LOGIN_RESPONSE"

TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
  echo "ERROR: Failed to get token"
  exit 1
fi

echo ""
echo "=== Step 2: Create Hostelworld Job ==="
JOB_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/jobs/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "location": "Kathmandu",
    "category_id": 1,
    "max_results": 25,
    "source_ids": [11]
  }')

echo "$JOB_RESPONSE"

JOB_ID=$(echo "$JOB_RESPONSE" | grep -o '"id":"[^"]*' | cut -d'"' -f4)

echo ""
echo "=== Job Created ==="
echo "Job ID: $JOB_ID"
echo "Monitor at: http://localhost:5173/jobs/$JOB_ID"
