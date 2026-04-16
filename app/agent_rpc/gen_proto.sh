#!/usr/bin/env bash
set -euo pipefail
python3 -m grpc_tools.protoc -I app/agent_rpc/proto --python_out=app/agent_rpc --grpc_python_out=app/agent_rpc app/agent_rpc/proto/agent.proto
