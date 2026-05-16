FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install --silent

COPY . .
# Copy frontend build for SPA fallback serving
# No COPY of frontend build - using volume mount instead
# This line will be removed since we use volume in docker-compose.yml

EXPOSE 3001

CMD ["node", "index.js"]
