# Cloud (AWS)

Most Java/React job ads list "AWS, Azure or GCP". This module uses AWS names, but the reasoning (identity, network, compute choice, managed data, cost) transfers to the other clouds. Kubernetes itself is in [Full Stack & DevOps](fullstack-devops-k8s.md), and Terraform commands are in the [Terraform notes](../notes/terraform.md).

## 🟢 Fundamentals

### Identity & network

#### Q1. How does AWS IAM work, and how should a Spring Boot service get its credentials? {#aws-iam-spring-boot-service}
**Answer:** IAM decides **who** (a principal: user, role, service) can do **what** (actions such as `s3:GetObject`) on
**which resource** (an ARN), under which conditions. Policies are JSON documents attached to identities or resources;
an explicit `Deny` always wins, and everything not allowed is denied. Applications should never use long-lived access
keys: they assume a **role** and get short-lived credentials automatically, through the EC2 instance profile, the ECS
task role, **EKS Pod Identity / IRSA**, or the Lambda execution role. The AWS SDK's default credential chain picks
these up with no code. Humans log in through SSO (IAM Identity Center), not IAM users with static keys.

**Example:**

```json
{
  "Effect": "Allow",
  "Action": ["s3:GetObject", "s3:PutObject"],
  "Resource": "arn:aws:s3:::acme-invoices-prod/*"
}
```

