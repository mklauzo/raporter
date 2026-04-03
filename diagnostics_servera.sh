#!/bin/bash
# Skrypt diagnostyczny - wyłącznie odczyt, bez modyfikacji serwera

echo "=== DIAGNOSTYKA ZAAWANSOWANA ==="
echo "Data: $(date '+%Y-%m-%d %H:%M:%S')"

# ── System ────────────────────────────────────────────────────────────────────
echo -e "\n--- SYSTEM ---"
uname -r
cat /etc/os-release 2>/dev/null | grep -E "^(NAME|VERSION|VERSION_ID)="
lsb_release -a 2>/dev/null
free -h 2>/dev/null
df -h 2>/dev/null
df -i 2>/dev/null
ulimit -n 2>/dev/null && echo "open files limit: $(ulimit -n)"

# ── Pakiety do aktualizacji (pełna lista) ─────────────────────────────────────
echo -e "\n--- PAKIETY DO AKTUALIZACJI (pelna lista) ---"
apt list --upgradable 2>/dev/null | grep -v "^Listing"

# ── SSH ───────────────────────────────────────────────────────────────────────
echo -e "\n--- KONFIGURACJA SSH ---"
sshd -T 2>/dev/null | grep -E "^(port|permitrootlogin|passwordauthentication|maxauthtries|logingracetime|clientaliveinterval|allowusers|allowgroups|protocol)"

# ── Otwarte porty ────────────────────────────────────────────────────────────
echo -e "\n--- OTWARTE PORTY (ss) ---"
ss -tlnp 2>/dev/null

# ── Użytkownicy ──────────────────────────────────────────────────────────────
echo -e "\n--- UZYTKOWNICY Z UID=0 ---"
awk -F: '($3==0){print $1}' /etc/passwd 2>/dev/null

echo -e "\n--- UZYTKOWNICY W GRUPIE sudo/wheel ---"
getent group sudo wheel 2>/dev/null

echo -e "\n--- KONTA BEZ HASLA ---"
awk -F: '($2=="" || $2=="!"){print $1}' /etc/shadow 2>/dev/null

# ── PHP ───────────────────────────────────────────────────────────────────────
echo -e "\n--- PHP ---"
php -v 2>/dev/null
php -i 2>/dev/null | grep -E "^(expose_php|display_errors|log_errors|allow_url_fopen|allow_url_include|disable_functions|memory_limit|max_execution_time|upload_max_filesize|post_max_size|open_basedir|session\.cookie_secure|session\.cookie_httponly|session\.cookie_samesite|opcache\.enable|opcache\.memory_consumption) =>"
php-fpm7.4 -t 2>/dev/null; php-fpm8.0 -t 2>/dev/null; php-fpm8.1 -t 2>/dev/null; php-fpm8.2 -t 2>/dev/null; php-fpm8.3 -t 2>/dev/null

# ── Apache ───────────────────────────────────────────────────────────────────
echo -e "\n--- APACHE ---"
apache2 -v 2>/dev/null || httpd -v 2>/dev/null
apachectl -M 2>/dev/null | grep -iE "security|headers|evasive"

# ── Nginx ────────────────────────────────────────────────────────────────────
echo -e "\n--- NGINX ---"
nginx -v 2>/dev/null

# ── MySQL / MariaDB ───────────────────────────────────────────────────────────
echo -e "\n--- MYSQL/MARIADB ---"
mysql --version 2>/dev/null
mysqladmin --defaults-extra-file=/etc/mysql/debian.cnf variables 2>/dev/null | grep -E "bind_address|skip_networking|slow_query_log|general_log|innodb_buffer_pool_size|max_connections|validate_password|default_authentication_plugin|query_cache_size"
cat /etc/mysql/mysql.conf.d/mysqld.cnf 2>/dev/null | grep -E "^(bind-address|skip-networking|slow_query_log|general_log|max_connections)"

# ── Redis ─────────────────────────────────────────────────────────────────────
echo -e "\n--- REDIS ---"
redis-cli --version 2>/dev/null
redis-cli info server 2>/dev/null | grep -E "redis_version|os|tcp_port"
redis-cli config get bind 2>/dev/null
redis-cli config get requirepass 2>/dev/null
redis-cli config get protected-mode 2>/dev/null
redis-cli config get maxmemory 2>/dev/null

# ── Docker ───────────────────────────────────────────────────────────────────
echo -e "\n--- DOCKER ---"
docker version 2>/dev/null | grep -E "Version|API version" | head -6
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null
docker info 2>/dev/null | grep -E "Server Version|Storage Driver|Security Options|Logging Driver"

# ── Let's Encrypt / certbot ───────────────────────────────────────────────────
echo -e "\n--- CERTYFIKATY SSL (certbot) ---"
certbot certificates 2>/dev/null

# ── AppArmor / SELinux ────────────────────────────────────────────────────────
echo -e "\n--- APPARMOR/SELINUX ---"
aa-status 2>/dev/null | head -5
getenforce 2>/dev/null

# ── Cron ─────────────────────────────────────────────────────────────────────
echo -e "\n--- CRON (root) ---"
crontab -l 2>/dev/null
ls -la /etc/cron.d/ 2>/dev/null
ls -la /etc/cron.daily/ /etc/cron.weekly/ /etc/cron.monthly/ 2>/dev/null

# ── Usługi systemd ────────────────────────────────────────────────────────────
echo -e "\n--- USLUGI SYSTEMD (uruchomione) ---"
systemctl list-units --type=service --state=running --no-pager 2>/dev/null | head -40

# ── Ostatnie logowania ────────────────────────────────────────────────────────
echo -e "\n--- OSTATNIE LOGOWANIA ---"
last -n 20 2>/dev/null

# ── Auth log (brute force) ────────────────────────────────────────────────────
echo -e "\n--- AUTH LOG (nieudane logowania, ostatnie 50) ---"
grep -E "Failed password|Invalid user|authentication failure" /var/log/auth.log 2>/dev/null | tail -50

# ── sysctl (parametry bezpieczenstwa) ────────────────────────────────────────
echo -e "\n--- SYSCTL (bezpieczenstwo) ---"
sysctl net.ipv4.tcp_syncookies net.ipv4.ip_forward kernel.dmesg_restrict kernel.randomize_va_space 2>/dev/null

# ── Plesk ─────────────────────────────────────────────────────────────────────
echo -e "\n--- PLESK ---"
plesk version 2>/dev/null
plesk bin spamassassin --status 2>/dev/null
plesk ext modsecurity --status 2>/dev/null

echo -e "\n=== KONIEC DIAGNOSTYKI ==="
