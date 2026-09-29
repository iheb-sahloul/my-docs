# Kubernetes

## Contextes et namespaces

### Contextes (clusters)
```bash
kubectl config get-contexts
kubectl config current-context
kubectl config use-context prod-eu
kubectl config set-context --current --namespace=payments   # namespace par défaut pour ce contexte
```

### Namespaces
```bash
kubectl get ns
kubectl create ns staging
kubectl get pods -n kube-system
kubectl get pods -A                            # tous les namespaces
```

### Alias pratiques
```bash
alias k=kubectl
source <(kubectl completion zsh)
complete -o default -F __start_kubectl k       # bash
```

---

## kubectl au quotidien

### Lister des ressources
```bash
kubectl get pods
kubectl get pods -o wide                       # nœud + IP
kubectl get pods -l app=api                    # sélecteur de labels
kubectl get pods --field-selector status.phase=Running
kubectl get pods -w                            # watch
kubectl get deploy,svc,ing                     # plusieurs types à la fois
kubectl get all                                # pods, svc, deploy, rs (pas tout !)
kubectl get pod api-7d9c -o yaml
kubectl get pod api-7d9c -o jsonpath='{.status.podIP}'
kubectl get pods --sort-by=.metadata.creationTimestamp
kubectl get pods -o custom-columns=NAME:.metadata.name,NODE:.spec.nodeName,STATUS:.status.phase
```

### Sortie typique
```text
NAME                   READY   STATUS             RESTARTS      AGE
api-7d9c8b6f5d-4xk2p   1/1     Running            0             3h
api-7d9c8b6f5d-9zq7m   0/1     CrashLoopBackOff   6 (45s ago)   10m
```

### Describe, apply, delete
```bash
kubectl describe pod api-7d9c8b6f5d-9zq7m      # les événements en bas sont la partie utile
kubectl apply -f deploy.yaml
kubectl apply -f k8s/                          # dossier entier
kubectl apply -k overlays/prod                 # kustomize
kubectl diff -f deploy.yaml                    # prévisualiser les changements
kubectl delete -f deploy.yaml
kubectl delete pod api-7d9c --grace-period=0 --force   # pod bloqué (dernier recours)
```

### Générer du YAML plutôt que l'écrire
```bash
kubectl create deploy api --image=myapp:1.0 --replicas=2 --dry-run=client -o yaml > deploy.yaml
kubectl expose deploy api --port=80 --target-port=8080 --dry-run=client -o yaml
kubectl explain deployment.spec.strategy       # documentation intégrée des champs
```

### Modifier et patcher des objets en direct
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

## Déboguer des pods

### Logs
```bash
kubectl logs api-7d9c
kubectl logs -f api-7d9c --tail=100
kubectl logs api-7d9c -c sidecar               # conteneur précis
kubectl logs api-7d9c --previous               # l'instance qui a planté
kubectl logs -l app=api --all-containers --prefix   # tous les pods d'un label
kubectl logs deploy/api --since=10m
```

### Exec, port-forward, copie
```bash
kubectl exec -it api-7d9c -- sh
kubectl exec api-7d9c -- env
kubectl port-forward pod/api-7d9c 8080:8080
kubectl port-forward svc/api 8080:80
kubectl cp api-7d9c:/tmp/heap.hprof ./heap.hprof
```

### Conteneur de debug éphémère (l'image n'a pas de shell)
```bash
kubectl debug -it api-7d9c --image=nicolaka/netshoot --target=api
kubectl debug node/worker-1 -it --image=busybox        # accès à l'hôte sur un nœud
kubectl run tmp --rm -it --image=busybox --restart=Never -- sh
```

### Lire STATUS

