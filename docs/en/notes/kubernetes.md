# Kubernetes

## Context and namespaces

### Contexts (clusters)
```bash
kubectl config get-contexts
kubectl config current-context
kubectl config use-context prod-eu
kubectl config set-context --current --namespace=payments   # default namespace for this context
```

### Namespaces
```bash
kubectl get ns
kubectl create ns staging
kubectl get pods -n kube-system
kubectl get pods -A                            # all namespaces
```

### Handy aliases
```bash
alias k=kubectl
source <(kubectl completion zsh)
complete -o default -F __start_kubectl k       # bash
```

---

## Daily kubectl

### Get resources
```bash
kubectl get pods
kubectl get pods -o wide                       # node + IP
kubectl get pods -l app=api                    # label selector
kubectl get pods --field-selector status.phase=Running
kubectl get pods -w                            # watch
kubectl get deploy,svc,ing                     # several kinds at once
kubectl get all                                # pods, svc, deploy, rs (not everything!)
kubectl get pod api-7d9c -o yaml
kubectl get pod api-7d9c -o jsonpath='{.status.podIP}'
kubectl get pods --sort-by=.metadata.creationTimestamp
kubectl get pods -o custom-columns=NAME:.metadata.name,NODE:.spec.nodeName,STATUS:.status.phase
```

### Typical output
```text
NAME                   READY   STATUS             RESTARTS      AGE
api-7d9c8b6f5d-4xk2p   1/1     Running            0             3h
api-7d9c8b6f5d-9zq7m   0/1     CrashLoopBackOff   6 (45s ago)   10m
```

### Describe, apply, delete
```bash
kubectl describe pod api-7d9c8b6f5d-9zq7m      # events at the bottom are the useful part
kubectl apply -f deploy.yaml
kubectl apply -f k8s/                          # whole directory
kubectl apply -k overlays/prod                 # kustomize
kubectl diff -f deploy.yaml                    # preview changes
kubectl delete -f deploy.yaml
kubectl delete pod api-7d9c --grace-period=0 --force   # stuck pod (last resort)
```

### Generate YAML instead of writing it
```bash
kubectl create deploy api --image=myapp:1.0 --replicas=2 --dry-run=client -o yaml > deploy.yaml
kubectl expose deploy api --port=80 --target-port=8080 --dry-run=client -o yaml
kubectl explain deployment.spec.strategy       # built-in field docs
```

### Edit and patch live objects
```bash
kubectl edit deploy api
kubectl scale deploy api --replicas=5
kubectl set image deploy/api api=myapp:1.1
kubectl set env deploy/api LOG_LEVEL=debug
kubectl label pod api-7d9c tier=backend
kubectl annotate pod api-7d9c owner=team-a
kubectl patch deploy api -p '{"spec":{"replicas":3}}'
```

---

## Debugging pods

### Logs
```bash
kubectl logs api-7d9c
kubectl logs -f api-7d9c --tail=100
kubectl logs api-7d9c -c sidecar               # specific container
kubectl logs api-7d9c --previous               # the crashed instance
kubectl logs -l app=api --all-containers --prefix   # all pods of a label
kubectl logs deploy/api --since=10m
```

### Exec, port-forward, copy
```bash
kubectl exec -it api-7d9c -- sh
kubectl exec api-7d9c -- env
kubectl port-forward pod/api-7d9c 8080:8080
kubectl port-forward svc/api 8080:80
kubectl cp api-7d9c:/tmp/heap.hprof ./heap.hprof
```

### Ephemeral debug container (image has no shell)
```bash
kubectl debug -it api-7d9c --image=nicolaka/netshoot --target=api
kubectl debug node/worker-1 -it --image=busybox        # host access on a node
kubectl run tmp --rm -it --image=busybox --restart=Never -- sh
```

### Reading STATUS

| Status | Meaning | First thing to check |
|---|---|---|
| `Pending` | Not scheduled | `describe` events: resources, taints, PVC, nodeSelector |
| `ContainerCreating` | Pulling image / mounting | Events: volume mount errors |
| `ImagePullBackOff` / `ErrImagePull` | Cannot pull image | Image name/tag, `imagePullSecrets` |
| `CrashLoopBackOff` | App keeps exiting | `logs --previous`, exit code, probes |
| `OOMKilled` (in `describe`) | Exceeded memory limit | Raise `limits.memory` or fix leak |
| `Error` / `Completed` | Job-style exit | Exit code in `describe` |
| `Terminating` (stuck) | Finalizer or node down | `kubectl get pod -o yaml` finalizers |
| `Running` but `0/1 READY` | Readiness probe failing | Probe path/port, `describe` events |

