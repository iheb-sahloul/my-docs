# Linux

## Fichiers et répertoires

### Naviguer et lister
```bash
ls -lah                                        # format long, tout, tailles lisibles
ls -lt | head                                  # les plus récents d'abord
tree -L 2 -a -I node_modules
pwd; cd -                                      # cd - = répertoire précédent
```

### Trouver des fichiers
```bash
find . -name "*.log" -mtime +7                 # plus vieux que 7 jours
find . -type f -size +100M
find . -name "*.tmp" -delete
find . -type f -name "*.java" -exec grep -l "TODO" {} +
find /var -user root -perm -4000 2>/dev/null   # binaires setuid
locate nginx.conf                              # utilise un index préconstruit (updatedb)
```

### Copier, déplacer, lier, supprimer
```bash
cp -a src/ dst/                                # archive : conserve droits/dates/liens symboliques
rsync -avh --progress src/ user@host:/data/    # slash final sur src = contenu uniquement
rsync -avh --delete --dry-run src/ dst/        # prévisualiser un miroir
mv old new
ln -s /opt/app-1.2 /opt/app                    # lien symbolique
rm -rf build/                                  # pas d'annulation, vérifiez bien le chemin
```

### Consulter des fichiers
```bash
less +F app.log                                # suit comme tail -f, Ctrl-C pour parcourir, q pour quitter
tail -f app.log
tail -n 200 app.log | grep ERROR
head -n 20 file
wc -l file
file unknown.bin                               # détecter le type
stat file                                      # taille, droits, horodatages
```

### Archives
```bash
tar czf backup.tgz dir/                        # créer en gzip
tar xzf backup.tgz -C /tmp                     # extraire dans /tmp
tar tf backup.tgz                              # lister seulement
zip -r out.zip dir/ && unzip -l out.zip
gzip -k file                                   # conserver l'original
```

---

## Permissions

### Lire et modifier
```bash
ls -l script.sh
```
```text
-rwxr-xr-- 1 alice dev 1204 Sep 29 10:12 script.sh
```

| Partie | Signification |
|---|---|
| `-` | Type (`-` fichier, `d` dossier, `l` lien) |
| `rwx` | Propriétaire : lecture, écriture, exécution |
| `r-x` | Groupe |
| `r--` | Autres |

| Octal | Symbolique | Usage courant |
|---|---|---|
| `755` | `rwxr-xr-x` | Exécutables, dossiers |
| `644` | `rw-r--r--` | Fichiers ordinaires |
| `600` | `rw-------` | Clés privées, secrets |
| `700` | `rwx------` | Dossiers privés (`~/.ssh`) |

```bash
chmod 755 script.sh
chmod u+x,g-w script.sh
chmod -R g+rX shared/                          # X majuscule : exécution seulement sur les dossiers/fichiers déjà exécutables
chown alice:dev file
chown -R www-data: /var/www
umask                                          # masque par défaut (022 -> fichiers 644, dossiers 755)
```

### Bits spéciaux et ACL
```bash
chmod u+s file                                 # setuid
chmod g+s dir                                  # les nouveaux fichiers héritent du groupe
chmod +t /shared                               # sticky : seul le propriétaire peut supprimer
setfacl -m u:bob:rw file
getfacl file
```

### Utilisateurs et groupes
```bash
id                                             # uid, gid, groupes
whoami
sudo useradd -m -s /bin/bash bob
sudo usermod -aG docker bob                    # ajouter à un groupe (se déconnecter/reconnecter pour appliquer)
sudo passwd bob
sudo -l                                        # que puis-je exécuter avec sudo ?
sudo -u postgres psql
```

---

## Processus

### Inspecter
```bash
ps aux | grep java
ps -ef --forest                                # vue en arbre
ps -o pid,ppid,%cpu,%mem,etime,cmd -p 1234
pgrep -fa java                                 # PID + ligne de commande complète
top                                            # dans top : 1 par CPU, M tri par mémoire, P par CPU, c commande complète
htop
uptime                                         # charge moyenne : 1/5/15 min
```

### Signaux
```bash
kill 1234                                      # SIGTERM : arrêt propre
kill -9 1234                                   # SIGKILL : dernier recours
kill -HUP 1234                                 # de nombreux daemons rechargent leur config
pkill -f "java.*myapp"
killall nginx
```

### Arrière-plan et contrôle des tâches
```bash
long_cmd &                                     # arrière-plan
Ctrl-Z; bg; fg; jobs                           # suspendre, reprendre en arrière/avant-plan, lister
nohup ./run.sh > out.log 2>&1 &                # survit à la déconnexion
disown %1
tmux new -s work                               # session persistante ; Ctrl-b d pour détacher
tmux attach -t work
```

