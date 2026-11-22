# Multi-stage build for React Dashboard
FROM node:20-alpine AS builder

WORKDIR /app

COPY chat-ui/package*.json ./
RUN npm install

COPY chat-ui/ ./
RUN npm run build

# Serve with lightweight web server
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY chat-ui/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