### Why is it restarting?
```bash
kubectl describe pod api-7d9c | grep -A6 'Last State'
```
```text
    Last State:     Terminated
      Reason:       OOMKilled
      Exit Code:    137
```

### Events, resource usage
```bash
kubectl get events --sort-by=.lastTimestamp
kubectl get events --field-selector type=Warning
kubectl top pods                               # needs metrics-server
kubectl top nodes
kubectl top pod --containers
```

### Service has no endpoints?
```bash
kubectl get endpoints api                      # empty = selector matches no ready pod
kubectl get svc api -o jsonpath='{.spec.selector}'
kubectl get pods -l app=api                    # do these labels match?
```

---

## Troubleshooting: find the cause, then fix it

Method, always in this order:
```bash
kubectl get pod api-7d9c -o wide               # STATUS, RESTARTS, node
kubectl describe pod api-7d9c                  # read the Events at the bottom first
kubectl logs api-7d9c --previous               # why the last run died
kubectl exec -it api-7d9c -- sh                # check env, files, DNS from inside
```

| Symptom | Likely cause | Confirm | Fix |
|---|---|---|---|
| `Pending` | Not enough CPU/memory | Event `FailedScheduling: Insufficient cpu` | Lower `requests`, add nodes, `kubectl top nodes` |
| `Pending` | Taint / nodeSelector / affinity | Event `node(s) had untolerated taint` | Add `tolerations`, fix `nodeSelector` |
| `Pending` | PVC not bound | `kubectl get pvc` shows `Pending` | Fix `storageClassName`, check the provisioner |
| `ImagePullBackOff` | Wrong name/tag | Event `manifest unknown` / `not found` | Fix `image:`, verify the tag exists |
| `ImagePullBackOff` | Private registry | Event `unauthorized` | `kubectl create secret docker-registry ...` + `imagePullSecrets` |
| `CrashLoopBackOff` | App error / bad config | `logs --previous`, exit code 1 | Fix config/env, missing dependency |
| `CrashLoopBackOff` | Liveness probe kills a slow app | Event `Liveness probe failed` | Add `startupProbe` or raise `initialDelaySeconds` |
| `OOMKilled` (exit 137) | Memory limit too low or leak | `describe` → `Last State: OOMKilled` | Raise `limits.memory`, fix leak (heap dump with `kubectl cp`) |
| `CreateContainerConfigError` | ConfigMap/Secret/key missing | Event `configmap "x" not found` | Create it or fix the name/key in the manifest |
| `Running`, `0/1 READY` | Readiness probe failing | Event `Readiness probe failed` | Fix probe path/port or the app's startup |
| `Evicted` | Node under disk/memory pressure | `describe` reason `Evicted` | Set `requests`/`limits`, free the node, `kubectl delete pod` the evicted ones |
| `Terminating` (stuck) | Finalizer or dead node | `get pod -o yaml` → `finalizers` | `kubectl patch pod x -p '{"metadata":{"finalizers":null}}'` (last resort: `--force --grace-period=0`) |
| Service unreachable | Selector doesn't match | `kubectl get endpoints api` is empty | Align `spec.selector` with pod labels |
| Service unreachable | Wrong `targetPort` | `port-forward pod/x` works, `svc/x` doesn't | Set `targetPort` to the container port |
| Ingress 404 / 502 | Wrong host/path or no ready backend | `describe ingress`, `get endpoints` | Fix host/path/`serviceName`, fix readiness |
| DNS fails in a pod | CoreDNS down / wrong name | `kubectl exec x -- nslookup api` | Use `svc.namespace.svc.cluster.local`, check `kubectl -n kube-system get pods -l k8s-app=kube-dns` |

Applied fix, then verify:
```bash
kubectl apply -f deployment.yaml
kubectl rollout status deploy/api
kubectl get pods -l app=api -w
```

---

## Rollouts

### Deploy, watch, undo
```bash
kubectl set image deploy/api api=myapp:1.2
kubectl rollout status deploy/api              # blocks until done or failed
kubectl rollout history deploy/api
kubectl rollout history deploy/api --revision=3
kubectl rollout undo deploy/api                # previous revision
kubectl rollout undo deploy/api --to-revision=2
kubectl rollout restart deploy/api             # rolling restart, same image
kubectl rollout pause deploy/api
kubectl rollout resume deploy/api
```

### Autoscaling
```bash
kubectl autoscale deploy api --min=2 --max=10 --cpu-percent=70
kubectl get hpa
```

### Drain a node for maintenance
```bash
kubectl cordon worker-1                        # no new pods
kubectl drain worker-1 --ignore-daemonsets --delete-emptydir-data
kubectl uncordon worker-1
```

