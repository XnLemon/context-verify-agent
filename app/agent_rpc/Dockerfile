FROM python:3.13-slim
WORKDIR /app
ENV PYTHONPATH=/app/app/agent_rpc:/app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY . /app
RUN python3 -m grpc_tools.protoc -I /app/app/agent_rpc/proto --python_out=/app/app/agent_rpc --grpc_python_out=/app/app/agent_rpc /app/app/agent_rpc/proto/agent.proto
EXPOSE 50051
CMD ["python3", "-m", "app.agent_rpc.server"]
