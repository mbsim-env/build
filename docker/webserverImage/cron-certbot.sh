#!/usr/bin/env bash

# if /etc/letsencrypt is not mounted then SSL is disabled -> skip certbot update
if [ ! -d /etc/letsencrypt/live/mbsim-env ]; then
  exit 0
fi

python3 -c "import time; import random; time.sleep(random.randint(0,24*60*60-100))"

/usr/bin/certbot-2 renew --work-dir /tmp/certbotwork --logs-dir /tmp/certbotlog --webroot \
-w /var/www/html/certbot --post-hook "/opt/rh/httpd24/root/usr/sbin/httpd -k graceful" \
2> >(sed -re "s/^/CERTBOT: /" > /proc/1/fd/2) > >(sed -re "s/^/CERTBOT: /" > /proc/1/fd/1)

chown -R dockeruser:dockeruser /etc/letsencrypt/