| Statut | Signification | Première chose à vérifier |
|---|---|---|
| `Pending` | Non planifié | Événements de `describe` : ressources, taints, PVC, nodeSelector |
| `ContainerCreating` | Téléchargement de l'image / montage | Événements : erreurs de montage de volume |
| `ImagePullBackOff` / `ErrImagePull` | Impossible de récupérer l'image | Nom/tag de l'image, `imagePullSecrets` |
| `CrashLoopBackOff` | L'application s'arrête en boucle | `logs --previous`, code de sortie, probes |
| `OOMKilled` (dans `describe`) | Limite de mémoire dépassée | Augmenter `limits.memory` ou corriger la fuite |
| `Error` / `Completed` | Fin de type Job | Code de sortie dans `describe` |
| `Terminating` (bloqué) | Finalizer ou nœud arrêté | Finalizers dans `kubectl get pod -o yaml` |
| `Running` mais `0/1 READY` | Readiness probe en échec | Chemin/port de la probe, événements de `describe` |

### Pourquoi redémarre-t-il ?
```bash
kubectl describe pod api-7d9c | grep -A6 'Last State'
```
```text
    Last State:     Terminated
      Reason:       OOMKilled
      Exit Code:    137
```

### Événements, consommation de ressources
```bash
kubectl get events --sort-by=.lastTimestamp
kubectl get events --field-selector type=Warning
kubectl top pods                               # nécessite metrics-server
kubectl top nodes
kubectl top pod --containers
```

### Le service n'a pas d'endpoints ?
```bash
kubectl get endpoints api                      # vide = le sélecteur ne correspond à aucun pod prêt
kubectl get svc api -o jsonpath='{.spec.selector}'
kubectl get pods -l app=api                    # ces labels correspondent-ils ?
```

---

## Dépannage : trouver la cause, puis corriger

Méthode, toujours dans cet ordre :
```bash
kubectl get pod api-7d9c -o wide               # STATUS, RESTARTS, nœud
kubectl describe pod api-7d9c                  # lire d'abord les Events en bas
kubectl logs api-7d9c --previous               # pourquoi la dernière exécution est morte
kubectl exec -it api-7d9c -- sh                # vérifier env, fichiers, DNS de l'intérieur
```

| Symptôme | Cause probable | Vérifier | Correction |
|---|---|---|---|
| `Pending` | Pas assez de CPU/mémoire | Événement `FailedScheduling: Insufficient cpu` | Baisser `requests`, ajouter des nœuds, `kubectl top nodes` |
| `Pending` | Taint / nodeSelector / affinity | Événement `node(s) had untolerated taint` | Ajouter des `tolerations`, corriger `nodeSelector` |
| `Pending` | PVC non lié | `kubectl get pvc` affiche `Pending` | Corriger `storageClassName`, vérifier le provisioner |
| `ImagePullBackOff` | Mauvais nom/tag | Événement `manifest unknown` / `not found` | Corriger `image:`, vérifier que le tag existe |
| `ImagePullBackOff` | Registry privé | Événement `unauthorized` | `kubectl create secret docker-registry ...` + `imagePullSecrets` |
| `CrashLoopBackOff` | Erreur applicative / mauvaise config | `logs --previous`, code de sortie 1 | Corriger config/env, dépendance manquante |
| `CrashLoopBackOff` | La liveness probe tue une appli lente | Événement `Liveness probe failed` | Ajouter un `startupProbe` ou augmenter `initialDelaySeconds` |
| `OOMKilled` (exit 137) | Limite mémoire trop basse ou fuite | `describe` → `Last State: OOMKilled` | Augmenter `limits.memory`, corriger la fuite (heap dump avec `kubectl cp`) |
| `CreateContainerConfigError` | ConfigMap/Secret/clé manquant | Événement `configmap "x" not found` | Le créer ou corriger le nom/la clé dans le manifest |
| `Running`, `0/1 READY` | Readiness probe en échec | Événement `Readiness probe failed` | Corriger chemin/port de la probe ou le démarrage de l'appli |
| `Evicted` | Nœud sous pression disque/mémoire | Raison `Evicted` dans `describe` | Définir `requests`/`limits`, libérer le nœud, `kubectl delete pod` des pods évincés |
| `Terminating` (bloqué) | Finalizer ou nœud mort | `get pod -o yaml` → `finalizers` | `kubectl patch pod x -p '{"metadata":{"finalizers":null}}'` (dernier recours : `--force --grace-period=0`) |
| Service inaccessible | Le sélecteur ne correspond pas | `kubectl get endpoints api` est vide | Aligner `spec.selector` avec les labels des pods |
| Service inaccessible | Mauvais `targetPort` | `port-forward pod/x` marche, `svc/x` non | Mettre `targetPort` sur le port du conteneur |
| Ingress 404 / 502 | Mauvais host/chemin ou aucun backend prêt | `describe ingress`, `get endpoints` | Corriger host/chemin/`serviceName`, corriger la readiness |
| DNS en échec dans un pod | CoreDNS arrêté / mauvais nom | `kubectl exec x -- nslookup api` | Utiliser `svc.namespace.svc.cluster.local`, vérifier `kubectl -n kube-system get pods -l k8s-app=kube-dns` |

