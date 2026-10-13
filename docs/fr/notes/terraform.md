# Terraform

## Workflow de base

```bash
terraform init                      # télécharge providers/modules, configure le backend
terraform fmt -recursive            # formatage canonique
terraform validate                  # syntaxe + cohérence interne
terraform plan -out=tfplan          # diff : ce qui CHANGERAIT
terraform apply tfplan              # applique exactement ce plan
terraform destroy                   # détruit tout (attention)
```

En CI, appliquez toujours un plan sauvegardé : ce qui a été relu est ce qui s'exécute.

## Exemple minimal

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

Les ressources se référencent entre elles (`aws_s3_bucket.logs.arn`) ; Terraform construit un graphe de dépendances (DAG) à partir de ces références et crée les ressources indépendantes en parallèle. N'utilisez `depends_on` que pour les dépendances qu'il ne voit pas.

## State

Le state associe votre code aux ressources réelles. Il peut contenir des secrets et ne doit jamais être commité.

```hcl
terraform {
  backend "s3" {
    bucket         = "acme-tfstate"
    key            = "orders/prod.tfstate"
    region         = "eu-west-1"
    dynamodb_table = "tf-locks"     # verrou du state : un seul apply à la fois
    encrypt        = true
  }
}
```

```bash
terraform state list
terraform state show aws_s3_bucket.logs
terraform state mv aws_s3_bucket.logs aws_s3_bucket.app_logs   # renommer sans recréer
terraform import aws_s3_bucket.logs acme-logs-dev              # adopter une ressource existante
terraform force-unlock <LOCK_ID>                               # seulement si un run est mort
```

Préférez les blocs `moved {}` et `import {}` dans le code à la chirurgie du state en CLI : ils sont relisables.

## Modules

```hcl
module "orders_db" {
  source  = "./modules/postgres"     # ou un registry / git avec version épinglée
  env     = var.env
  size    = "db.t3.medium"
}
# module.orders_db.endpoint  <- les outputs sont l'API publique du module
```

Gardez des modules petits, avec peu de variables et des outputs explicites. Un environnement = un root module + un state.

## Patterns à connaître

```hcl
# count / for_each : plusieurs ressources similaires (préférez for_each, clés stables)
resource "aws_iam_user" "dev" {
  for_each = toset(["alice", "bob"])
  name     = each.key
}

# lifecycle : protéger les ressources importantes
resource "aws_db_instance" "main" {
  # ...
  lifecycle { prevent_destroy = true }
}

# data source : lire ce que Terraform ne gère pas
data "aws_vpc" "default" { default = true }
```

## Drift et sécurité

- **Drift** = la réalité a changé en dehors de Terraform. `terraform plan` (ou `plan -refresh-only`) le montre ; corrigez en ré-appliquant, ou en important le changement manuel dans le code.
- Cherchez `-/+` dans le plan (détruire puis recréer) : cela signifie souvent une perte de données sur les ressources à état.
- Ne mettez jamais de secrets dans des `.tfvars` commités : utilisez un gestionnaire de secrets, des `TF_VAR_*` issus des secrets CI, ou `sensitive = true` (qui masque l'affichage mais ne chiffre **pas** le state).
- Lancez `plan` sur chaque pull request et publiez-le en commentaire ; `apply` seulement après le merge.
- Épinglez les versions de providers et modules ; commitez `.terraform.lock.hcl`.

## Référence rapide

| Besoin | Commande / bloc |
|---|---|
| Prévisualiser les changements | `terraform plan` |
| Cibler une ressource (debug seulement) | `terraform plan -target=aws_s3_bucket.logs` |
| Afficher les outputs | `terraform output` |
| Recréer une ressource | `terraform apply -replace=aws_instance.web` |
| Workspaces (même code, plusieurs states) | `terraform workspace new staging` |
| Analyses statiques | `tflint`, `checkov` / `trivy config .` |
