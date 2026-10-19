#!/usr/bin/env bash
# Generate traffic so the Grafana panels have data. Usage: ./monitoring/load_test.sh [url] [n]
URL=${1:-http://localhost:8000}
N=${2:-200}
for i in $(seq 1 "$N"); do
  AGE=$((30 + RANDOM % 45)); THAL=$((120 + RANDOM % 70)); CP=$((1 + RANDOM % 4)); EX=$((RANDOM % 2))
  curl -s -o /dev/null -X POST "$URL/predict" -H 'Content-Type: application/json' \
    -d "{\"age\":$AGE,\"sex\":1,\"cp\":$CP,\"trestbps\":130,\"chol\":240,\"fbs\":0,\"restecg\":0,\"thalach\":$THAL,\"exang\":$EX,\"oldpeak\":1.2,\"slope\":2,\"ca\":1,\"thal\":3}"
  # every 20th request is invalid, to exercise the error-rate panel
  if (( i % 20 == 0 )); then curl -s -o /dev/null -X POST "$URL/predict" -H 'Content-Type: application/json' -d '{"age":-1}'; fi
done
echo "sent $N requests to $URL"
