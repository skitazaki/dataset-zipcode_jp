# NOTE: Prepare the `.env` file on your own in order to define the following variables.
include .env
AWS_S3_STORAGE_BUCKET ?= skitazaki
AWS_S3_STORAGE_PREFIX ?= datasets/zipcode_jp/
AWS_S3_PACKAGE_BUCKET ?= skitazaki
AWS_S3_PACKAGE_PREFIX ?= aws-serverless/dataset-zipcode_jp/
AWS_CFN_STACK_NAME    ?= App-ZipcodeJP
AWS_IAM_ROLE_ARN      ?=
PACKAGED_TEMPLATE     ?= packaged-template.yaml

.PHONY: all
all: clean deploy

.PHONY: clean
clean:
	@rm -f $(PACKAGED_TEMPLATE)

.PHONY: test
test:
	aws cloudformation validate-template --template-body file://template.yaml

.PHONY: build
build: test $(PACKAGED_TEMPLATE)

.PHONY: dist
dist: build
	aws s3 cp $(PACKAGED_TEMPLATE) s3://$(AWS_S3_PACKAGE_BUCKET)/$(AWS_S3_PACKAGE_PREFIX)

src/datapackage.json:
	cp -p ../datapackage.json src/datapackage.json

$(PACKAGED_TEMPLATE): src/datapackage.json
	aws cloudformation package --template-file template.yaml \
		--s3-bucket $(AWS_S3_PACKAGE_BUCKET) --s3-prefix $(AWS_S3_PACKAGE_PREFIX)assets \
		--output-template-file $(PACKAGED_TEMPLATE)

.PHONY: deploy
deploy: build
	aws cloudformation deploy --template-file $(PACKAGED_TEMPLATE) \
		--stack-name $(AWS_CFN_STACK_NAME) --capabilities CAPABILITY_IAM \
		--role-arn $(AWS_IAM_ROLE_ARN) \
		--parameter-overrides StorageBucket=$(AWS_S3_STORAGE_BUCKET) StoragePrefix=$(AWS_S3_STORAGE_PREFIX)

.PHONY: delete-stack
delete-stack:
	aws cloudformation delete-stack --stack-name $(AWS_CFN_STACK_NAME)

.PHONY: describe-stack
describe-stack:
	aws cloudformation describe-stacks --stack-name $(AWS_CFN_STACK_NAME)
