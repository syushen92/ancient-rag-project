FROM node:22-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 5173

# 啟動 Vite 開發伺服器，並綁定 0.0.0.0 使其能被容器外訪問
CMD ["npm", "run", "dev", "--", "--host"]
