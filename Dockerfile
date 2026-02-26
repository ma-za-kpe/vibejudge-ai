# VibeJudge AI - Streamlit Dashboard Dockerfile
# Multi-stage build for optimized image size (<500MB target)

# ============================================================================
# BUILDER STAGE - Install dependencies
# ============================================================================
FROM python:3.12-alpine AS builder

# Set working directory
WORKDIR /build

# Install build dependencies for compiling Python packages
RUN apk add --no-cache \
    gcc \
    musl-dev \
    linux-headers \
    g++ \
    libffi-dev \
    openssl-dev \
    cargo \
    rust

# Copy requirements file
COPY streamlit_ui/requirements.txt .

# Install Python dependencies to a local directory
RUN pip install --no-cache-dir --user -r requirements.txt && \
    # Remove unnecessary files to reduce size
    find /root/.local -type d -name "tests" -exec rm -rf {} + || true && \
    find /root/.local -type d -name "__pycache__" -exec rm -rf {} + || true && \
    find /root/.local -name "*.pyc" -delete || true && \
    find /root/.local -name "*.pyo" -delete || true && \
    find /root/.local -name "*.c" -delete || true && \
    find /root/.local -name "*.pxd" -delete || true && \
    find /root/.local -name "*.pyd" -delete || true

# ============================================================================
# RUNTIME STAGE - Minimal production image
# ============================================================================
FROM python:3.12-alpine

# Metadata labels
LABEL maintainer="VibeJudge AI Team"
LABEL version="1.0.0"
LABEL description="Streamlit dashboard for VibeJudge AI hackathon judging platform"

# Install runtime dependencies only
RUN apk add --no-cache \
    libstdc++ \
    libgcc \
    bash \
    curl

# Create non-root user with UID 1000
RUN addgroup -g 1000 streamlit && \
    adduser -D -u 1000 -G streamlit -s /bin/bash streamlit

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder stage
COPY --from=builder /root/.local /home/streamlit/.local

# Copy only necessary Streamlit application files
COPY --chown=streamlit:streamlit streamlit_ui/app.py streamlit_ui/requirements.txt ./
COPY --chown=streamlit:streamlit streamlit_ui/components ./components/
COPY --chown=streamlit:streamlit streamlit_ui/pages ./pages/
COPY --chown=streamlit:streamlit streamlit_ui/.streamlit ./.streamlit/

# Configure Streamlit environment variables
ENV PATH=/home/streamlit/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    API_BASE_URL=""

# Expose Streamlit port
EXPOSE 8501

# Switch to non-root user
USER streamlit

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8501/_stcore/health')"

# Run Streamlit application
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
