#!/bin/bash

# Download model from cloud storage
wget https://your-cloud-storage-link/model.h5 -O model.h5

# Start FastAPI server
uvicorn app:app --host=0.0.0.0 --port=10000
