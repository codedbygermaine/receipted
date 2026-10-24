#!/usr/bin/env bash
# Build the image, push it to ECR, create or update the Lambda function, and expose it through API Gateway.
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

echo "== s3 bucket for job inputs and results =="
BUCKET="$NAME-jobs-$ACCOUNT"
aws s3api head-bucket --bucket "$BUCKET" 2>/dev/null || \
  aws s3api create-bucket --bucket "$BUCKET" --region "$REGION" --create-bucket-configuration LocationConstraint="$REGION" >/dev/null
aws s3api put-public-access-block --bucket "$BUCKET" --public-access-block-configuration \
  BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
aws s3api put-bucket-lifecycle-configuration --bucket "$BUCKET" --lifecycle-configuration \
  '{"Rules":[{"ID":"expire-jobs","Status":"Enabled","Filter":{"Prefix":"jobs/"},"Expiration":{"Days":7}}]}'
aws iam put-role-policy --role-name "$ROLE_NAME" --policy-name "$NAME-jobs" --policy-document "{
  \"Version\":\"2012-10-17\",\"Statement\":[
   {\"Effect\":\"Allow\",\"Action\":[\"s3:GetObject\",\"s3:PutObject\"],\"Resource\":\"arn:aws:s3:::$BUCKET/jobs/*\"},
   {\"Effect\":\"Allow\",\"Action\":\"lambda:InvokeFunction\",\"Resource\":\"arn:aws:lambda:$REGION:$ACCOUNT:function:$NAME\"}]}"

ENV="Variables={ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY,RECEIPTED_API_TOKEN=$RECEIPTED_API_TOKEN,RECEIPTED_DATA_DIR=/tmp/receipted,RECEIPTED_CHROMA_EPHEMERAL=1,RECEIPTED_BAKED_HOME=/var/task/home,RECEIPTED_ASYNC=1,RECEIPTED_BUCKET=$BUCKET}"
if aws lambda get-function --function-name "$NAME" --region "$REGION" >/dev/null 2>&1; then
  aws lambda update-function-code --function-name "$NAME" --image-uri "$REPO:latest" --region "$REGION" >/dev/null
  aws lambda wait function-updated --function-name "$NAME" --region "$REGION"
  aws lambda update-function-configuration --function-name "$NAME" --region "$REGION" --environment "$ENV" --timeout 120 --memory-size 2048 >/dev/null
else
  aws lambda create-function --function-name "$NAME" --package-type Image --code ImageUri="$REPO:latest" \
    --role "$ROLE_ARN" --architectures "$ARCH" --timeout 120 --memory-size 2048 --region "$REGION" --environment "$ENV" >/dev/null
  aws lambda wait function-active --function-name "$NAME" --region "$REGION"
fi
# Public endpoint through API Gateway (HTTP API, payload format 2.0). New AWS accounts block public Lambda
# function URLs, and a gateway is the conventional front door anyway.
API_ID=$(aws apigatewayv2 get-apis --region "$REGION" --query "Items[?Name=='$NAME'].ApiId | [0]" --output text)
if [ "$API_ID" = "None" ] || [ -z "$API_ID" ]; then
  FN_ARN=$(aws lambda get-function --function-name "$NAME" --region "$REGION" --query Configuration.FunctionArn --output text)
  API_ID=$(aws apigatewayv2 create-api --name "$NAME" --protocol-type HTTP --target "$FN_ARN" --region "$REGION" --query ApiId --output text)
fi
aws lambda add-permission --function-name "$NAME" --region "$REGION" --statement-id apigw-invoke --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com --source-arn "arn:aws:execute-api:$REGION:$ACCOUNT:$API_ID/*" >/dev/null 2>&1 || true
URL="https://$API_ID.execute-api.$REGION.amazonaws.com"
echo "deployed: $URL"
echo "try: curl $URL/health   (POST /check returns 202 + job id; poll GET /jobs/<id>)"
