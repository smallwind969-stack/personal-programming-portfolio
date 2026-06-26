FROM node:22-alpine

WORKDIR /app/apps/web

COPY apps/web/package.json ./package.json
RUN npm install

COPY apps/web ./

EXPOSE 3000

CMD ["sh", "-c", "npm run dev -- -p ${WEB_PORT:-3000}"]
