# syntax=docker/dockerfile:1
FROM mcr.microsoft.com/devcontainers/python:3.11

# Install lightweight system deps commonly used by Pillow/folium/selenium
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        unzip \
        fonts-dejavu \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
