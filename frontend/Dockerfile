# Stage 1: Build the Angular app using Node
FROM node:20-alpine AS build
WORKDIR /app

# Copy package files and install dependencies (using legacy peer deps for your setup)
COPY package*.json ./
RUN npm install --legacy-peer-deps

# Copy the source code and build for production
COPY . .
RUN npm run build --configuration=production

# Stage 2: Serve the compiled app via highly-performant NGINX
FROM nginx:alpine

# Angular 17+ outputs to dist/<project-name>/browser
COPY --from=build /app/dist/frontend/browser /usr/share/nginx/html

# Expose HTTP port
EXPOSE 80

# Start NGINX
CMD ["nginx", "-g", "daemon off;"]
