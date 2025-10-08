#!/bin/bash

# Pull and run Evolution API container
docker run -d \
  --name evolution-api \
  -p 8080:8080 \
  -e SERVER_TYPE=http \
  -e SERVER_PORT=8080 \
  -e CORS_ORIGIN=* \
  -e CORS_METHODS=POST,GET,PUT,DELETE \
  -e CORS_CREDENTIALS=true \
  -e LOG_LEVEL=ERROR,WARN,DEBUG,INFO,LOG,VERBOSE,DARK,WEBHOOKS \
  -e LOG_COLOR=true \
  -e LOG_BAILEYS=false \
  -e DEL_INSTANCE=false \
  -e PROVIDER_ENABLED=false \
  -e DATABASE_ENABLED=false \
  -e REDIS_ENABLED=false \
  -e RABBITMQ_ENABLED=false \
  -e SQS_ENABLED=false \
  -e WEBSOCKET_ENABLED=false \
  -e WA_BUSINESS_TOKEN_WEBHOOK=evolution \
  -e WA_BUSINESS_URL=https://graph.facebook.com \
  -e WA_BUSINESS_VERSION=v20.0 \
  -e WA_BUSINESS_LANGUAGE=pt_BR \
  -e WEBHOOK_GLOBAL_URL='' \
  -e WEBHOOK_GLOBAL_ENABLED=false \
  -e CONFIG_SESSION_PHONE_CLIENT=Evolution \
  -e CONFIG_SESSION_PHONE_NAME=Chrome \
  -e QRCODE_LIMIT=30 \
  -e AUTHENTICATION_TYPE=apikey \
  -e AUTHENTICATION_API_KEY=${EVOLUTION_API_KEY:-Ev0l_API_K3y_9x7m2p8w4q5t1n6z3v8b2r7} \
  -e AUTHENTICATION_EXPOSE_IN_FETCH_INSTANCES=true \
  -e AUTHENTICATION_JWT_EXPIRIN_IN=0 \
  -e AUTHENTICATION_JWT_SECRET=L=0ZWfAERVcfeMOt=XqOuvLL1Ws=tXgixJJqJKSR32TE9VLMu5TRF=gJhj3DlX=d6L1WjE1=1F9eLa9TWcuAKc \
  -e LANGUAGE=en \
  atendai/evolution-api:latest

# Keep container running
docker logs -f evolution-api