#### Q2. What is a VPC, and how do public and private subnets fit together? {#vpc-public-private-subnets-fit}
**Answer:** A **VPC** is your private network in a region, split into **subnets**, each in one availability zone (AZ).
A **public subnet** has a route to an **Internet Gateway**; put only load balancers and bastions (or nothing) there.
**Private subnets** hold application and database instances; they reach the internet for outbound calls through a
**NAT Gateway**, and reach AWS services privately through **VPC endpoints** (cheaper than NAT for S3/DynamoDB traffic).
**Security groups** are stateful firewalls on each resource; reference other security groups instead of IP ranges
(the DB accepts 5432 only from the app's security group). Spread every tier across at least two AZs.

**Example:**

```text
Internet → ALB (public subnets, AZ a/b)
         → ECS tasks / EKS pods (private subnets, AZ a/b)   SG: 8080 from ALB SG
         → RDS Postgres Multi-AZ (private DB subnets)       SG: 5432 from app SG
outbound: NAT Gateway per AZ; S3 via gateway endpoint
```

### Compute & data

#### Q3. EC2, ECS, EKS or Lambda — how do you choose where to run a Java service? {#ec2-ecs-eks-lambda-run}
**Answer:** **Lambda** suits event-driven, spiky or low-traffic work (S3 triggers, queue consumers, small APIs): no
servers, pay per request, but there are limits on duration (15 min) and payload, and JVM cold starts (mitigate with
SnapStart, GraalVM native or a lighter framework). **ECS on Fargate** is the simplest way to run long-running
containers: no cluster to manage, good for most Spring Boot services. **EKS** gives you Kubernetes: portable, a rich
ecosystem (Helm, operators, service mesh), but with platform work you must staff. **EC2** directly is for special
needs (GPUs, licensed software, very tuned workloads). Default for a small team: ECS Fargate; EKS when the
organization already runs a Kubernetes platform.

**Example:**

```text
Order API, steady traffic, Spring Boot         -> ECS Fargate (or EKS if the platform exists)
Thumbnail generation on S3 upload              -> Lambda
Nightly 3-hour batch                           -> ECS scheduled task / AWS Batch (not Lambda: 15 min limit)
```

#### Q4. Which managed data and messaging services should a full-stack developer know, and when do you use each? {#managed-data-messaging-services-full}
**Answer:** **RDS / Aurora** for relational data (Postgres), with Multi-AZ for availability and read replicas for read
scaling. **DynamoDB** for key-value access at any scale when you know your access patterns upfront. **S3** for files,
backups and static sites (with CloudFront in front). **ElastiCache** (Redis/Valkey) for caching and sessions. **SQS** for
point-to-point queues (standard: at-least-once, best-effort order; FIFO: ordered per group, lower throughput), **SNS**
for pub/sub fan-out (often SNS → several SQS queues), **EventBridge** for event routing between services and SaaS, and
**MSK** or **Amazon MQ** when you need Kafka or RabbitMQ semantics (see [Messaging](messaging-rabbitmq-kafka.md)).

**Example:**

```text
OrderPlaced -> SNS topic -> SQS "billing"   -> billing service
                         -> SQS "shipping"  -> shipping service
                         -> SQS "analytics" -> Lambda -> S3 data lake
each queue has its own DLQ and retry policy
```

#### Q5. How do you deploy a React SPA on AWS? {#deploy-react-spa-aws}
**Answer:** Build static files and upload them to a **private S3 bucket**, served through **CloudFront** with Origin
Access Control (the bucket isn't public). Cache hashed assets (`main.abc123.js`) for a year and `index.html` for a short
time or not at all, so a deploy takes effect immediately; invalidate `index.html` on deploy. Return `index.html` for
client-side routes (a CloudFront error response or function). Use ACM for TLS, add security headers (CSP, HSTS) with a
response-headers policy, and route `/api/*` to the backend's ALB as a second origin, so browser and API share one
domain and CORS disappears.

**Example:**

```text
aws s3 sync dist/ s3://acme-web-prod --delete \
  --cache-control "public,max-age=31536000,immutable" --exclude index.html
aws s3 cp dist/index.html s3://acme-web-prod/ --cache-control "no-cache"
aws cloudfront create-invalidation --distribution-id E123 --paths /index.html
```

## 🟡 Senior traps

### Questions

#### Q6. How do you apply least privilege in IAM without blocking every team? {#apply-least-privilege-iam-blocking}
**Answer:** One role per workload with only the actions and resources it uses, scoped by ARN and, where useful,
conditions (tags, `aws:SourceVpce`, encryption required). Avoid `*` actions and resources, and never attach
`AdministratorAccess` to a service. Start from **IAM Access Analyzer** (it can generate a policy from CloudTrail
activity) and its unused-access findings. Use **separate AWS accounts** per environment (and per team for larger
organizations) under **AWS Organizations**, with **Service Control Policies** as guardrails (deny disabling CloudTrail,
deny unapproved regions). Define roles in Terraform so they are reviewed like code.

**Example:**

```text
⛔ "Action": "s3:*", "Resource": "*"
✅ "Action": ["s3:GetObject"], "Resource": "arn:aws:s3:::acme-invoices-prod/tenant/*",
   "Condition": {"StringEquals": {"aws:ResourceTag/env": "prod"}}
```

**Why it's a trap:** a leaked credential's blast radius is the policy attached to it; `s3:*` on `*` turns a bug in one
small service into a data breach of every bucket in the account.

#### Q7. Where do application secrets live on AWS, and how do they reach the app? {#application-secrets-live-aws-app}
**Answer:** In **Secrets Manager** (rotation built in, for example for RDS passwords) or **SSM Parameter Store**
SecureString (cheaper, for config and secrets without rotation), encrypted with **KMS**. The workload's role is allowed
to read only its own secrets. They reach the app through ECS task-definition `secrets`, the Kubernetes External Secrets
Operator or Secrets Store CSI driver ([Full Stack Q38](fullstack-devops-k8s.md#application-secrets-managed-kubernetes-kubernetes)), or Spring Cloud AWS reading them at
startup. Even better, avoid the secret altogether: **RDS IAM authentication** uses the role instead of a password.

**Example:**

```json
"secrets": [
  { "name": "SPRING_DATASOURCE_PASSWORD",
    "valueFrom": "arn:aws:secretsmanager:eu-west-1:123456789012:secret:orders/db-AbCd" }
]
```

**Why it's a trap:** secrets in Terraform variables or plain environment variables in the task definition end up in
state files, the console and CI logs.

#### Q8. What drives the AWS bill for a typical web application, and what are the usual surprises? {#drives-aws-bill-web-application}
**Answer:** Compute (instance and Fargate hours, overprovisioned requests), managed databases (instance size,
Multi-AZ, storage IOPS), and the surprises: **NAT Gateway** data processing (all private traffic to S3 or ECR going
through NAT instead of VPC endpoints), **cross-AZ and internet data transfer**, **CloudWatch Logs** ingestion of debug
logs, idle resources (old environments, unattached volumes, forgotten snapshots), and high-cardinality custom metrics.
Levers: rightsizing, Graviton (ARM) instances, Savings Plans for the steady baseline, Spot for interruptible work,
autoscaling to zero for non-prod at night, S3 lifecycle rules, and **tagging plus budgets and anomaly alerts** so each
team sees its own cost.

**Example:**

```text
Cost Explorer, top line items this month:
  NAT Gateway bytes processed   $4,100   <- ECR image pulls + S3 traffic through NAT
  → add S3 gateway endpoint + ECR interface endpoints: -$3,300/month
```

**Why it's a trap:** architecture diagrams don't show data transfer, and it's often the line that grows fastest.

#### Q9. What does "highly available" mean on AWS, and what's the difference between Multi-AZ and multi-region? {#highly-available-aws-multi-az}
**Answer:** **Multi-AZ** (at least two availability zones in one region) is the baseline for production: load balancer
across AZs, tasks or pods spread across AZs, RDS Multi-AZ with automatic failover (about a minute), and no single-AZ
dependency such as one NAT Gateway. It protects against the failure of a data centre and is cheap. **Multi-region**
protects against a regional outage or meets data-residency rules, but it's expensive and complex: data replication
(Aurora Global Database, DynamoDB global tables), DNS failover with Route 53 health checks, and writes in two regions
bring conflicts. Pick it from the RTO/RPO the business really needs ([System Design Q31](system-design.md#rto-rpo-disaster-recovery-planning)): often
backups plus infrastructure as code that can rebuild in another region (pilot light) is enough.

**Example:**

```text
RTO 4 h, RPO 15 min   -> Multi-AZ + cross-region backups + Terraform to rebuild (pilot light)
RTO 1 min, RPO ~0     -> active-active multi-region, global tables, conflict strategy (rarely justified)
```

**Why it's a trap:** "we're on AWS so we're highly available" is false; a single-AZ deployment fails like any data
centre, and many outages come from a forgotten single-AZ component.

## 🔴 Expert / Open

### Questions

#### Q10. How would you organise AWS accounts and infrastructure as code for a company with several teams? {#organise-aws-accounts-infrastructure-code}
**Answer:** A **multi-account landing zone** (Control Tower or a Terraform equivalent): management, security/log
archive, shared networking, and workload accounts per environment (and per team or domain as it grows). Centralised
CloudTrail, GuardDuty and Config, SSO for humans with permission sets, SCP guardrails. Infrastructure in **Terraform**
(or CDK) with remote state per environment and component, small modules owned by a platform team, and plan/apply from
CI with OIDC-federated roles (no static keys in CI). Teams own their service stacks; the platform team owns the paved
road (VPC, cluster, pipelines, observability).

#### Q11. When is serverless the right architecture for a Java team, and when does it hurt? {#serverless-right-architecture-java-team}
**Answer:** Serverless (API Gateway, Lambda, SQS, DynamoDB, Step Functions) is attractive for event-driven and spiky
workloads, small teams with no ops capacity, and glue between managed services: you pay for use and scale to zero. It
hurts with steady high traffic (per-request pricing exceeds containers), long or stateful processing, heavy
relational work with many connections (use RDS Proxy), strict latency where cold starts matter, and when local
development and testing across many functions slows the team down. For Java: SnapStart or native images for cold
starts, one function per bounded use case rather than per endpoint, and Step Functions for workflows instead of
Lambdas calling Lambdas.

## 🎯 Real-world scenarios

### S1. The service gets `AccessDenied` on S3 right after a deployment {#service-gets-accessdenied-s3-right}
- **Symptoms:** A new ECS task (or pod) logs `software.amazon.awssdk.services.s3.model.S3Exception: Access Denied
  (Status Code: 403)` when writing invoices; the previous version worked.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Check which identity the app is really using (`aws sts get-caller-identity` from the container, or
  the SDK debug log); the new task definition or service account may reference a different role, or none (falling back
  to the node role). Then check the role policy, the **bucket policy**, the KMS key policy if the bucket uses SSE-KMS,
  and any SCP. CloudTrail shows the denied call with the principal and the reason.
- **Example:**

  ```text
  CloudTrail: PutObject  principal=arn:aws:sts::123:assumed-role/eks-node-role/...  errorCode=AccessDenied
  -> pod is using the node role: serviceAccountName was dropped from the Helm values
  ```

- **Resolution:** Restore the correct role binding (task role or service account annotation/Pod Identity association),
  and add `kms:GenerateDataKey` if the bucket is KMS-encrypted.
- **Prevention:** Keep role and binding in the same Terraform/Helm change, make node roles minimal so a fallback fails
  loudly, and add a startup smoke check for the critical permissions.

</details>

### S2. The AWS bill doubled this month and nobody changed the architecture {#aws-bill-doubled-month-nobody}
- **Symptoms:** Finance flags a 2× increase; the main growth line is "EC2-Other" and "Data Transfer".

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** In Cost Explorer, group by usage type and then by tag/account. "EC2-Other" usually hides NAT Gateway
  bytes, EBS volumes and snapshots. Check VPC Flow Logs for the top talkers through NAT, and look for cross-AZ chatter
  (a service calling a cache or broker in another AZ at high volume).
- **Example:**

  ```text
  usage type NatGateway-Bytes: 38 TB (+30 TB)
  top flow: batch job pods -> S3 (via NAT), new nightly export
  ```

- **Resolution:** Add the S3 gateway endpoint (free) and interface endpoints for ECR, STS and Secrets Manager; move the
  export closer to its data; delete orphaned volumes and snapshots.
- **Prevention:** Mandatory cost-allocation tags, per-team budgets with anomaly detection, and a cost review in the
  design checklist for any new data flow.

</details>

### S3. An availability zone has problems, and part of the traffic fails {#availability-zone-has-problems-part}
- **Symptoms:** Error rate rises to about 30% during an AWS incident in one AZ; the service runs in two AZs.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Break errors down by AZ (load balancer target metrics, logs with AZ metadata). Common causes: tasks in
  the bad AZ still pass shallow health checks, a single NAT Gateway or cache node lives in that AZ, or the remaining
  AZ lacks capacity to absorb the load.
- **Example:**

  ```text
  ALB: 5xx only from targets in eu-west-1b; health checks green (/health returns 200 without checking deps)
  all private subnets route outbound through one NAT Gateway in eu-west-1b
  ```

- **Resolution:** Shift traffic away from the impaired AZ (ALB zonal shift / ARC), scale up the healthy AZ, and fail
  over stateful components if needed.
- **Prevention:** One NAT Gateway per AZ, capacity planned for N-1 AZs, meaningful readiness checks, zonal autoshift,
  and regular game days that simulate an AZ loss.

</details>

### S4. A Lambda-based API works in testing, then exhausts RDS connections during the first marketing campaign {#lambda-exhausts-rds-connections}
- **Symptoms:** `FATAL: remaining connection slots are reserved` from Postgres; Lambda concurrency went from 20 to 900 in minutes; cold-start p99 at 3 s.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Each concurrent Lambda execution environment opens its own connection (or pool), so connections scale with concurrency, not with load on the database. Cold starts add JVM startup plus a TLS + auth handshake to the DB.
- **Resolution:** Put RDS Proxy in front of the database (pools and multiplexes connections), set reserved concurrency on the function to cap fan-out, keep the pool size at 1 per environment, and reduce cold starts with SnapStart (Java) or provisioned concurrency for the hot path.
- **Prevention:** Load-test with the expected concurrency, alert on `DatabaseConnections` and Lambda `ConcurrentExecutions`, and document the concurrency budget per function.

</details>

### S5. After an RDS Multi-AZ failover, the database is healthy in 60 seconds but the app keeps failing for 15 minutes {#rds-failover-stale-dns}
- **Symptoms:** AWS event shows failover completed at 03:12; the application logs `Connection refused` / read-only errors until pods are restarted at 03:27.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** The cluster endpoint DNS now points to the new primary, but the JVM cached the old IP (`networkaddress.cache.ttl` unlimited with a security manager, or long by default), and the pool keeps handing out dead connections without validation or a max lifetime.
- **Example:**

  ```properties
  # JVM: respect the endpoint's short DNS TTL
  networkaddress.cache.ttl=5
  # HikariCP: recycle connections and fail fast
  spring.datasource.hikari.max-lifetime=600000
  spring.datasource.hikari.connection-timeout=3000
  ```

- **Resolution:** Set a short JVM DNS TTL, configure `maxLifetime` and timeouts in the pool, and use the AWS Advanced JDBC Wrapper (failover plugin) or RDS Proxy, which hides the failover from clients.
- **Prevention:** Run a failover drill in staging every quarter (`aws rds failover-db-cluster`) and measure time-to-recover for the application, not just for the database.

</details>

## 🗣️ Reported interview questions

Questions reported from real interviews, grouped by topic. Each has a short model answer: expand it with the detailed questions and scenarios above, and say the answer aloud.

### Access & services

#### R1. An EC2 instance needs to access S3 securely. How do you configure it without storing credentials? {#ec2-instance-needs-access-s3}
**Answer:** Attach an **IAM role** (instance profile) with a least-privilege policy for the specific bucket/prefix; the SDK gets temporary credentials from the instance metadata service (use IMDSv2). Optionally restrict with a bucket policy, a VPC endpoint and `aws:SourceVpce`. No access keys in code, env vars or AMIs.

#### R2. Difference between EC2, ECS and Lambda. {#ec2-ecs-lambda}
**Answer:** **EC2**: virtual machines you manage (OS, scaling, patching): maximum control. **ECS**: container orchestrator, on EC2 or serverless **Fargate**. **Lambda**: functions run on events, auto-scaled, pay per invocation, with time and memory limits and cold starts. Choose by control vs operations vs workload shape.

#### R3. How do you monitor applications in AWS? {#monitor-applications-aws}
**Answer:** **CloudWatch** metrics, logs and alarms (plus Logs Insights, Container Insights); **X-Ray**/OpenTelemetry for traces; CloudTrail for API audit; health checks and SNS/PagerDuty for alerts. Alert on SLOs (latency, errors, saturation), not just CPU, and use dashboards per service.

#### R4. Have you deployed microservices on AWS? Explain the deployment flow. {#have-deployed-microservices-aws-deployment}
**Answer:** Typical flow: commit → CI (build, test, scan) → build a Docker image → push to **ECR** → deploy to ECS/EKS (Terraform/CloudFormation for infra, ArgoCD/CodeDeploy for releases) behind an **ALB**, using rolling/blue-green/canary → health checks → CloudWatch monitoring and automatic rollback. Secrets in Secrets Manager, IAM roles per task, config per environment.

## 🎤 Oral quiz

Ten questions picked across the levels. Answer each **aloud in 2–3 minutes** without looking, structuring it as context → options → decision → trade-offs. Then open the linked question and score yourself: **0** blank · **1** definition only · **2** plus an example · **3** plus trade-offs and a pitfall. Below 24/30, redo the weak ones after two weeks. Questions and scenarios are in the sections above.

1. Q1. How does AWS IAM work, and how should a Spring Boot service get its credentials?
2. Q2. What is a VPC, and how do public and private subnets fit together?
3. Q3. EC2, ECS, EKS or Lambda — how do you choose where to run a Java service?
4. Q4. Which managed data and messaging services should a full-stack developer know, and when do you use each?
5. Q5. How do you deploy a React SPA on AWS?
6. Q6. How do you apply least privilege in IAM without blocking every team?
7. Q8. What drives the AWS bill for a typical web application, and what are the usual surprises?
8. Q9. What does "highly available" mean on AWS, and what's the difference between Multi-AZ and multi-region?
9. Q11. When is serverless the right architecture for a Java team, and when does it hurt?
10. S1. The service gets `AccessDenied` on S3 right after a deployment

## 📌 Cheat-sheet

### Identity & network

> **Start here:** roles not keys, private subnets, security groups referencing security groups.

- **IAM** — principal, action, resource, condition; explicit deny wins. *Workloads assume roles (task role, Pod Identity/IRSA).*
- **Accounts** — one per environment, Organizations + SCPs, SSO for humans.
- **VPC** — public subnets for ALB only, private for apps and DBs, NAT per AZ, VPC endpoints for S3/ECR.

### Compute & data

> **Start here:** ECS Fargate by default, Lambda for events, EKS when the platform exists.

- **Lambda** — 15 min max, cold starts (SnapStart/native), RDS Proxy for DB connections.
- **Data** — RDS/Aurora (relational), DynamoDB (known access patterns), S3 (files), ElastiCache (cache).
- **Messaging** — SQS (queue + DLQ), SNS (fan-out), EventBridge (routing), MSK/Amazon MQ (Kafka/RabbitMQ).
- **SPA** — private S3 + CloudFront OAC, immutable hashed assets, `index.html` no-cache, `/api/*` origin.

### Reliability & cost

> **Start here:** Multi-AZ always, multi-region only when RTO/RPO demand it.

- **HA** — spread across AZs, no single-AZ dependency, capacity for N-1 AZs.
- **Secrets** — Secrets Manager/SSM + KMS, or RDS IAM auth; never in Terraform state or plain env.
- **Cost** — NAT bytes, data transfer, logs, idle resources; tags, budgets, anomaly alerts, Savings Plans, Graviton.