### Que fait un processus ?
```bash
lsof -p 1234                                   # fichiers ouverts
ls -l /proc/1234/fd | wc -l                    # nombre de FD
strace -p 1234 -f -e trace=network             # appels système (nécessite root)
cat /proc/1234/status | grep -E 'VmRSS|Threads'
```

---

## Réseau

### Adresses, routes, DNS
```bash
ip -br addr                                    # liste concise des interfaces
ip route
hostname -I
dig example.com +short
dig @8.8.8.8 example.com MX
nslookup example.com
cat /etc/resolv.conf
```

### Ports en écoute et connexions
```bash
ss -tulpn                                      # TCP+UDP en écoute, avec processus
ss -tn state established '( dport = :443 )'
ss -s                                          # résumé
lsof -i :8080                                  # qui possède ce port ?
```
```text
Netid State  Recv-Q Send-Q Local Address:Port Peer Address:Port Process
tcp   LISTEN 0      4096   0.0.0.0:8080      0.0.0.0:*         users:(("java",pid=1234,fd=9))
```

### Tester la connectivité
```bash
ping -c 4 host
traceroute host                                # ou : mtr host
nc -zv host 5432                               # le port est-il ouvert ?
curl -I https://example.com                    # en-têtes uniquement
curl -sS -o /dev/null -w '%{http_code} %{time_total}s\n' https://example.com
curl -X POST -H 'Content-Type: application/json' -d '{"a":1}' http://localhost:8080/api
curl -v --resolve api.example.com:443:10.0.0.5 https://api.example.com/   # contourner le DNS
wget -c https://example.com/big.iso            # téléchargement reprenable
```

### Pare-feu (coup d'œil rapide)
```bash
sudo ufw status verbose
sudo ufw allow 8080/tcp
sudo iptables -L -n -v
sudo nft list ruleset
```

### Capturer le trafic
```bash
sudo tcpdump -i any port 5432 -nn -c 20
sudo tcpdump -i eth0 host 10.0.0.5 -w cap.pcap # ouvrir dans Wireshark
```

---

## Disque et mémoire

### Espace
```bash
df -h                                          # par système de fichiers
df -i                                          # inodes (inodes pleins = « no space » malgré des octets libres)
du -sh *                                       # taille de chaque élément ici
du -h --max-depth=1 /var | sort -h
ncdu /var                                      # interactif
lsblk -f                                       # périphériques, systèmes de fichiers, points de montage
```

### Trouver ce qui remplit le disque
```bash
du -xh / --max-depth=2 2>/dev/null | sort -rh | head -15
sudo lsof +L1                                  # fichiers supprimés encore ouverts par un processus
journalctl --disk-usage
sudo journalctl --vacuum-size=500M
```

### Mémoire
```bash
free -h
```
```text
               total        used        free      shared  buff/cache   available
Mem:            15Gi       6.1Gi       1.2Gi       300Mi       8.0Gi       9.0Gi
```

Lisez la colonne `available`, pas `free` : le cache est récupérable.

```bash
vmstat 1 5                                     # si/so > 0 = swap en cours
sudo dmesg -T | grep -i -E 'oom|killed process'
```

### Montages
```bash
mount | grep ext4
sudo mount /dev/sdb1 /mnt/data
sudo umount /mnt/data
# ligne de /etc/fstab
UUID=1234-abcd  /mnt/data  ext4  defaults,nofail  0  2
```

---

## systemd

### Gérer les services
```bash
systemctl status nginx
sudo systemctl start|stop|restart|reload nginx
sudo systemctl enable --now nginx              # démarrer maintenant + au boot
sudo systemctl disable nginx
systemctl list-units --type=service --state=running
systemctl --failed
systemctl cat nginx                            # fichier d'unité effectif
sudo systemctl daemon-reload                   # après modification des fichiers d'unité
```

### Logs (journald)
```bash
journalctl -u nginx -f                         # suivre
journalctl -u nginx --since "1 hour ago"
journalctl -u nginx -p err                     # erreurs et pire
journalctl -b                                  # ce boot
journalctl -b -1 -e                            # boot précédent, aller à la fin
journalctl -k                                  # messages du noyau
```

### Une unité de service minimale
```ini
# /etc/systemd/system/myapp.service
[Unit]
Description=My App
After=network-online.target
Wants=network-online.target

[Service]
User=myapp
WorkingDirectory=/opt/myapp
EnvironmentFile=/etc/myapp.env
ExecStart=/usr/bin/java -jar /opt/myapp/app.jar
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl daemon-reload && sudo systemctl enable --now myapp
sudo systemctl edit nginx                      # surcharge drop-in, plus sûr que de modifier l'unité du paquet
```

