#!/usr/bin/env bash
# exit on error
set -o errexit

# --- Build Frontend ---
echo "Building Frontend..."
cd frontend
npm install
npm run build
cd ..

# Ensure backend/static exists
mkdir -p backend/static

# Move built files to backend/static
# Angular 17+ outputs to dist/frontend/browser
if [ -d "frontend/dist/frontend/browser" ]; then
    cp -r frontend/dist/frontend/browser/* backend/static/
elif [ -d "frontend/dist/frontend" ]; then
    cp -r frontend/dist/frontend/* backend/static/
fi

# --- Build Backend ---
echo "Building Backend..."
cd backend
pip install -r requirements.txt
cd ..

echo "Build Complete!"
