# Container for the agent-queue demo. Build: docker build -t firstreply .  Run: docker run -p 8501:8501 firstreply
FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src src
COPY app app
COPY evalset evalset
COPY outputs outputs
ENV PYTHONPATH=/app/src FIRSTREPLY_DB=/tmp/approvals.db
EXPOSE 8501
CMD ["streamlit", "run", "app/queue_app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
