#!/usr/bin/env bash
# wait-for-it.sh

host="$1"
shift
port="$1"
shift

while ! nc -z "$host" "$port"; do
  echo "Service $host:$port is unavailable - sleeping"
  sleep 1
done

echo "Service $host:$port is up!"
exec "$@"