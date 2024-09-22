#!/bin/bash

# chmod +x deploy.sh
# Define variables
SSH_USER="ubuntu"
SSH_HOST="16.16.202.145"
SSH_KEY="/home/pyro/access.pem"

# Get the current directory name
CURRENT_DIR_NAME=$(basename "$PWD")

# Define the remote directory path
REMOTE_DIR="/home/ubuntu/$CURRENT_DIR_NAME"

# Create the remote directory if it does not exist
ssh -i "$SSH_KEY" "$SSH_USER@$SSH_HOST" "mkdir -p $REMOTE_DIR"

# Upload the current folder to the remote server
scp -r -i "$SSH_KEY" "$PWD/" "$SSH_USER@$SSH_HOST:$REMOTE_DIR"

echo "Upload complete!"