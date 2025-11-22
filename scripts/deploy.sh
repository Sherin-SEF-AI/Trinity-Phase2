#!/bin/bash
# Trinity Phase 2 - Deployment Script
# Manages Docker Compose deployment with various profiles

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Print colored message
print_message() {
    local color=$1
    shift
    echo -e "${color}$@${NC}"
}

# Print banner
print_banner() {
    echo "================================================"
    echo "  Trinity Phase 2 - AV Testing Platform"
    echo "  Docker Deployment Manager"
    echo "================================================"
    echo
}

# Check prerequisites
check_prerequisites() {
    print_message "$YELLOW" "Checking prerequisites..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_message "$RED" "ERROR: Docker is not installed"
        exit 1
    fi

    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null &&  ! docker compose version &> /dev/null; then
        print_message "$RED" "ERROR: Docker Compose is not installed"
        exit 1
    fi

    # Check NVIDIA Docker runtime (optional but recommended)
    if ! docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi &> /dev/null; then
        print_message "$YELLOW" "WARNING: NVIDIA Docker runtime not available. GPU acceleration will not work."
    fi

    print_message "$GREEN" "✓ Prerequisites check passed"
}

# Create required directories
create_directories() {
    print_message "$YELLOW" "Creating required directories..."

    mkdir -p data/{sessions,calibration}
    mkdir -p logs
    mkdir -p reports
    mkdir -p models/yolo
    mkdir -p config

    print_message "$GREEN" "✓ Directories created"
}

# Generate .env file if it doesn't exist
generate_env() {
    if [ ! -f .env ]; then
        print_message "$YELLOW" "Generating .env file..."

        cat > .env << EOF
# Trinity Phase 2 - Environment Configuration

# Database
DB_PASSWORD=trinity_$(openssl rand -hex 16)
POSTGRES_PASSWORD=\${DB_PASSWORD}

# Grafana
GRAFANA_PASSWORD=admin_$(openssl rand -hex 8)

# pgAdmin
PGADMIN_PASSWORD=admin_$(openssl rand -hex 8)

# Display (for GUI)
DISPLAY=:0

# Trinity Configuration
TRINITY_LOG_LEVEL=INFO
TRINITY_USE_GPU=true
TRINITY_GPU_ID=0
EOF

        print_message "$GREEN" "✓ .env file generated"
        print_message "$YELLOW" "NOTE: Please review and customize .env file"
    else
        print_message "$GREEN" "✓ .env file exists"
    fi
}

# Start services
start_services() {
    local profile="${1:-default}"

    print_message "$YELLOW" "Starting Trinity services (profile: $profile)..."

    case "$profile" in
        "api-only")
            docker-compose up -d database redis trinity-api
            ;;
        "full")
            docker-compose --profile monitoring --profile admin up -d
            ;;
        "monitoring")
            docker-compose --profile monitoring up -d
            ;;
        "gui")
            # Allow X11 forwarding
            xhost +local:docker || true
            docker-compose --profile gui up -d
            ;;
        "carla")
            docker-compose --profile carla up -d
            ;;
        *)
            docker-compose up -d
            ;;
    esac

    print_message "$GREEN" "✓ Services started"
}

# Stop services
stop_services() {
    print_message "$YELLOW" "Stopping Trinity services..."
    docker-compose down
    print_message "$GREEN" "✓ Services stopped"
}

# View logs
view_logs() {
    local service="${1:-trinity-api}"
    docker-compose logs -f "$service"
}

# Check service status
check_status() {
    print_message "$YELLOW" "Checking service status..."
    docker-compose ps
    echo
    print_message "$YELLOW" "API Health Check:"
    curl -s http://localhost:8000/api/v1/health | jq '.' || echo "API not responding"
}

# Clean up
cleanup() {
    print_message "$YELLOW" "Cleaning up Docker resources..."

    read -p "This will remove all containers, volumes, and images. Continue? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker-compose down -v --rmi all
        print_message "$GREEN" "✓ Cleanup complete"
    else
        print_message "$YELLOW" "Cleanup cancelled"
    fi
}

# Show help
show_help() {
    cat << EOF
Trinity Phase 2 - Deployment Script

Usage: $0 <command> [options]

Commands:
    init                Initialize environment (create dirs, generate .env)
    start [profile]     Start services (profiles: default, api-only, full, monitoring, gui, carla)
    stop                Stop all services
    restart [profile]   Restart services
    logs [service]      View logs (default: trinity-api)
    status              Check service status
    cleanup             Remove all containers, volumes, and images
    help                Show this help message

Examples:
    $0 init                    # Initialize environment
    $0 start                   # Start default services
    $0 start full              # Start all services including monitoring
    $0 start gui               # Start with GUI support
    $0 logs trinity-api        # View API logs
    $0 status                  # Check status
    $0 stop                    # Stop all services

EOF
}

# Main script
main() {
    print_banner

    local command="${1:-help}"

    case "$command" in
        "init")
            check_prerequisites
            create_directories
            generate_env
            print_message "$GREEN" "\n✓ Initialization complete!"
            print_message "$YELLOW" "Next steps:"
            print_message "$YELLOW" "  1. Review and customize .env file"
            print_message "$YELLOW" "  2. Run: $0 start"
            ;;
        "start")
            check_prerequisites
            create_directories
            generate_env
            start_services "${2:-default}"
            sleep 5
            check_status
            ;;
        "stop")
            stop_services
            ;;
        "restart")
            stop_services
            sleep 2
            start_services "${2:-default}"
            ;;
        "logs")
            view_logs "${2}"
            ;;
        "status")
            check_status
            ;;
        "cleanup")
            cleanup
            ;;
        "help"|*)
            show_help
            ;;
    esac
}

# Run main function
main "$@"
