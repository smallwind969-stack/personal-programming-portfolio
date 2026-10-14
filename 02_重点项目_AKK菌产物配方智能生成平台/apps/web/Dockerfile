FROM node:22-alpine

WORKDIR /app/apps/web

COPY apps/web/package.json ./package.json
RUN npm install

COPY apps/web ./
RUN npm run build

EXPOSE 3000

CMD ["sh", "-c", "npm run start -- -p ${WEB_PORT:-3000}"]
