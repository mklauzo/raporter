#!/bin/bash

# Konfiguracja
DATA_RAPORTU=$(date "+%Y-%m-%d %H:%M:%S")
LOG_PATH="/var/log"
VHOSTS_LOG_PATH="/var/www/vhosts/system"
MIESIAC_TEMU=$(date --date='1 month ago' '+%b')

echo "=== RAPORT STANU SERWERA - $DATA_RAPORTU ==="

# 1. Metryka serwera
echo -e "\n1. Metryka serwera:"
echo "IP: $(hostname -I | awk '{print $1}')"
echo "Hostname: $(hostnamectl --static 2>/dev/null || hostname)"
echo "System: $(hostnamectl 2>/dev/null | grep 'Operating System' | sed 's/.*: //')"
echo "Kernel: $(hostnamectl 2>/dev/null | grep 'Kernel' | sed 's/.*: //')"
VENDOR=$(hostnamectl 2>/dev/null | grep 'Hardware Vendor' | sed 's/.*: //')
echo "Vendor: $VENDOR"
if [ "$VENDOR" != "QEMU" ]; then
    echo "Model: $(hostnamectl 2>/dev/null | grep 'Hardware Model' | sed 's/.*: //')"
fi

# 2. Wersja Plesk
echo -e "\n2. Plesk Version:"
plesk -v | grep "Product version"

# 3. Dysk
echo -e "\n3. Zużycie dysku:"
df -h | grep '^/dev/' | awk '{ print $5 " (" $1 ")" }'

# 4. Load Average & Uptime
echo -e "\n4. Obciążenie i Uptime:"
uptime

# 5. Kolejka poczty
echo -e "\n5. Kolejka poczty (Postfix):"
mailq | tail -n 1

# 6. Aktualizacje pakietów
echo -e "\n6. Pakiety do aktualizacji:"
UPDATES=$(apt list --upgradable 2>/dev/null | grep -v "Listing..." | wc -l)
if [ "$UPDATES" -gt 0 ]; then echo "$UPDATES pakietów do aktualizacji"; else echo "Brak aktualizacji"; fi

# 7. ANALIZA LOGÓW (Ostatni miesiąc)
echo -e "\n7. ANALIZA POTENCJALNYCH PROBLEMÓW (LOGI):"

# --- Logi systemowe ---
echo "--- Błędy w logach systemowych (/var/log/syslog) ---"
SYS_ERRORS=$(grep -Ei "error|critical|fatal" $LOG_PATH/syslog 2>/dev/null | grep "$MIESIAC_TEMU" | tail -n 10)
if [ -z "$SYS_ERRORS" ]; then echo "BRAK BŁĘDÓW"; else echo "$SYS_ERRORS"; fi

# --- Logi Webowe (vhosts) ---
echo -e "\n--- Błędy w logach Webowych (vhosts) ---"
WEB_ERRORS=$(find $VHOSTS_LOG_PATH -name "error_log" -mtime -30 -exec grep -HiE "fatal|error" {} \; 2>/dev/null | tail -n 20)
if [ -z "$WEB_ERRORS" ]; then echo "BRAK BŁĘDÓW"; else echo "$WEB_ERRORS"; fi

# --- Problemy z bazą danych (MySQL) ---
echo -e "\n--- Problemy z bazą danych (MySQL) ---"
DB_ERRORS=$(tail -n 20 /var/log/mysql/error.log 2>/dev/null | grep -Ei "error|locked|crash")
if [ -z "$DB_ERRORS" ]; then echo "BRAK BŁĘDÓW"; else echo "$DB_ERRORS"; fi

# 8. Bezpieczeństwo
echo -e "\n8. Bezpieczeństwo (Firewall & Fail2Ban):"

# --- Sprawdzenie Plesk Firewall (Komenda Extension) ---
echo -n "Plesk Firewall Status: "
if plesk ext firewall --is-enabled >/dev/null 2>&1; then
    echo "WŁĄCZONY (OK)"
else
    echo "UWAGA: WYŁĄCZONY LUB BRAK MODUŁU!"
fi

# --- Lista filtrów Fail2Ban ---
echo "Lista aktywnych filtrów Fail2Ban (włączone filtry):"
JAILS=$(fail2ban-client status | grep "Jail list" | sed 's/.*Jail list://' | sed 's/,//g')

if [ -z "$JAILS" ]; then
    echo "Brak aktywnych filtrów (Fail2Ban może być wyłączony)."
else
    for jail in $JAILS; do
        BANNED=$(fail2ban-client status "$jail" | grep "Currently banned" | awk '{print $4}')
        echo "  - [ $jail ]: zablokowanych IP: $BANNED"
    done
fi

# 9. ClamAV - Antywirus
CLAMSCAN_RUNNING=$(pgrep -f "clamscan" 2>/dev/null)
if [ -n "$CLAMSCAN_RUNNING" ]; then
    echo -e "\n9. ClamAV - Antywirus:"
    echo "Status: Skanowanie w toku (PID: $CLAMSCAN_RUNNING)"

    # Wyświetl poprzednie podsumowanie jeśli istnieje
    if [ -f "/root/wynik_antywirusa" ]; then
        echo "Poprzednie wyniki skanowania:"
        sed -n '/----------- SCAN SUMMARY -----------/,$p' /root/wynik_antywirusa
    else
        echo "Brak poprzednich wyników skanowania."
    fi

    # Uruchom ponowne skanowanie w tle (screen)
    if command -v screen &>/dev/null; then
        screen -dmS clamscan_session bash -c "clamscan --infected --recursive --remove / > /root/wynik_antywirusa 2>&1"
        echo "Uruchomiono nowe skanowanie w screen (sesja: clamscan_session)"
    else
        nohup bash -c "clamscan --infected --recursive --remove / > /root/wynik_antywirusa 2>&1" &>/dev/null &
        echo "Uruchomiono nowe skanowanie w tle (nohup)"
    fi
fi
