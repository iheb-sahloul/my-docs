# Linux

## Files and directories

### Navigate and list

```bash
ls -lah                                        # long, all, human sizes
ls -lt | head                                  # newest first
tree -L 2 -a -I node_modules
pwd; cd -                                      # cd - = previous directory
```

### Find files

```bash
find . -name "*.log" -mtime +7                 # older than 7 days
find . -type f -size +100M
find . -name "*.tmp" -delete
find . -type f -name "*.java" -exec grep -l "TODO" {} +
find /var -user root -perm -4000 2>/dev/null   # setuid binaries
locate nginx.conf                              # uses a prebuilt index (updatedb)
```

### Copy, move, link, remove

```bash
cp -a src/ dst/                                # archive: keep perms/times/symlinks
rsync -avh --progress src/ user@host:/data/    # trailing slash on src = contents only
rsync -avh --delete --dry-run src/ dst/        # preview a mirror
mv old new
ln -s /opt/app-1.2 /opt/app                    # symlink
rm -rf build/                                  # no undo, double-check the path
```

### View files

```bash
less +F app.log                                # follow like tail -f, Ctrl-C to browse, q to quit
tail -f app.log
tail -n 200 app.log | grep ERROR
head -n 20 file
wc -l file
file unknown.bin                               # detect type
stat file                                      # size, perms, timestamps
```

### Archives

```bash
tar czf backup.tgz dir/                        # create gzip
tar xzf backup.tgz -C /tmp                     # extract into /tmp
tar tf backup.tgz                              # list only
zip -r out.zip dir/ && unzip -l out.zip
gzip -k file                                   # keep original
```

---

## Permissions

### Read and change

```bash
ls -l script.sh
```

```text
-rwxr-xr-- 1 alice dev 1204 Sep 29 10:12 script.sh
```

| Part | Meaning |
|---|---|
| `-` | Type (`-` file, `d` dir, `l` link) |
| `rwx` | Owner: read, write, execute |
| `r-x` | Group |
| `r--` | Others |

| Octal | Symbolic | Common use |
|---|---|---|
| `755` | `rwxr-xr-x` | Executables, directories |
| `644` | `rw-r--r--` | Regular files |
| `600` | `rw-------` | Private keys, secrets |
| `700` | `rwx------` | Private directories (`~/.ssh`) |

```bash
chmod 755 script.sh
chmod u+x,g-w script.sh
chmod -R g+rX shared/                          # capital X: exec only on dirs/already-executable files
chown alice:dev file
chown -R www-data: /var/www
umask                                          # default mask (022 -> files 644, dirs 755)
```

### Special bits and ACLs

```bash
chmod u+s file                                 # setuid
chmod g+s dir                                  # new files inherit group
chmod +t /shared                               # sticky: only owner can delete
setfacl -m u:bob:rw file
getfacl file
```

### Users and groups

```bash
id                                             # uid, gid, groups
whoami
sudo useradd -m -s /bin/bash bob
sudo usermod -aG docker bob                    # add to group (log out/in to apply)
sudo passwd bob
sudo -l                                        # what can I run with sudo?
sudo -u postgres psql
```

---

## Processes

### Inspect

```bash
ps aux | grep java
ps -ef --forest                                # tree view
ps -o pid,ppid,%cpu,%mem,etime,cmd -p 1234
pgrep -fa java                                 # PID + full command line
top                                            # in top: 1 per-CPU, M sort by mem, P by cpu, c full cmd
htop
uptime                                         # load average: 1/5/15 min
```

### Signals

```bash
kill 1234                                      # SIGTERM: graceful
kill -9 1234                                   # SIGKILL: last resort
kill -HUP 1234                                 # many daemons reload config
pkill -f "java.*myapp"
killall nginx
```

### Background and job control

```bash
long_cmd &                                     # background
Ctrl-Z; bg; fg; jobs                           # suspend, resume in bg/fg, list
nohup ./run.sh > out.log 2>&1 &                # survive logout
disown %1
tmux new -s work                               # persistent session; Ctrl-b d detach
tmux attach -t work
```

