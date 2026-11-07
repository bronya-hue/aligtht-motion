FROM node:18-slim

# Instal Python 3 dan pip
RUN apt-get update && apt-get install -y python3 python3-pip && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

# Instal dependensi Node.js & Python
RUN npm install
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

EXPOSE 8080

# Jalankan Backend dan Bot bersamaan
CMD ["bash", "-c", "node server.js & python3 bot.py"]
