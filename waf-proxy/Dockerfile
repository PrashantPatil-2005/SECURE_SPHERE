FROM openresty/openresty:1.25.3.1-0-alpine-fat

RUN apk add --no-cache bash curl ca-certificates tzdata openssl

RUN mkdir -p /var/log/waf /etc/waf/conf.d /usr/local/openresty/nginx/lua \
 && chown -R nobody:nobody /var/log/waf /etc/waf

COPY nginx.conf /usr/local/openresty/nginx/conf/nginx.conf
COPY conf.d/ /etc/waf/conf.d/
COPY lua/ /usr/local/openresty/nginx/lua/
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 8080 8443

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["openresty", "-g", "daemon off;"]
