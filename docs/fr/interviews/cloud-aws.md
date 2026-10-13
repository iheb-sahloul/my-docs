# Cloud (AWS)

La plupart des offres Java/React mentionnent « AWS, Azure ou GCP ». Ce module utilise les noms AWS, mais le raisonnement (identité, réseau, choix du compute, données managées, coûts) se transpose aux autres clouds. Kubernetes est traité dans [Full Stack & DevOps](fullstack-devops-k8s.md), et les commandes Terraform dans les [notes Terraform](../notes/terraform.md).

## 🟢 Fondamentaux

### Identité & réseau

#### Q1. Comment fonctionne AWS IAM, et comment un service Spring Boot doit-il obtenir ses identifiants ?

**Réponse :** IAM décide **qui** (un principal : utilisateur, rôle, service) peut faire **quoi** (des actions comme
`s3:GetObject`) sur **quelle ressource** (un ARN), sous quelles conditions. Les politiques sont des documents JSON
attachés à des identités ou à des ressources ; un `Deny` explicite l'emporte toujours, et tout ce qui n'est pas
autorisé est refusé. Les applications ne doivent jamais utiliser de clés d'accès longue durée : elles assument un
**rôle** et obtiennent automatiquement des identifiants temporaires, via l'instance profile EC2, le task role ECS,
**EKS Pod Identity / IRSA**, ou le rôle d'exécution Lambda. La chaîne d'identifiants par défaut du SDK AWS les récupère
sans code. Les humains se connectent via SSO (IAM Identity Center), pas via des utilisateurs IAM avec des clés
statiques.

**Exemple :**

```json
{
  "Effect": "Allow",
  "Action": ["s3:GetObject", "s3:PutObject"],
  "Resource": "arn:aws:s3:::acme-invoices-prod/*"
}
```

#### Q2. Qu'est-ce qu'un VPC, et comment s'articulent sous-réseaux publics et privés ?

