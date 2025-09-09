#!/bin/bash
BASE64_CONTENT=$(base64 -i images/W2-sample.png | tr -d '\n')
curl -X POST https://iljpaj6ogl.execute-api.us-east-1.amazonaws.com/prod/process-document \
  -H "Content-Type: application/json" \
  -d "{\"filename\":\"W2-sample.png\",\"contentBase64\":\"$BASE64_CONTENT\"}" | jq .