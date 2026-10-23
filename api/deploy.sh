#!/usr/bin/env bash
# Build the image, push it to ECR, and create or update the Lambda function with a public URL.
# Needs: aws CLI signed in (aws sts get-caller-identity works), docker running, and these env vars:
#   RECEIPTED_API_TOKEN   token callers must send in X-Api-Token
#   ANTHROPIC_API_KEY     the Claude API key (set in the Lambda's environment; never printed)
set -euo pipefail
REGION="${AWS_REGION:-ap-southeast-1}"          # Singapore
NAME="receipted-api"
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
REPO="$ACCOUNT.dkr.ecr.$REGION.amazonaws.com/$NAME"
ARCH="${ARCH:-arm64}"                            # Graviton: cheaper, and native on Apple Silicon
: "${RECEIPTED_API_TOKEN:?set RECEIPTED_API_TOKEN}"; : "${ANTHROPIC_API_KEY:?set ANTHROPIC_API_KEY}"

echo "== build =="
docker build --platform "linux/$ARCH" -f api/Dockerfile -t "$NAME" .

echo "== push to ECR =="
aws ecr describe-repositories --repository-names "$NAME" --region "$REGION" >/dev/null 2>&1 || \
  aws ecr create-repository --repository-name "$NAME" --region "$REGION" >/dev/null
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$ACCOUNT.dkr.ecr.$REGION.amazonaws.com"
docker tag "$NAME:latest" "$REPO:latest" && docker push "$REPO:latest" | tail -1

echo "== lambda =="
ROLE_NAME="$NAME-role"
if ! aws iam get-role --role-name "$ROLE_NAME" >/dev/null 2>&1; then
  aws iam create-role --role-name "$ROLE_NAME" --assume-role-policy-document \
    '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}' >/dev/null
  aws iam attach-role-policy --role-name "$ROLE_NAME" --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
  sleep 10   # IAM propagation
fi
ROLE_ARN=$(aws iam get-role --role-name "$ROLE_NAME" --query Role.Arn --output text)
ENV="Variables={ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY,RECEIPTED_API_TOKEN=$RECEIPTED_API_TOKEN,RECEIPTED_DATA_DIR=/tmp/receipted,RECEIPTED_CHROMA_EPHEMERAL=1,HOME=/var/task/home}"
if aws lambda get-function --function-name "$NAME" --region "$REGION" >/dev/null 2>&1; then
  aws lambda update-function-code --function-name "$NAME" --image-uri "$REPO:latest" --region "$REGION" >/dev/null
  aws lambda wait function-updated --function-name "$NAME" --region "$REGION"
  aws lambda update-function-configuration --function-name "$NAME" --region "$REGION" --environment "$ENV" --timeout 120 --memory-size 2048 >/dev/null
else
  aws lambda create-function --function-name "$NAME" --package-type Image --code ImageUri="$REPO:latest" \
    --role "$ROLE_ARN" --architectures "$ARCH" --timeout 120 --memory-size 2048 --region "$REGION" --environment "$ENV" >/dev/null
  aws lambda wait function-active --function-name "$NAME" --region "$REGION"
fi
aws lambda get-function-url-config --function-name "$NAME" --region "$REGION" >/dev/null 2>&1 || \
  aws lambda create-function-url-config --function-name "$NAME" --auth-type NONE --region "$REGION" >/dev/null
aws lambda add-permission --function-name "$NAME" --region "$REGION" --statement-id public-url --action lambda:InvokeFunctionUrl \
  --principal '*' --function-url-auth-type NONE >/dev/null 2>&1 || true
URL=$(aws lambda get-function-url-config --function-name "$NAME" --region "$REGION" --query FunctionUrl --output text)
echo "deployed: $URL"
echo "try: curl ${URL}health"
