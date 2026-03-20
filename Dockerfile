FROM python:3.9-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    WANDB_MODE=disabled

WORKDIR /app

# Build tools are required for C++ planner extensions.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    g++ \
    liboctomap-dev \
    libdynamicedt3d-dev \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && \
    pip install -r /app/requirements.txt && \
    pip install pybind11 cppimport

COPY . /app

# Build planner extensions from source for the current Python/CPU architecture.
# Compile in separate Python processes to avoid pybind11 type re-registration.
RUN python -c "import cppimport; cppimport.imp('planner.LB_A.planner')"
RUN python -c "import cppimport; cppimport.imp('planner.Static_A.planner')"

CMD ["python", "main.py"]
