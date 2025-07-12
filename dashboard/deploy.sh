#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if Docker is installed
check_docker() {
    if command -v docker &> /dev/null; then
        return 0
    else
        return 1
    fi
}

# Function to check if nginx is installed
check_nginx() {
    if command -v nginx &> /dev/null; then
        return 0
    else
        return 1
    fi
}

# Function to install and configure nginx
install_nginx() {
    print_status "Installing and configuring nginx..."
    
    # Update package index
    sudo apt-get update
    
    # Install nginx
    sudo apt-get install -y nginx
    
    # Create nginx configuration for proxy pass
    sudo tee /etc/nginx/sites-available/marium-dashboard > /dev/null <<EOF
server {
    listen 80;
    server_name localhost;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    location /static/ {
        alias /home/aviox/projects/deepak/marium/middleware/dashboard/src/staticfiles/;
    }
    
    location /media/ {
        alias /home/aviox/projects/deepak/marium/middleware/dashboard/src/media/;
    }
}
EOF
    
    # Remove default nginx site
    sudo rm -f /etc/nginx/sites-enabled/default
    
    # Enable our site
    sudo ln -sf /etc/nginx/sites-available/marium-dashboard /etc/nginx/sites-enabled/
    
    # Test nginx configuration
    sudo nginx -t
    
    # Start and enable nginx
    sudo systemctl start nginx
    sudo systemctl enable nginx
    
    print_success "Nginx installed and configured successfully!"
}

# Function to install Docker Engine
install_docker() {
    print_status "Installing Docker Engine..."
    
    # Update package index
    sudo apt-get update
    
    # Install prerequisites
    sudo apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release
    
    # Add Docker's official GPG key
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    
    # Add Docker repository
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # Update package index again
    sudo apt-get update
    
    # Install Docker Engine
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io
    
    # Add current user to docker group
    sudo usermod -aG docker $USER
    
    print_success "Docker Engine installed successfully!"
    print_warning "You may need to log out and log back in for group changes to take effect."
}

# Function to copy env.example to .env
copy_env_file() {
    if [ -f "env.example" ]; then
        if [ ! -f ".env" ]; then
            print_status "Copying env.example to .env..."
            cp env.example .env
            print_success "Environment file created successfully!"
        else
            print_warning ".env file already exists. Skipping..."
        fi
    else
        print_error "env.example file not found!"
        exit 1
    fi
}

# Function to deploy with Docker Compose
deploy_docker() {
    print_status "Deploying with Docker Compose..."
    
    if [ -f "docker-compose-prod.yml" ]; then
        docker compose -f docker-compose-prod.yml up --build -d
        if [ $? -eq 0 ]; then
            print_success "Deployment completed successfully!"
            print_status "Application should be available at http://localhost (via nginx proxy)"
        else
            print_error "Deployment failed!"
            exit 1
        fi
    else
        print_error "docker-compose-prod.yml file not found!"
        exit 1
    fi
}

# Main script
main() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}    Marium Dashboard Deployer    ${NC}"
    echo -e "${BLUE}================================${NC}"
    echo ""
    
    # Check if we're in the correct directory
    if [ ! -f "docker-compose-prod.yml" ]; then
        print_error "Please run this script from the dashboard directory!"
        exit 1
    fi
    
    # Interactive menu
    echo "Choose deployment type:"
    echo "1) Fresh Install (Install Docker + Deploy)"
    echo "2) Normal Deploy (Deploy only)"
    echo ""
    read -p "Enter your choice (1 or 2): " choice
    
    case $choice in
        1)
            print_status "Starting fresh install..."
            
            # Install and configure nginx first
            install_nginx
            
            # Check if Docker is already installed
            if check_docker; then
                print_warning "Docker is already installed. Skipping Docker installation..."
            else
                install_docker
            fi
            
            # Copy environment file
            copy_env_file
            
            # Deploy
            deploy_docker
            ;;
        2)
            print_status "Starting normal deployment..."
            
            # Check if nginx is installed
            if ! check_nginx; then
                print_error "Nginx is not installed. Please run fresh install first!"
                exit 1
            fi
            
            # Check if Docker is installed
            if ! check_docker; then
                print_error "Docker is not installed. Please run fresh install first!"
                exit 1
            fi
            
            # Copy environment file
            copy_env_file
            
            # Deploy
            deploy_docker
            ;;
        *)
            print_error "Invalid choice. Please run the script again and select 1 or 2."
            exit 1
            ;;
    esac
}

# Run main function
main 