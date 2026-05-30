FROM node:20-alpine

WORKDIR /app

# Copy all source files
COPY . .

# Install backend dependencies
RUN npm install --production

# Install frontend dependencies and build
WORKDIR /app/frontend
RUN npm install
RUN npx vite build

# Back to root
WORKDIR /app

# Seed initial data
RUN node seed-data.js

# Expose port
EXPOSE 3001

# Start server
CMD ["node", "server.js"]
