FROM node:20-alpine AS build

RUN addgroup -S buildgroup && adduser -S builduser -G buildgroup

WORKDIR /app

COPY --chown=builduser:buildgroup package.json package-lock.json ./
RUN npm install

COPY --chown=builduser:buildgroup . .

USER builduser

RUN npm run build

FROM nginxinc/nginx-unprivileged:alpine AS serve

COPY --from=build /app/dist /usr/share/nginx/html

RUN printf 'server {\n\
    listen 8080;\n\
    root /usr/share/nginx/html;\n\
    index index.html;\n\
    location /api/ {\n\
        proxy_pass http://backend:8000;\n\
        proxy_set_header Host $host;\n\
        proxy_set_header X-Real-IP $remote_addr;\n\
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n\
        proxy_read_timeout 120s;\n\
    }\n\
    location / {\n\
        try_files $uri $uri/ /index.html;\n\
    }\n\
}\n' > /etc/nginx/conf.d/default.conf

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
