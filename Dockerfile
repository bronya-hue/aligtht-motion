# Gunakan Node.js sebagai base image
FROM node:18-slim

# Instal Python 3 dan pip
RUN apt-get update && apt-get install -y python3 python3-pip && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy semua file
COPY . .

# Instal dependensi Node.js
RUN npm install

# Instal dependensi Python
RUN pip3 install --no-cache-dir -r requirements.txt

# Expose port 8080
EXPOSE 8080

# Jalankan Backend (Node) di background, lalu jalankan Bot (Python) di foreground
CMD ["bash", "-c", "node server.js & python3 bot.py"]
