#!/bin/bash

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
else
    echo "Virtual environment already exists."
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create uploads directory if it doesn't exist
if [ ! -d "uploads" ]; then
    echo "Creating uploads directory..."
    mkdir uploads
fi

# Create .env file from example if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file from example..."
    cp .env.example .env
    echo "Please update the .env file with your OpenAI API key."
fi

echo "Setup complete! You can now run the server with:"
echo "python app.py"
