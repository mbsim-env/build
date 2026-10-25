#!/usr/bin/env bash

export LD_LIBRARY_PATH=/opt/rh/httpd24/root/usr/lib64

# if /etc/letsencrypt is not mounted then SSL is disabled -> skip certbot update
if [ ! -d /etc/letsencrypt/live/mbsim-env ]; then
  exit 0
fi

python3 -c "import time; import random; time.sleep(random.randint(0,24*60*60-100))"

echo "RUN certbot **************************************************************************************" \
2> >(sed -re "s/^/CERTBOT: /" > /proc/1/fd/2) > >(sed -re "s/^/CERTBOT: /" > /proc/1/fd/1)
date \
2> >(sed -re "s/^/CERTBOT: /" > /proc/1/fd/2) > >(sed -re "s/^/CERTBOT: /" > /proc/1/fd/1)

/usr/bin/certbot-2 renew --work-dir /tmp/certbotwork --logs-dir /tmp/certbotlog --webroot -w /var/www/html/certbot \
--post-hook \
"/opt/rh/httpd24/root/usr/sbin/httpd -k graceful && echo httpd_reload_OK || echo httpd_reload_FAILED" \
2> >(sed -re "s/^/CERTBOT: /" > /proc/1/fd/2) > >(sed -re "s/^/CERTBOT: /" > /proc/1/fd/1)

chown -R dockeruser:dockeruser /etc/letsencrypt/

echo "CURRENT webserver expiry dates" \
2> >(sed -re "s/^/CERTBOT: /" > /proc/1/fd/2) > >(sed -re "s/^/CERTBOT: /" > /proc/1/fd/1)
echo | openssl s_client -connect www.mbsim-env.de:443 2>/dev/null | openssl x509 -noout -dates \
2> >(sed -re "s/^/CERTBOT: /" > /proc/1/fd/2) > >(sed -re "s/^/CERTBOT: /" > /proc/1/fd/1)