### What is a process doing?

```bash
lsof -p 1234                                   # open files
ls -l /proc/1234/fd | wc -l                    # FD count
strace -p 1234 -f -e trace=network             # syscalls (needs root)
cat /proc/1234/status | grep -E 'VmRSS|Threads'
```

---

## Network

### Addresses, routes, DNS

```bash
ip -br addr                                    # brief interface list
ip route
hostname -I
dig example.com +short
dig @8.8.8.8 example.com MX
nslookup example.com
cat /etc/resolv.conf
```

### Listening ports and connections

```bash
ss -tulpn                                      # TCP+UDP listening, with process
ss -tn state established '( dport = :443 )'
ss -s                                          # summary
lsof -i :8080                                  # who owns this port?
```

```text
Netid State  Recv-Q Send-Q Local Address:Port Peer Address:Port Process
tcp   LISTEN 0      4096   0.0.0.0:8080      0.0.0.0:*         users:(("java",pid=1234,fd=9))
```

### Test connectivity

```bash
ping -c 4 host
traceroute host                                # or: mtr host
nc -zv host 5432                               # is the port open?
curl -I https://example.com                    # headers only
curl -sS -o /dev/null -w '%{http_code} %{time_total}s\n' https://example.com
curl -X POST -H 'Content-Type: application/json' -d '{"a":1}' http://localhost:8080/api
curl -v --resolve api.example.com:443:10.0.0.5 https://api.example.com/   # bypass DNS
wget -c https://example.com/big.iso            # resumable download
```

### Firewall (quick look)

```bash
sudo ufw status verbose
sudo ufw allow 8080/tcp
sudo iptables -L -n -v
sudo nft list ruleset
```

### Capture traffic

```bash
sudo tcpdump -i any port 5432 -nn -c 20
sudo tcpdump -i eth0 host 10.0.0.5 -w cap.pcap # open in Wireshark
```

---

## Disk and memory

### Space

```bash
df -h                                          # per filesystem
df -i                                          # inodes (full inodes = "no space" with free bytes)
du -sh *                                       # size of each item here
du -h --max-depth=1 /var | sort -h
ncdu /var                                      # interactive
lsblk -f                                       # devices, filesystems, mountpoints
```

### Find what fills the disk

```bash
du -xh / --max-depth=2 2>/dev/null | sort -rh | head -15
sudo lsof +L1                                  # deleted files still held open by a process
journalctl --disk-usage
sudo journalctl --vacuum-size=500M
```

### Memory

```bash
free -h
```

```text
               total        used        free      shared  buff/cache   available
Mem:            15Gi       6.1Gi       1.2Gi       300Mi       8.0Gi       9.0Gi
```

Read the `available` column, not `free`: cache is reclaimable.

```bash
vmstat 1 5                                     # si/so > 0 = swapping
sudo dmesg -T | grep -i -E 'oom|killed process'
```

### Mounts

```bash
mount | grep ext4
sudo mount /dev/sdb1 /mnt/data
sudo umount /mnt/data
# /etc/fstab line
UUID=1234-abcd  /mnt/data  ext4  defaults,nofail  0  2
```

---

## systemd

### Manage services

```bash
systemctl status nginx
sudo systemctl start|stop|restart|reload nginx
sudo systemctl enable --now nginx              # start now + at boot
sudo systemctl disable nginx
systemctl list-units --type=service --state=running
systemctl --failed
systemctl cat nginx                            # effective unit file
sudo systemctl daemon-reload                   # after editing unit files
```

### Logs (journald)

```bash
journalctl -u nginx -f                         # follow
journalctl -u nginx --since "1 hour ago"
journalctl -u nginx -p err                     # errors and worse
journalctl -b                                  # this boot
journalctl -b -1 -e                            # previous boot, jump to end
journalctl -k                                  # kernel messages
```