**Réponse :** Un **VPC** est votre réseau privé dans une région, découpé en **sous-réseaux**, chacun dans une zone de
disponibilité (AZ). Un **sous-réseau public** a une route vers une **Internet Gateway** ; n'y placez que les load
balancers et bastions (ou rien). Les **sous-réseaux privés** hébergent les instances applicatives et les bases ; ils
sortent sur internet via une **NAT Gateway**, et atteignent les services AWS en privé via des **VPC endpoints** (moins
chers que le NAT pour le trafic S3/DynamoDB). Les **security groups** sont des pare-feux stateful sur chaque ressource ;
référencez d'autres security groups plutôt que des plages d'IP (la base n'accepte le 5432 que depuis le security group
de l'application). Répartissez chaque couche sur au moins deux AZ.

**Exemple :**

```text
Internet → ALB (sous-réseaux publics, AZ a/b)
         → tâches ECS / pods EKS (sous-réseaux privés, AZ a/b)   SG : 8080 depuis le SG de l'ALB
         → RDS Postgres Multi-AZ (sous-réseaux privés de base)   SG : 5432 depuis le SG de l'app
sortant : une NAT Gateway par AZ ; S3 via un gateway endpoint
```

### Compute & données

#### Q3. EC2, ECS, EKS ou Lambda — comment choisir où exécuter un service Java ?

**Réponse :** **Lambda** convient au travail événementiel, en pics ou à faible trafic (déclencheurs S3, consommateurs
de file, petites API) : pas de serveurs, paiement à la requête, mais avec des limites de durée (15 min) et de taille de
payload, et des cold starts JVM (à atténuer avec SnapStart, GraalVM native ou un framework plus léger). **ECS sur
Fargate** est la façon la plus simple d'exécuter des conteneurs longue durée : pas de cluster à gérer, adapté à la
plupart des services Spring Boot. **EKS** apporte Kubernetes : portable, écosystème riche (Helm, opérateurs, service
mesh), mais avec un travail de plateforme à staffer. **EC2** en direct sert aux besoins particuliers (GPU, logiciels
sous licence, charges très optimisées). Par défaut pour une petite équipe : ECS Fargate ; EKS quand l'organisation
exploite déjà une plateforme Kubernetes.

**Exemple :**

```text
API Commandes, trafic régulier, Spring Boot   -> ECS Fargate (ou EKS si la plateforme existe)
Génération de miniatures à l'upload S3        -> Lambda
Batch nocturne de 3 heures                    -> tâche planifiée ECS / AWS Batch (pas Lambda : limite de 15 min)
```

#### Q4. Quels services managés de données et de messaging un développeur full-stack doit-il connaître, et quand utiliser chacun ?

**Réponse :** **RDS / Aurora** pour les données relationnelles (Postgres), avec Multi-AZ pour la disponibilité et des
read replicas pour la montée en charge en lecture. **DynamoDB** pour l'accès clé-valeur à toute échelle quand vous
connaissez vos patterns d'accès à l'avance. **S3** pour les fichiers, les sauvegardes et les sites statiques (avec
CloudFront devant). **ElastiCache** (Redis/Valkey) pour le cache et les sessions. **SQS** pour les files point à point
(standard : at-least-once, ordre au mieux ; FIFO : ordonné par groupe, débit moindre), **SNS** pour le fan-out pub/sub
(souvent SNS → plusieurs files SQS), **EventBridge** pour router des événements entre services et SaaS, et **MSK** ou
**Amazon MQ** quand il vous faut la sémantique de Kafka ou RabbitMQ (voir [Messaging](messaging-rabbitmq-kafka.md)).

**Exemple :**

```text
OrderPlaced -> topic SNS -> SQS "billing"   -> service de facturation
                         -> SQS "shipping"  -> service d'expédition
                         -> SQS "analytics" -> Lambda -> data lake S3
chaque file a sa propre DLQ et sa politique de retry
```

#### Q5. Comment déployer une SPA React sur AWS ?

**Réponse :** Construisez les fichiers statiques et déposez-les dans un **bucket S3 privé**, servi par **CloudFront**
avec Origin Access Control (le bucket n'est pas public). Mettez en cache un an les assets hashés (`main.abc123.js`) et
`index.html` peu de temps ou pas du tout, pour qu'un déploiement prenne effet immédiatement ; invalidez `index.html` au
déploiement. Renvoyez `index.html` pour les routes côté client (réponse d'erreur ou fonction CloudFront). Utilisez ACM
pour le TLS, ajoutez les en-têtes de sécurité (CSP, HSTS) via une response-headers policy, et routez `/api/*` vers
l'ALB du backend comme second origin : navigateur et API partagent un domaine et CORS disparaît.

**Exemple :**

```text
aws s3 sync dist/ s3://acme-web-prod --delete \
  --cache-control "public,max-age=31536000,immutable" --exclude index.html
aws s3 cp dist/index.html s3://acme-web-prod/ --cache-control "no-cache"
aws cloudfront create-invalidation --distribution-id E123 --paths /index.html
```

## 🟡 Pièges seniors

### Questions

#### Q6. Comment appliquer le moindre privilège dans IAM sans bloquer toutes les équipes ?

**Réponse :** Un rôle par workload avec uniquement les actions et ressources qu'il utilise, limité par ARN et, si
utile, par conditions (tags, `aws:SourceVpce`, chiffrement obligatoire). Évitez les actions et ressources `*`, et
n'attachez jamais `AdministratorAccess` à un service. Partez d'**IAM Access Analyzer** (il peut générer une politique à
partir de l'activité CloudTrail) et de ses alertes d'accès inutilisés. Utilisez des **comptes AWS séparés** par
environnement (et par équipe dans les grandes organisations) sous **AWS Organizations**, avec des **Service Control
Policies** comme garde-fous (interdire la désactivation de CloudTrail, interdire les régions non approuvées).
Définissez les rôles dans Terraform pour qu'ils soient revus comme du code.

**Exemple :**

```text
⛔ "Action": "s3:*", "Resource": "*"
✅ "Action": ["s3:GetObject"], "Resource": "arn:aws:s3:::acme-invoices-prod/tenant/*",
   "Condition": {"StringEquals": {"aws:ResourceTag/env": "prod"}}
```

**Pourquoi c'est un piège :** le rayon d'impact d'un identifiant fuité est la politique qui lui est attachée ; `s3:*`
sur `*` transforme un bug dans un petit service en fuite de données de tous les buckets du compte.

#### Q7. Où vivent les secrets applicatifs sur AWS, et comment arrivent-ils jusqu'à l'application ?

**Réponse :** Dans **Secrets Manager** (rotation intégrée, par exemple pour les mots de passe RDS) ou **SSM Parameter
Store** en SecureString (moins cher, pour la configuration et les secrets sans rotation), chiffrés avec **KMS**. Le
rôle du workload n'a le droit de lire que ses propres secrets. Ils arrivent à l'application via les `secrets` de la task
definition ECS, l'External Secrets Operator ou le Secrets Store CSI driver de Kubernetes
([Full Stack Q38](fullstack-devops-k8s.md)), ou Spring Cloud AWS qui les lit au démarrage. Mieux encore, supprimez le
secret : l'**authentification IAM de RDS** utilise le rôle au lieu d'un mot de passe.

**Exemple :**

```json
"secrets": [
  { "name": "SPRING_DATASOURCE_PASSWORD",
    "valueFrom": "arn:aws:secretsmanager:eu-west-1:123456789012:secret:orders/db-AbCd" }
]
```

**Pourquoi c'est un piège :** des secrets dans des variables Terraform ou en variables d'environnement en clair dans la
task definition finissent dans les fichiers de state, la console et les logs de CI.

#### Q8. Qu'est-ce qui fait la facture AWS d'une application web typique, et quelles sont les surprises habituelles ?

**Réponse :** Le compute (heures d'instances et de Fargate, requests surdimensionnées), les bases managées (taille
d'instance, Multi-AZ, IOPS de stockage), et les surprises : le traitement de données de la **NAT Gateway** (tout le
trafic privé vers S3 ou ECR passant par le NAT au lieu des VPC endpoints), le **transfert de données inter-AZ et vers
internet**, l'ingestion des logs de debug dans **CloudWatch Logs**, les ressources inutilisées (anciens environnements,
volumes détachés, snapshots oubliés), et les métriques custom à forte cardinalité. Leviers : redimensionnement,
instances Graviton (ARM), Savings Plans pour la base stable, Spot pour le travail interruptible, mise à zéro des
environnements hors prod la nuit, règles de cycle de vie S3, et **tags plus budgets et alertes d'anomalie** pour que
chaque équipe voie son propre coût.

**Exemple :**

```text
Cost Explorer, principales lignes du mois :
  NAT Gateway bytes processed   4 100 $   <- pulls d'images ECR + trafic S3 via le NAT
  → ajout d'un gateway endpoint S3 + interface endpoints ECR : -3 300 $/mois
```

**Pourquoi c'est un piège :** les schémas d'architecture ne montrent pas le transfert de données, et c'est souvent la
ligne qui grossit le plus vite.

#### Q9. Que signifie « hautement disponible » sur AWS, et quelle différence entre Multi-AZ et multi-région ?

**Réponse :** Le **Multi-AZ** (au moins deux zones de disponibilité dans une région) est le minimum en production :
load balancer réparti sur les AZ, tâches ou pods répartis sur les AZ, RDS Multi-AZ avec bascule automatique (environ une
minute), et aucune dépendance mono-AZ comme une NAT Gateway unique. Il protège contre la panne d'un datacenter et coûte
peu. Le **multi-région** protège contre une panne régionale ou répond à des exigences de résidence des données, mais il
est coûteux et complexe : réplication des données (Aurora Global Database, tables globales DynamoDB), bascule DNS avec
les health checks Route 53, et les écritures dans deux régions amènent des conflits. Choisissez selon les RTO/RPO dont
le métier a vraiment besoin ([System Design Q31](system-design.md)) : souvent, des sauvegardes plus une infrastructure
as code capable de tout reconstruire dans une autre région (pilot light) suffisent.

**Exemple :**

```text
RTO 4 h, RPO 15 min   -> Multi-AZ + sauvegardes inter-régions + Terraform pour reconstruire (pilot light)
RTO 1 min, RPO ~0     -> multi-région actif-actif, tables globales, stratégie de conflits (rarement justifié)
```

**Pourquoi c'est un piège :** « on est sur AWS donc on est hautement disponible » est faux ; un déploiement mono-AZ
tombe comme n'importe quel datacenter, et beaucoup de pannes viennent d'un composant mono-AZ oublié.

## 🔴 Expert / Ouvert

### Questions

#### Q10. Comment organiser les comptes AWS et l'infrastructure as code d'une entreprise à plusieurs équipes ?

**Réponse :** Une **landing zone multi-comptes** (Control Tower ou un équivalent Terraform) : comptes de management,
de sécurité/archive des logs, de réseau partagé, et comptes de workload par environnement (puis par équipe ou domaine
avec la croissance). CloudTrail, GuardDuty et Config centralisés, SSO pour les humains avec des permission sets,
garde-fous par SCP. L'infrastructure en **Terraform** (ou CDK) avec un state distant par environnement et composant,
de petits modules maintenus par une équipe plateforme, et plan/apply depuis la CI avec des rôles fédérés en OIDC (pas
de clés statiques dans la CI). Les équipes possèdent les stacks de leurs services ; l'équipe plateforme possède la
voie balisée (VPC, cluster, pipelines, observabilité).

#### Q11. Quand le serverless est-il la bonne architecture pour une équipe Java, et quand fait-il mal ?

**Réponse :** Le serverless (API Gateway, Lambda, SQS, DynamoDB, Step Functions) est intéressant pour les charges
événementielles et en pics, les petites équipes sans capacité d'exploitation, et la glue entre services managés : on
paie à l'usage et on descend à zéro. Il fait mal avec un trafic élevé et régulier (le prix à la requête dépasse celui
des conteneurs), des traitements longs ou avec état, un usage relationnel intensif avec beaucoup de connexions
(utilisez RDS Proxy), une latence stricte où les cold starts comptent, et quand le développement et les tests locaux
sur de nombreuses fonctions ralentissent l'équipe. En Java : SnapStart ou images natives pour les cold starts, une
fonction par cas d'usage cohérent plutôt que par endpoint, et Step Functions pour les workflows au lieu de Lambdas qui
appellent des Lambdas.

## 🎯 Scénarios réels

### S1. Le service reçoit `AccessDenied` sur S3 juste après un déploiement

- **Symptômes :** Une nouvelle tâche ECS (ou un pod) loggue `software.amazon.awssdk.services.s3.model.S3Exception:
  Access Denied (Status Code: 403)` en écrivant des factures ; la version précédente fonctionnait.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Vérifiez quelle identité l'application utilise réellement (`aws sts get-caller-identity` depuis le
  conteneur, ou le log debug du SDK) ; la nouvelle task definition ou le service account peut référencer un autre rôle,
  ou aucun (repli sur le rôle du nœud). Vérifiez ensuite la politique du rôle, la **bucket policy**, la key policy KMS si
  le bucket utilise SSE-KMS, et les éventuelles SCP. CloudTrail montre l'appel refusé avec le principal et la raison.
- **Exemple :**

  ```text
  CloudTrail : PutObject  principal=arn:aws:sts::123:assumed-role/eks-node-role/...  errorCode=AccessDenied
  -> le pod utilise le rôle du nœud : serviceAccountName a disparu des values Helm
  ```

- **Résolution :** Rétablissez la bonne liaison de rôle (task role, ou annotation du service account / association Pod
  Identity), et ajoutez `kms:GenerateDataKey` si le bucket est chiffré par KMS.
- **Prévention :** Gardez le rôle et sa liaison dans le même changement Terraform/Helm, rendez les rôles de nœud
  minimaux pour qu'un repli échoue bruyamment, et ajoutez au démarrage une vérification des permissions critiques.

</details>

### S2. La facture AWS a doublé ce mois-ci et personne n'a changé l'architecture

- **Symptômes :** La finance signale une hausse de 2× ; les lignes qui grossissent sont « EC2-Other » et « Data
  Transfer ».

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Dans Cost Explorer, regroupez par type d'usage puis par tag/compte. « EC2-Other » cache souvent les
  octets de NAT Gateway, les volumes EBS et les snapshots. Consultez les VPC Flow Logs pour trouver les plus gros
  émetteurs via le NAT, et cherchez le trafic inter-AZ (un service appelant à haut volume un cache ou un broker dans une
  autre AZ).
- **Exemple :**

  ```text
  type d'usage NatGateway-Bytes : 38 To (+30 To)
  flux principal : pods du job batch -> S3 (via NAT), nouvel export nocturne
  ```

- **Résolution :** Ajoutez le gateway endpoint S3 (gratuit) et des interface endpoints pour ECR, STS et Secrets
  Manager ; rapprochez l'export de ses données ; supprimez les volumes et snapshots orphelins.
- **Prévention :** Tags d'allocation de coûts obligatoires, budgets par équipe avec détection d'anomalies, et une revue
  de coût dans la checklist de conception de tout nouveau flux de données.

</details>

### S3. Une zone de disponibilité a des problèmes, et une partie du trafic échoue

- **Symptômes :** Le taux d'erreur monte à environ 30 % pendant un incident AWS dans une AZ ; le service tourne sur deux
  AZ.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Ventilez les erreurs par AZ (métriques des targets du load balancer, logs avec la métadonnée d'AZ).
  Causes fréquentes : les tâches de l'AZ dégradée passent encore des health checks superficiels, une NAT Gateway ou un
  nœud de cache unique vit dans cette AZ, ou l'AZ restante manque de capacité pour absorber la charge.
- **Exemple :**

  ```text
  ALB : 5xx uniquement depuis les targets en eu-west-1b ; health checks verts (/health renvoie 200 sans vérifier les dépendances)
  tous les sous-réseaux privés sortent par une seule NAT Gateway en eu-west-1b
  ```

- **Résolution :** Détournez le trafic de l'AZ dégradée (zonal shift ALB / ARC), augmentez la capacité de l'AZ saine,
  et basculez les composants avec état si nécessaire.
- **Prévention :** Une NAT Gateway par AZ, une capacité planifiée pour N-1 AZ, des readiness checks pertinents, le
  zonal autoshift, et des game days réguliers simulant la perte d'une AZ.

</details>

## 🗣️ Questions posées en entretien

Questions rapportées d'entretiens réels, regroupées par sujet. Chacune a une courte réponse type : approfondissez avec les questions et scénarios détaillés ci-dessus, et dites la réponse à voix haute.

### Accès & services

#### R1. Une instance EC2 doit accéder à S3 en sécurité. Comment configurer sans stocker d'identifiants ?

**Réponse :** Attacher un **rôle IAM** (instance profile) avec une politique de moindre privilège pour le bucket/préfixe précis ; le SDK obtient des identifiants temporaires via le service de métadonnées de l'instance (utiliser IMDSv2). Restreindre en option par une bucket policy, un VPC endpoint et `aws:SourceVpce`. Aucune clé d'accès dans le code, les variables d'environnement ou les AMI.

#### R2. Différence entre EC2, ECS et Lambda.

**Réponse :** **EC2** : machines virtuelles que vous gérez (OS, scaling, patchs) : contrôle maximal. **ECS** : orchestrateur de conteneurs, sur EC2 ou en serverless via **Fargate**. **Lambda** : fonctions déclenchées par événements, mise à l'échelle automatique, facturation à l'invocation, avec limites de temps/mémoire et cold starts. Choisir selon contrôle vs exploitation vs forme de la charge.

#### R3. Comment surveiller des applications dans AWS ?

**Réponse :** **CloudWatch** métriques, logs et alarmes (plus Logs Insights, Container Insights) ; **X-Ray**/OpenTelemetry pour les traces ; CloudTrail pour l'audit des API ; health checks et SNS/PagerDuty pour l'alerte. Alerter sur les SLO (latence, erreurs, saturation), pas seulement le CPU, et avoir un dashboard par service.

#### R4. Avez-vous déployé des microservices sur AWS ? Expliquez le flux de déploiement.

**Réponse :** Flux typique : commit → CI (build, tests, scan) → image Docker → push vers **ECR** → déploiement sur ECS/EKS (Terraform/CloudFormation pour l'infra, ArgoCD/CodeDeploy pour les releases) derrière un **ALB**, en rolling/blue-green/canary → health checks → supervision CloudWatch et rollback automatique. Secrets dans Secrets Manager, rôles IAM par tâche, configuration par environnement.

## 🎤 Quiz oral

Dix questions réparties sur les niveaux. Répondez à chacune **à voix haute en 2–3 minutes**, sans regarder, en structurant : contexte → options → décision → compromis. Ouvrez ensuite la question et notez-vous : **0** vide · **1** définition seule · **2** plus un exemple · **3** plus compromis et piège. Sous 24/30, refaites les points faibles après deux semaines. Les questions et scénarios sont dans les sections ci-dessus.

1. Q1. Comment fonctionne AWS IAM, et comment un service Spring Boot doit-il obtenir ses identifiants ?
2. Q2. Qu'est-ce qu'un VPC, et comment s'articulent sous-réseaux publics et privés ?
3. Q3. EC2, ECS, EKS ou Lambda — comment choisir où exécuter un service Java ?
4. Q4. Quels services managés de données et de messaging un développeur full-stack doit-il connaître, et quand utiliser chacun ?
5. Q5. Comment déployer une SPA React sur AWS ?
6. Q6. Comment appliquer le moindre privilège dans IAM sans bloquer toutes les équipes ?
7. Q8. Qu'est-ce qui fait la facture AWS d'une application web typique, et quelles sont les surprises habituelles ?
8. Q9. Que signifie « hautement disponible » sur AWS, et quelle différence entre Multi-AZ et multi-région ?
9. Q11. Quand le serverless est-il la bonne architecture pour une équipe Java, et quand fait-il mal ?
10. S1. Le service reçoit `AccessDenied` sur S3 juste après un déploiement

## 📌 Cheat-sheet

### Identité & réseau

> **Pour commencer :** des rôles, pas des clés ; des sous-réseaux privés ; des security groups qui référencent des security groups.

- **IAM** — principal, action, ressource, condition ; le deny explicite l'emporte. *Les workloads assument des rôles (task role, Pod Identity/IRSA).*
- **Comptes** — un par environnement, Organizations + SCP, SSO pour les humains.
- **VPC** — sous-réseaux publics pour l'ALB seulement, privés pour les apps et bases, un NAT par AZ, VPC endpoints pour S3/ECR.

### Compute & données

> **Pour commencer :** ECS Fargate par défaut, Lambda pour les événements, EKS quand la plateforme existe.

- **Lambda** — 15 min max, cold starts (SnapStart/native), RDS Proxy pour les connexions à la base.
- **Données** — RDS/Aurora (relationnel), DynamoDB (patterns d'accès connus), S3 (fichiers), ElastiCache (cache).
- **Messaging** — SQS (file + DLQ), SNS (fan-out), EventBridge (routage), MSK/Amazon MQ (Kafka/RabbitMQ).
- **SPA** — S3 privé + CloudFront OAC, assets hashés immuables, `index.html` en no-cache, origin `/api/*`.

### Fiabilité & coûts

> **Pour commencer :** Multi-AZ toujours, multi-région seulement si les RTO/RPO l'exigent.

- **HA** — répartir sur les AZ, aucune dépendance mono-AZ, capacité pour N-1 AZ.
- **Secrets** — Secrets Manager/SSM + KMS, ou auth IAM RDS ; jamais dans le state Terraform ni en env en clair.
- **Coûts** — octets NAT, transfert de données, logs, ressources inutilisées ; tags, budgets, alertes d'anomalie, Savings Plans, Graviton.
