#!/bin/bash
cd /root/ORGON
git pull origin main
docker-compose down
docker-compose build --no-cache
docker-compose up -d
echo "Deployed at $(date)"
echo "Backend: http://localhost:8890"
echo "Frontend: http://localhost:3000"
echo "Public: https://orgon.asystem.ai"
