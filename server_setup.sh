#!/bin/bash

# Set HOME environment variable
export HOME=/home/ubuntu

# Install Ollama
echo "### Install Ollama"
curl -fsSL https://ollama.com/install.sh | sh

# Update package lists
echo "### Update package lists"
apt-get update

# Start Ollama service
echo "### Start Ollama service"
systemctl start ollama.service

# Wait for 30 seconds
sleep 30

# Configure Ollama service
echo "### Configure Ollama service"
mkdir -p /etc/systemd/system/ollama.service.d
cat <<EOF > /etc/systemd/system/ollama.service.d/override.conf
[Service]
Environment=OLLAMA_HOST=127.0.0.1:11434
EOF

# Reload and restart Ollama service
echo "### Reload and restart Ollama service"
systemctl daemon-reexec
systemctl daemon-reload
systemctl restart ollama.service

# Wait for another 30 seconds
sleep 30

# Pull models
echo "### Pull models"
models=("qwen3:30b-a3b" "gemma3:27b" "llama4")
for model in "${models[@]}"; do
  ollama pull "$model"
done