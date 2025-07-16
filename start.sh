#!/bin/bash

# Download model from cloud storage
wget https://drive.google.com/file/d/1O6F8-dcxAe2jwjrBV6jZLqmKFw8WtaHl/view?usp=drive_link/model.h5 -O model.h5

# Start FastAPI server
uvicorn app:app --host=0.0.0.0 --port=10000