### Timers et cron
```bash
systemctl list-timers
crontab -e
# m h dom mon dow  commande
0 2 * * *  /opt/backup.sh >> /var/log/backup.log 2>&1
*/5 * * * * curl -fsS https://example.com/ping
```

---

## Outils texte

### grep
```bash
grep -rn "TODO" src/                           # récursif avec numéros de ligne
grep -rniI --include="*.java" "OrderService" .
grep -E 'ERROR|WARN' app.log
grep -v DEBUG app.log                          # inverser
grep -C 3 "Exception" app.log                  # 3 lignes de contexte
grep -c ERROR app.log                          # compter
```

### sed, awk, cut
```bash
sed -i 's/foo/bar/g' file                      # sur place (macOS : sed -i '' ...)
sed -n '10,20p' file                           # affiche les lignes 10 à 20
sed '/^#/d;/^$/d' conf                         # supprime commentaires et lignes vides
awk '{print $1, $NF}' file                     # première et dernière colonne
awk -F: '{print $1}' /etc/passwd               # séparateur personnalisé
awk '$9 >= 500 {c++} END {print c}' access.log # compter les 5xx dans un log nginx
cut -d, -f1,3 data.csv
```

### sort, uniq, xargs, tr
```bash
sort file | uniq -c | sort -rn | head          # lignes les plus répétées
awk '{print $1}' access.log | sort | uniq -c | sort -rn | head   # IP clientes les plus fréquentes
find . -name "*.log" | xargs -P4 gzip          # en parallèle
tr -d '\r' < win.txt > unix.txt
tee out.txt                                    # écrit et laisse passer
```

### JSON
```bash
curl -s https://api.example.com/users | jq '.[] | {id, name}'
jq -r '.items[].metadata.name' pods.json
jq '.[] | select(.age > 30)' users.json
```

### Redirection
```bash
cmd > out.txt                                  # stdout, écrase
cmd >> out.txt                                 # ajoute
cmd 2> err.txt
cmd > all.txt 2>&1                             # les deux dans un fichier
cmd &> all.txt                                 # raccourci bash
cmd > /dev/null 2>&1                           # faire taire
diff <(sort a.txt) <(sort b.txt)               # substitution de processus
```

---

## SSH

### Se connecter et copier
```bash
ssh user@host
ssh -p 2222 -i ~/.ssh/id_ed25519 user@host
ssh user@host 'df -h'                          # exécuter une seule commande
scp file user@host:/tmp/
scp -r user@host:/var/log/app ./logs
```

### Clés
```bash
ssh-keygen -t ed25519 -C "me@example.com"
ssh-copy-id user@host                          # installer la clé publique
eval "$(ssh-agent -s)" && ssh-add ~/.ssh/id_ed25519
chmod 700 ~/.ssh && chmod 600 ~/.ssh/id_ed25519 ~/.ssh/authorized_keys
```

### Tunnels
```bash
ssh -L 5433:db.internal:5432 user@bastion      # local : localhost:5433 -> db.internal:5432
ssh -R 9000:localhost:3000 user@host           # distant : host:9000 -> mon localhost:3000
ssh -D 1080 user@host                          # proxy SOCKS
ssh -N -f -L 5433:db.internal:5432 user@bastion   # sans shell, en arrière-plan
```

### ~/.ssh/config
```text
Host bastion
  HostName bastion.example.com
  User alice
  IdentityFile ~/.ssh/id_ed25519

Host db-*
  ProxyJump bastion
  User alice

Host *
  ServerAliveInterval 30
  AddKeysToAgent yes
```
```bash
ssh db-prod                                    # passe automatiquement par le bastion
ssh -J bastion user@10.0.0.7                   # hôte de rebond ponctuel
```

---

## Astuces shell

### Historique et raccourcis
```bash
!!                                             # répète la dernière commande
sudo !!                                        # ...avec sudo
!$                                             # dernier argument de la commande précédente
Ctrl-R                                         # recherche inversée dans l'historique
Ctrl-A / Ctrl-E                                # début / fin de ligne
Ctrl-W / Ctrl-U                                # supprime un mot / jusqu'au début
```

### Scripts sûrs
```bash
#!/usr/bin/env bash
set -euo pipefail                              # quitte sur erreur, variable non définie, échec de pipe
trap 'echo "failed at line $LINENO"' ERR
```

### Environnement
```bash
env | sort
export JAVA_HOME=/usr/lib/jvm/temurin-21
echo "$PATH" | tr ':' '\n'
which -a java                                  # toutes les correspondances dans le PATH
```

### Informations système
```bash
uname -a
cat /etc/os-release
lscpu | head
nproc
date -u +%FT%TZ
```
