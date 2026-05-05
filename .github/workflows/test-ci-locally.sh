#!/bin/bash
# Test CI/CD pipeline locally before pushing
# This script simulates the CI pipeline steps

set -e  # Exit on error

echo "🧪 Testing CI/CD Pipeline Locally"
echo "=================================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Backend Tests
echo -e "\n${YELLOW}[1/5] Running Backend Tests...${NC}"
docker-compose run --rm \
  -e TEST_DATABASE_URL=postgresql://scraper:scraper_pass@postgres:5432/scraper_test_db \
  -e MOCK_MODE=true \
  backend pytest tests/ -v --cov=. --cov-report=term

if [ $? -eq 0 ]; then
  echo -e "${GREEN}✓ Backend tests passed${NC}"
else
  echo -e "${RED}✗ Backend tests failed${NC}"
  exit 1
fi

# Test 2: Backend Coverage Check
echo -e "\n${YELLOW}[2/5] Checking Backend Coverage (≥85%)...${NC}"
docker-compose run --rm backend coverage report --fail-under=85

if [ $? -eq 0 ]; then
  echo -e "${GREEN}✓ Backend coverage meets threshold${NC}"
else
  echo -e "${RED}✗ Backend coverage below 85%${NC}"
  exit 1
fi

# Test 3: Frontend Linting
echo -e "\n${YELLOW}[3/5] Running Frontend Linting...${NC}"
cd frontend
npm run lint

if [ $? -eq 0 ]; then
  echo -e "${GREEN}✓ Frontend linting passed${NC}"
else
  echo -e "${RED}✗ Frontend linting failed${NC}"
  exit 1
fi

# Test 4: Frontend Tests
echo -e "\n${YELLOW}[4/5] Running Frontend Tests...${NC}"
npm test -- --run --coverage

if [ $? -eq 0 ]; then
  echo -e "${GREEN}✓ Frontend tests passed${NC}"
else
  echo -e "${RED}✗ Frontend tests failed${NC}"
  exit 1
fi

# Test 5: Docker Build Test
echo -e "\n${YELLOW}[5/5] Testing Docker Builds...${NC}"
cd ..

echo "Building backend image..."
docker build -t gen-scraper-backend-test ./backend

if [ $? -eq 0 ]; then
  echo -e "${GREEN}✓ Backend Docker build successful${NC}"
else
  echo -e "${RED}✗ Backend Docker build failed${NC}"
  exit 1
fi

echo "Building frontend image..."
docker build -t gen-scraper-frontend-test ./frontend

if [ $? -eq 0 ]; then
  echo -e "${GREEN}✓ Frontend Docker build successful${NC}"
else
  echo -e "${RED}✗ Frontend Docker build failed${NC}"
  exit 1
fi

# Cleanup test images
echo -e "\n${YELLOW}Cleaning up test images...${NC}"
docker rmi gen-scraper-backend-test gen-scraper-frontend-test

# Success
echo -e "\n${GREEN}=================================="
echo -e "✓ All CI checks passed!"
echo -e "==================================${NC}"
echo -e "\nYou can safely push your changes."
echo -e "The GitHub Actions pipeline should pass."
