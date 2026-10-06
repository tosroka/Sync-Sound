FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y curl build-essential && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

WORKDIR /app

# Copy the pyproject.toml and uv.lock (if it exists) to leverage Docker cache
COPY pyproject.toml .
COPY uv.lock .

# Install dependencies using uv
RUN uv sync

# Copy the rest of the application
COPY . .

# Expose the port FastAPI will run on
EXPOSE 8000

# Start the application using uv to run uvicorn
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]


