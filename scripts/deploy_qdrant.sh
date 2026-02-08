#!/bin/bash
# Deploy Qdrant on AWS EC2 or any Linux server

echo "🚀 Deploying Qdrant Vector Database"
echo "===================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "📦 Docker not found. Installing Docker..."
    
    # Update package list
    sudo apt-get update -y
    
    # Install Docker
    sudo apt-get install docker.io -y
    
    # Start Docker service
    sudo systemctl start docker
    sudo systemctl enable docker
    
    # Add current user to docker group
    sudo usermod -aG docker $USER
    
    echo "✅ Docker installed successfully!"
    echo "⚠️  You may need to log out and back in for docker group to take effect"
else
    echo "✅ Docker is already installed"
fi

# Create directory for Qdrant data
echo ""
echo "📁 Creating Qdrant storage directory..."
mkdir -p ~/qdrant_storage

# Stop existing Qdrant container if running
echo ""
echo "🛑 Stopping existing Qdrant container (if any)..."
docker stop qdrant 2>/dev/null || true
docker rm qdrant 2>/dev/null || true

# Pull latest Qdrant image
echo ""
echo "📥 Pulling Qdrant Docker image..."
docker pull qdrant/qdrant:latest

# Run Qdrant container
echo ""
echo "🚀 Starting Qdrant container..."
docker run -d \
  --name qdrant \
  --restart unless-stopped \
  -p 6333:6333 \
  -p 6334:6334 \
  -v ~/qdrant_storage:/qdrant/storage \
  qdrant/qdrant:latest

# Wait for Qdrant to start
echo ""
echo "⏳ Waiting for Qdrant to start..."
sleep 5

# Check if Qdrant is running
if docker ps | grep -q qdrant; then
    echo ""
    echo "✅ Qdrant is running!"
    
    # Get server IP
    SERVER_IP=$(curl -s ifconfig.me)
    
    echo ""
    echo "===================================="
    echo "🎉 Qdrant Deployment Successful!"
    echo "===================================="
    echo ""
    echo "Qdrant is now running at:"
    echo "  Local:    http://localhost:6333"
    echo "  External: http://$SERVER_IP:6333"
    echo ""
    echo "Web UI available at:"
    echo "  Local:    http://localhost:6333/dashboard"
    echo "  External: http://$SERVER_IP:6333/dashboard"
    echo ""
    echo "Storage location: ~/qdrant_storage"
    echo ""
    echo "===================================="
    echo "Next Steps:"
    echo "===================================="
    echo "1. Update your .env file:"
    echo "   VECTOR_STORE=qdrant"
    echo "   QDRANT_URL=http://$SERVER_IP:6333"
    echo "   QDRANT_COLLECTION=rag_documents"
    echo ""
    echo "2. If using AWS EC2, open port 6333 in Security Group:"
    echo "   - Type: Custom TCP"
    echo "   - Port: 6333"
    echo "   - Source: Your IP or 0.0.0.0/0 (for testing)"
    echo ""
    echo "3. Test connection:"
    echo "   curl http://localhost:6333/collections"
    echo ""
    echo "4. Restart your RAG application"
    echo ""
    
    # Test connection
    echo "Testing connection..."
    RESPONSE=$(curl -s http://localhost:6333/collections)
    if [ $? -eq 0 ]; then
        echo "✅ Connection successful!"
        echo "Response: $RESPONSE"
    else
        echo "⚠️  Could not connect. Check firewall settings."
    fi
else
    echo ""
    echo "❌ Qdrant failed to start. Check logs with:"
    echo "   docker logs qdrant"
fi

echo ""
echo "Useful commands:"
echo "  docker logs qdrant          # View logs"
echo "  docker restart qdrant       # Restart"
echo "  docker stop qdrant          # Stop"
echo "  docker start qdrant         # Start"
echo "  docker exec -it qdrant sh   # Access shell"