Appliquer la correction, puis vérifier :
```bash
kubectl apply -f deployment.yaml
kubectl rollout status deploy/api
kubectl get pods -l app=api -w
```

---

## Rollouts

### Déployer, surveiller, annuler
```bash
kubectl set image deploy/api api=myapp:1.2
kubectl rollout status deploy/api              # bloque jusqu'à la fin ou l'échec
kubectl rollout history deploy/api
kubectl rollout history deploy/api --revision=3
kubectl rollout undo deploy/api                # révision précédente
kubectl rollout undo deploy/api --to-revision=2
kubectl rollout restart deploy/api             # redémarrage progressif, même image
kubectl rollout pause deploy/api
kubectl rollout resume deploy/api
```

### Autoscaling
```bash
kubectl autoscale deploy api --min=2 --max=10 --cpu-percent=70
kubectl get hpa
```

### Vider un nœud pour maintenance
```bash
kubectl cordon worker-1                        # plus de nouveaux pods
kubectl drain worker-1 --ignore-daemonsets --delete-emptydir-data
kubectl uncordon worker-1
```

---

## Configuration et secrets

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

Les Secrets sont seulement encodés en base64, pas chiffrés. Activez le chiffrement au repos ou utilisez un gestionnaire de secrets externe.

### Les utiliser dans un pod
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
    matchLabels: { app: api }              # doit correspondre aux labels du template
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

Les `requests` guident la planification, les `limits` sont appliquées à l'exécution (mémoire au-delà de la limite = OOMKilled, CPU au-delà de la limite = throttling).

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

| Type de Service | Accessible depuis |
|---|---|
| `ClusterIP` | L'intérieur du cluster uniquement (par défaut) |
| `NodePort` | `<nodeIP>:30000-32767` |
| `LoadBalancer` | Load balancer du cloud, IP externe |
| `ExternalName` | CNAME DNS vers un hôte externe |

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
kubectl create job --from=cronjob/nightly-report manual-run-1   # déclencher maintenant
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

## Accès et RBAC

### Qui peut faire quoi
```bash
kubectl auth can-i create pods -n staging
kubectl auth can-i --list
kubectl auth can-i get secrets --as=system:serviceaccount:staging:ci
kubectl get rolebindings,clusterrolebindings -A | grep my-user
```

### Donner un accès en lecture à un service account
```bash
kubectl create serviceaccount ci -n staging
kubectl create role pod-reader --verb=get,list,watch --resource=pods -n staging
kubectl create rolebinding ci-pod-reader --role=pod-reader --serviceaccount=staging:ci -n staging
```

---

## Commandes utiles en une ligne

### Redémarrer chaque pod bloqué dans un mauvais état
```bash
kubectl get pods -A | grep -E 'CrashLoopBackOff|Error|ImagePullBackOff'
kubectl delete pod --field-selector=status.phase=Failed -A
```

### Images en cours d'exécution dans le cluster
```bash
kubectl get pods -A -o jsonpath='{range .items[*]}{.spec.containers[*].image}{"\n"}{end}' | tr ' ' '\n' | sort | uniq -c
```

### Quel nœud exécute quel pod
```bash
kubectl get pods -o wide --sort-by=.spec.nodeName
```