---

## Config and secrets

### ConfigMap
```bash
kubectl create configmap app-config --from-literal=LOG_LEVEL=info --from-file=application.yml
kubectl get cm app-config -o yaml
```

### Secret
```bash
kubectl create secret generic db-creds --from-literal=password='s3cr3t'
kubectl create secret docker-registry regcred \
  --docker-server=registry.example.com --docker-username=me --docker-password=xxx
kubectl get secret db-creds -o jsonpath='{.data.password}' | base64 -d
```

Secrets are only base64-encoded, not encrypted. Enable encryption at rest or use an external secret store.

### Use them in a pod
```yaml
containers:
  - name: api
    image: myapp:1.0
    envFrom:
      - configMapRef: { name: app-config }
    env:
      - name: DB_PASSWORD
        valueFrom:
          secretKeyRef: { name: db-creds, key: password }
    volumeMounts:
      - name: cfg
        mountPath: /config
volumes:
  - name: cfg
    configMap: { name: app-config }
```

---

## Manifests

### Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
  labels: { app: api }
spec:
  replicas: 3
  selector:
    matchLabels: { app: api }              # must match template labels
  strategy:
    type: RollingUpdate
    rollingUpdate: { maxSurge: 1, maxUnavailable: 0 }
  template:
    metadata:
      labels: { app: api }
    spec:
      containers:
        - name: api
          image: registry.example.com/myapp:1.0
          ports:
            - containerPort: 8080
          resources:
            requests: { cpu: 250m, memory: 512Mi }
            limits:   { memory: 1Gi }
          readinessProbe:
            httpGet: { path: /actuator/health/readiness, port: 8080 }
            initialDelaySeconds: 10
            periodSeconds: 5
          livenessProbe:
            httpGet: { path: /actuator/health/liveness, port: 8080 }
            initialDelaySeconds: 30
            periodSeconds: 10
```

`requests` drive scheduling, `limits` are enforced at runtime (memory over the limit = OOMKilled, CPU over the limit = throttled).

### Service
```yaml
apiVersion: v1
kind: Service
metadata:
  name: api
spec:
  selector: { app: api }
  ports:
    - port: 80
      targetPort: 8080
  type: ClusterIP
```

| Service type | Reachable from |
|---|---|
| `ClusterIP` | Inside the cluster only (default) |
| `NodePort` | `<nodeIP>:30000-32767` |
| `LoadBalancer` | Cloud load balancer, external IP |
| `ExternalName` | DNS CNAME to an outside host |

### Ingress
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: api
  annotations:
    nginx.ingress.kubernetes.io/proxy-body-size: 10m
spec:
  ingressClassName: nginx
  tls:
    - hosts: [api.example.com]
      secretName: api-tls
  rules:
    - host: api.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service: { name: api, port: { number: 80 } }
```

### CronJob
```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: nightly-report
spec:
  schedule: "0 2 * * *"
  concurrencyPolicy: Forbid
  jobTemplate:
    spec:
      backoffLimit: 2
      template:
        spec:
          restartPolicy: OnFailure
          containers:
            - name: report
              image: myapp:1.0
              args: ["report", "--daily"]
```
```bash
kubectl create job --from=cronjob/nightly-report manual-run-1   # trigger now
```

### PersistentVolumeClaim
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: data
spec:
  accessModes: [ReadWriteOnce]
  resources:
    requests: { storage: 10Gi }
```

---

## Access and RBAC

### Who can do what
```bash
kubectl auth can-i create pods -n staging
kubectl auth can-i --list
kubectl auth can-i get secrets --as=system:serviceaccount:staging:ci
kubectl get rolebindings,clusterrolebindings -A | grep my-user
```

### Grant a service account read access
```bash
kubectl create serviceaccount ci -n staging
kubectl create role pod-reader --verb=get,list,watch --resource=pods -n staging
kubectl create rolebinding ci-pod-reader --role=pod-reader --serviceaccount=staging:ci -n staging
```

---

## Useful one-liners

### Restart every pod stuck in a bad state
```bash
kubectl get pods -A | grep -E 'CrashLoopBackOff|Error|ImagePullBackOff'
kubectl delete pod --field-selector=status.phase=Failed -A
```

### Images running in the cluster
```bash
kubectl get pods -A -o jsonpath='{range .items[*]}{.spec.containers[*].image}{"\n"}{end}' | tr ' ' '\n' | sort | uniq -c
```

### Which node runs which pod
```bash
kubectl get pods -o wide --sort-by=.spec.nodeName
```
