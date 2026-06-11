FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html casa-ep-3d-tour.html /usr/share/nginx/html/
COPY vendor /usr/share/nginx/html/vendor
EXPOSE 8080
