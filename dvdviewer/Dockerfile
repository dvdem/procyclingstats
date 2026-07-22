FROM nginx:alpine

# Copiar la configuración personalizada de nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copiar los archivos estáticos de la aplicación
COPY index.html /usr/share/nginx/html/
COPY style.css /usr/share/nginx/html/
COPY script.js /usr/share/nginx/html/
COPY stages.json /usr/share/nginx/html/
COPY climbs.json /usr/share/nginx/html/
COPY gpx /usr/share/nginx/html/gpx/

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
