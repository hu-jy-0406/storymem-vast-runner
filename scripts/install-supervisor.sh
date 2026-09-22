#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
CONFIG=${1:?Usage: install-supervisor.sh /absolute/path/to/config.env [service-name]}
SERVICE=${2:-storymem-batch}
CONF=/etc/supervisor/conf.d/${SERVICE}.conf
test -f "$CONFIG"
cat > "$CONF" <<EOF
[program:${SERVICE}]
environment=PROC_NAME="%(program_name)s"
command=/bin/bash ${ROOT}/scripts/run-job.sh ${CONFIG}
autostart=false
autorestart=false
startsecs=10
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
redirect_stderr=true
stopasgroup=true
killasgroup=true
stopwaitsecs=60
EOF
supervisorctl reread
supervisorctl update
echo "Installed. Start with: supervisorctl start ${SERVICE}"
