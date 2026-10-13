# HTTP: curl & jq

## curl

### Requests

```bash
curl https://api.example.com/orders/42                       # GET
curl -i https://api.example.com/orders/42                    # include response headers
curl -sS -o /dev/null -w '%{http_code}\n' https://api.example.com/health   # status code only
curl -X POST https://api.example.com/orders \
  -H 'Content-Type: application/json' \
  -d '{"customerId": 7, "items": [{"sku": "A1", "qty": 2}]}'
curl -X POST https://api.example.com/orders -H 'Content-Type: application/json' -d @order.json
curl --json '{"status":"PAID"}' -X PATCH https://api.example.com/orders/42      # curl ≥ 7.82: sets both JSON headers
curl -G https://api.example.com/orders --data-urlencode 'q=status:PAID & total>100' -d page=2
curl -F file=@invoice.pdf -F type=INVOICE https://api.example.com/uploads      # multipart upload
```

### Auth

```bash
curl -H "Authorization: Bearer $TOKEN" https://api.example.com/me
curl -u user:pass https://api.example.com/admin                                # basic auth
TOKEN=$(curl -sS -X POST https://idp.example.com/oauth2/token \
  -d grant_type=client_credentials -d client_id=$ID -d client_secret=$SECRET | jq -r .access_token)
curl -c cookies.txt -b cookies.txt -X POST https://app.example.com/login -d 'user=a&pass=b'   # keep session cookies
```

### Debugging

```bash
curl -v https://api.example.com/orders                       # request/response headers, TLS handshake
curl -sS -o /dev/null -w 'dns %{time_namelookup}s  connect %{time_connect}s  tls %{time_appconnect}s  ttfb %{time_starttransfer}s  total %{time_total}s\n' https://api.example.com/orders
curl -H 'Origin: https://app.example.com' -X OPTIONS \
  -H 'Access-Control-Request-Method: POST' -i https://api.example.com/orders     # test a CORS preflight
curl --resolve api.example.com:443:10.0.3.17 https://api.example.com/health    # hit one specific backend IP
curl -k https://localhost:8443/health                        # ignore TLS errors (local only)
curl -L https://example.com                                  # follow redirects
curl --retry 5 --retry-delay 2 --retry-all-errors --max-time 10 https://api.example.com/health
curl -N https://api.example.com/orders/42/events             # stream SSE without buffering
```

### From inside a pod

```bash
kubectl run tmp --rm -it --image=curlimages/curl --restart=Never -- \
  curl -sS http://orders.default.svc.cluster.local:8080/actuator/health
kubectl port-forward svc/orders 8080:8080          # in another terminal: curl localhost:8080/actuator/health
```

## jq

### Read

```bash
curl -sS .../orders | jq .                                   # pretty-print
jq '.items[0]' orders.json                                   # first element
jq -r '.items[].id' orders.json                              # raw values, one per line
jq '.items | length' orders.json
jq '.items[] | {id, total, customer: .customer.name}' orders.json   # reshape
jq -r '.items[] | [.id, .status, .total] | @csv' orders.json        # to CSV (@tsv also works)
jq 'keys' order.json                                         # field names
jq '.. | .traceId? // empty' log.json                       # find a key anywhere
```

### Filter & aggregate

```bash
jq '.items[] | select(.status == "PAID" and .total > 100)' orders.json
jq '[.items[] | select(.status == "FAILED")] | length' orders.json
jq '[.items[].total] | add' orders.json                      # sum
jq 'group_by(.status) | map({status: .[0].status, count: length})' orders.json
jq 'sort_by(.createdAt) | reverse | .[0:5]' orders.json      # 5 most recent
jq 'map(select(.email | test("@example\\.com$")))' users.json
```

### Build & modify

```bash
jq -n --arg id "$ID" --argjson qty 2 '{orderId: $id, qty: $qty}'      # build JSON safely from shell vars
jq '.status = "CANCELLED" | del(.internalNotes)' order.json
jq '.items |= map(.price *= 1.2)' order.json
```

### Structured logs

```bash
kubectl logs deploy/orders --since=15m | jq -c 'select(.level == "ERROR") | {ts: .["@timestamp"], msg: .message, trace: .traceId}'
kubectl logs deploy/orders --since=1h | jq -r 'select(.level=="ERROR") | .message' | sort | uniq -c | sort -rn | head
kubectl logs deploy/orders | jq -R 'fromjson? // empty'      # skip non-JSON lines
```

### Decode a JWT payload (debugging only, no signature check)

```bash
jq -R 'split(".")[1] | gsub("-";"+") | gsub("_";"/") | @base64d | fromjson' <<< "$TOKEN"
```
