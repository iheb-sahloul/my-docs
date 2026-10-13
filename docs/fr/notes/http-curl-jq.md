# HTTP: curl & jq

## curl

### Requêtes

```bash
curl https://api.example.com/orders/42                       # GET
curl -i https://api.example.com/orders/42                    # inclure les en-têtes de réponse
curl -sS -o /dev/null -w '%{http_code}\n' https://api.example.com/health   # code de statut seulement
curl -X POST https://api.example.com/orders \
  -H 'Content-Type: application/json' \
  -d '{"customerId": 7, "items": [{"sku": "A1", "qty": 2}]}'
curl -X POST https://api.example.com/orders -H 'Content-Type: application/json' -d @order.json
curl --json '{"status":"PAID"}' -X PATCH https://api.example.com/orders/42      # curl ≥ 7.82 : pose les deux en-têtes JSON
curl -G https://api.example.com/orders --data-urlencode 'q=status:PAID & total>100' -d page=2
curl -F file=@invoice.pdf -F type=INVOICE https://api.example.com/uploads      # upload multipart
```

### Auth

```bash
curl -H "Authorization: Bearer $TOKEN" https://api.example.com/me
curl -u user:pass https://api.example.com/admin                                # authentification basic
TOKEN=$(curl -sS -X POST https://idp.example.com/oauth2/token \
  -d grant_type=client_credentials -d client_id=$ID -d client_secret=$SECRET | jq -r .access_token)
curl -c cookies.txt -b cookies.txt -X POST https://app.example.com/login -d 'user=a&pass=b'   # garder les cookies de session
```

### Débogage

```bash
curl -v https://api.example.com/orders                       # en-têtes requête/réponse, handshake TLS
curl -sS -o /dev/null -w 'dns %{time_namelookup}s  connect %{time_connect}s  tls %{time_appconnect}s  ttfb %{time_starttransfer}s  total %{time_total}s\n' https://api.example.com/orders
curl -H 'Origin: https://app.example.com' -X OPTIONS \
  -H 'Access-Control-Request-Method: POST' -i https://api.example.com/orders     # tester un preflight CORS
curl --resolve api.example.com:443:10.0.3.17 https://api.example.com/health    # viser une IP de backend précise
curl -k https://localhost:8443/health                        # ignorer les erreurs TLS (local uniquement)
curl -L https://example.com                                  # suivre les redirections
curl --retry 5 --retry-delay 2 --retry-all-errors --max-time 10 https://api.example.com/health
curl -N https://api.example.com/orders/42/events             # flux SSE sans mise en tampon
```

### Depuis l'intérieur d'un pod

```bash
kubectl run tmp --rm -it --image=curlimages/curl --restart=Never -- \
  curl -sS http://orders.default.svc.cluster.local:8080/actuator/health
kubectl port-forward svc/orders 8080:8080          # dans un autre terminal : curl localhost:8080/actuator/health
```

## jq

### Lire

```bash
curl -sS .../orders | jq .                                   # pretty-print
jq '.items[0]' orders.json                                   # premier élément
jq -r '.items[].id' orders.json                              # valeurs brutes, une par ligne
jq '.items | length' orders.json
jq '.items[] | {id, total, customer: .customer.name}' orders.json   # remodeler
jq -r '.items[] | [.id, .status, .total] | @csv' orders.json        # en CSV (@tsv fonctionne aussi)
jq 'keys' order.json                                         # noms des champs
jq '.. | .traceId? // empty' log.json                       # trouver une clé n'importe où
```

### Filtrer & agréger

```bash
jq '.items[] | select(.status == "PAID" and .total > 100)' orders.json
jq '[.items[] | select(.status == "FAILED")] | length' orders.json
jq '[.items[].total] | add' orders.json                      # somme
jq 'group_by(.status) | map({status: .[0].status, count: length})' orders.json
jq 'sort_by(.createdAt) | reverse | .[0:5]' orders.json      # les 5 plus récents
jq 'map(select(.email | test("@example\\.com$")))' users.json
```

### Construire & modifier

```bash
jq -n --arg id "$ID" --argjson qty 2 '{orderId: $id, qty: $qty}'      # construire du JSON sûr depuis des variables shell
jq '.status = "CANCELLED" | del(.internalNotes)' order.json
jq '.items |= map(.price *= 1.2)' order.json
```

### Logs structurés

```bash
kubectl logs deploy/orders --since=15m | jq -c 'select(.level == "ERROR") | {ts: .["@timestamp"], msg: .message, trace: .traceId}'
kubectl logs deploy/orders --since=1h | jq -r 'select(.level=="ERROR") | .message' | sort | uniq -c | sort -rn | head
kubectl logs deploy/orders | jq -R 'fromjson? // empty'      # ignorer les lignes non JSON
```

### Décoder le payload d'un JWT (débogage uniquement, sans vérifier la signature)

```bash
jq -R 'split(".")[1] | gsub("-";"+") | gsub("_";"/") | @base64d | fromjson' <<< "$TOKEN"
```
