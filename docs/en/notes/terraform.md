# Terraform

## Core workflow

```bash
terraform init                      # download providers/modules, configure backend
terraform fmt -recursive            # canonical formatting
terraform validate                  # syntax + internal consistency
terraform plan -out=tfplan          # diff: what WOULD change
terraform apply tfplan              # apply exactly that plan
terraform destroy                   # tear everything down (careful)
```

Always `apply` a saved plan in CI: what was reviewed is what runs.

## Minimal example

```hcl
terraform {
  required_version = ">= 1.9"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

variable "env" { type = string }

resource "aws_s3_bucket" "logs" {
  bucket = "acme-logs-${var.env}"
  tags   = { env = var.env }
}

output "bucket_arn" { value = aws_s3_bucket.logs.arn }
```

```bash
terraform plan -var env=dev
terraform apply -var-file=prod.tfvars
```

Resources reference each other (`aws_s3_bucket.logs.arn`); Terraform builds a dependency graph (DAG) from those references and creates independent resources in parallel. Use `depends_on` only for dependencies it can't see.

## State

State maps your code to real resources. It can contain secrets and must never be committed.

```hcl
terraform {
  backend "s3" {
    bucket         = "acme-tfstate"
    key            = "orders/prod.tfstate"
    region         = "eu-west-1"
    dynamodb_table = "tf-locks"     # state locking: one apply at a time
    encrypt        = true
  }
}
```

```bash
terraform state list
terraform state show aws_s3_bucket.logs
terraform state mv aws_s3_bucket.logs aws_s3_bucket.app_logs   # rename without recreate
terraform import aws_s3_bucket.logs acme-logs-dev              # adopt an existing resource
terraform force-unlock <LOCK_ID>                               # only if a run died
```

Prefer `moved {}` and `import {}` blocks in code over CLI state surgery: they are reviewable.

## Modules

```hcl
module "orders_db" {
  source  = "./modules/postgres"     # or a registry / git source with a pinned version
  env     = var.env
  size    = "db.t3.medium"
}
# module.orders_db.endpoint  <- outputs are the module's public API
```

Keep modules small, with few variables and explicit outputs. One environment = one root module + one state.

## Patterns worth knowing

```hcl
# count / for_each: several similar resources (prefer for_each, stable keys)
resource "aws_iam_user" "dev" {
  for_each = toset(["alice", "bob"])
  name     = each.key
}

# lifecycle: protect important resources
resource "aws_db_instance" "main" {
  # ...
  lifecycle { prevent_destroy = true }
}

# data source: read something Terraform doesn't manage
data "aws_vpc" "default" { default = true }
```

## Drift and safety

- **Drift** = reality changed outside Terraform. `terraform plan` (or `plan -refresh-only`) shows it; fix by re-applying, or by importing the manual change into the code.
- Read the plan for `-/+` (destroy and recreate): it often means data loss on stateful resources.
- Never put secrets in `.tfvars` committed to Git: use a secret manager, `TF_VAR_*` from CI secrets, or `sensitive = true` (which hides output but does **not** encrypt state).
- Run `plan` on every pull request and post it as a comment; `apply` only after merge.
- Pin provider and module versions; commit `.terraform.lock.hcl`.

## Quick reference

| Need | Command / block |
|---|---|
| Preview changes | `terraform plan` |
| Target one resource (debug only) | `terraform plan -target=aws_s3_bucket.logs` |
| Show outputs | `terraform output` |
| Re-create one resource | `terraform apply -replace=aws_instance.web` |
| Workspaces (same code, several states) | `terraform workspace new staging` |
| Static checks | `tflint`, `checkov` / `trivy config .` |