### A minimal service unit

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
sudo systemctl edit nginx                      # drop-in override, safer than editing the packaged unit
```

### Timers and cron

```bash
systemctl list-timers
crontab -e
# m h dom mon dow  command
0 2 * * *  /opt/backup.sh >> /var/log/backup.log 2>&1
*/5 * * * * curl -fsS https://example.com/ping
```

---

## Text tools

### grep

```bash
grep -rn "TODO" src/                           # recursive with line numbers
grep -rniI --include="*.java" "OrderService" .
grep -E 'ERROR|WARN' app.log
grep -v DEBUG app.log                          # invert
grep -C 3 "Exception" app.log                  # 3 lines of context
grep -c ERROR app.log                          # count
```

### sed, awk, cut

```bash
sed -i 's/foo/bar/g' file                      # in place (macOS: sed -i '' ...)
sed -n '10,20p' file                           # print lines 10-20
sed '/^#/d;/^$/d' conf                         # drop comments and blank lines
awk '{print $1, $NF}' file                     # first and last column
awk -F: '{print $1}' /etc/passwd               # custom separator
awk '$9 >= 500 {c++} END {print c}' access.log # count 5xx in an nginx log
cut -d, -f1,3 data.csv
```

### sort, uniq, xargs, tr

```bash
sort file | uniq -c | sort -rn | head          # top repeated lines
awk '{print $1}' access.log | sort | uniq -c | sort -rn | head   # top client IPs
find . -name "*.log" | xargs -P4 gzip          # parallel
tr -d '\r' < win.txt > unix.txt
tee out.txt                                    # write and pass through
```

### JSON

```bash
curl -s https://api.example.com/users | jq '.[] | {id, name}'
jq -r '.items[].metadata.name' pods.json
jq '.[] | select(.age > 30)' users.json
```

### Redirection

```bash
cmd > out.txt                                  # stdout, overwrite
cmd >> out.txt                                 # append
cmd 2> err.txt
cmd > all.txt 2>&1                             # both to one file
cmd &> all.txt                                 # bash shorthand
cmd > /dev/null 2>&1                           # silence
diff <(sort a.txt) <(sort b.txt)               # process substitution
```

---

## SSH

### Connect and copy

```bash
ssh user@host
ssh -p 2222 -i ~/.ssh/id_ed25519 user@host
ssh user@host 'df -h'                          # run one command
scp file user@host:/tmp/
scp -r user@host:/var/log/app ./logs
```

### Keys

```bash
ssh-keygen -t ed25519 -C "me@example.com"
ssh-copy-id user@host                          # install public key
eval "$(ssh-agent -s)" && ssh-add ~/.ssh/id_ed25519
chmod 700 ~/.ssh && chmod 600 ~/.ssh/id_ed25519 ~/.ssh/authorized_keys
```

### Tunnels

```bash
ssh -L 5433:db.internal:5432 user@bastion      # local: localhost:5433 -> db.internal:5432
ssh -R 9000:localhost:3000 user@host           # remote: host:9000 -> my localhost:3000
ssh -D 1080 user@host                          # SOCKS proxy
ssh -N -f -L 5433:db.internal:5432 user@bastion   # no shell, background
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
ssh db-prod                                    # goes through bastion automatically
ssh -J bastion user@10.0.0.7                   # one-off jump host
```

---

## Shell tips

### History and shortcuts

```bash
!!                                             # repeat last command
sudo !!                                        # ...with sudo
!$                                             # last argument of previous command
Ctrl-R                                         # reverse search history
Ctrl-A / Ctrl-E                                # start / end of line
Ctrl-W / Ctrl-U                                # delete word / to start
```

### Safe scripts

```bash
#!/usr/bin/env bash
set -euo pipefail                              # exit on error, unset var, pipe failure
trap 'echo "failed at line $LINENO"' ERR
```

### Environment

```bash
env | sort
export JAVA_HOME=/usr/lib/jvm/temurin-21
echo "$PATH" | tr ':' '\n'
which -a java                                  # all matches on PATH
```

### System info

```bash
uname -a
cat /etc/os-release
lscpu | head
nproc
date -u +%FT%TZ
```
