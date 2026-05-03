FROM node:20-alpine AS build

RUN addgroup -S buildgroup && adduser -S builduser -G buildgroup

WORKDIR /app
RUN chown -R builduser:buildgroup /app

USER builduser

COPY --chown=builduser:buildgroup package.json package-lock.json ./
RUN npm ci

COPY --chown=builduser:buildgroup . .

RUN npm run build

FROM nginxinc/nginx-unprivileged:alpine AS serve

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
