#!/usr/bin/env bash
set -Eeuo pipefail

release_sha="${1:-}"
sender="${2:-}"
if [[ ! "$release_sha" =~ ^[0-9a-f]{40}$ ]]; then
  echo "Expected a 40-character commit SHA" >&2
  exit 1
fi
if [[ ! "$sender" =~ ^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+$ ]]; then
  echo "Expected a valid receipt sender address" >&2
  exit 1
fi

root="$HOME/ragezine-portal"
archive="$root/incoming/$release_sha.tar.gz"
release="$root/releases/$release_sha"
env_file="$root/shared/.env"

if [[ ! -f "$archive" ]]; then
  echo "Release archive is missing: $archive" >&2
  exit 1
fi
if [[ ! -f "$env_file" ]]; then
  echo "Create the server's private environment file at $env_file" >&2
  exit 1
fi

required_values=(
  DJANGO_SECRET_KEY POSTGRES_PASSWORD DJANGO_ALLOWED_HOSTS RAGEZINE_PUBLIC_HOST RAGEZINE_ADMIN_HOST
  AWS_STORAGE_BUCKET_NAME AWS_S3_REGION_NAME AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY
)
for name in "${required_values[@]}"; do
  if ! grep -Eq "^${name}=.+" "$env_file"; then
    echo "Set $name in the server's private environment file before deploying" >&2
    exit 1
  fi
done
if ! grep -Eq '^RAGEZINE_STORAGE_BACKEND=s3$' "$env_file"; then
  echo "Set RAGEZINE_STORAGE_BACKEND=s3 before deploying" >&2
  exit 1
fi

mkdir -p "$release"
tar -xzf "$archive" -C "$release"
ln -sfn "$env_file" "$release/.env"

compose=(docker compose -p ragezine-portal --project-directory "$release" --env-file "$env_file" -f "$release/docker-compose.yml")
"${compose[@]}" config --quiet
"${compose[@]}" build --pull
sender_changed=false
if ! grep -Fxq "SUBMISSION_EMAIL_FROM=$sender" "$env_file"; then
  temp_env="$(mktemp "$root/shared/.env.XXXXXX")"
  chmod --reference="$env_file" "$temp_env"
  awk -v sender="$sender" '
    /^SUBMISSION_EMAIL_FROM=/ {
      if (!seen++) print "SUBMISSION_EMAIL_FROM=" sender
      next
    }
    { print }
    END { if (!seen) print "SUBMISSION_EMAIL_FROM=" sender }
  ' "$env_file" > "$temp_env"
  mv "$temp_env" "$env_file"
  sender_changed=true
fi
"${compose[@]}" up -d --remove-orphans --wait --wait-timeout 180
if "$sender_changed"; then
  "${compose[@]}" up -d --no-deps --force-recreate --wait --wait-timeout 180 backend
fi

port_binding="$("${compose[@]}" port nginx 80)"
http_port="${port_binding##*:}"
if [[ ! "$http_port" =~ ^[0-9]+$ ]]; then
  echo "Could not determine the published nginx port: $port_binding" >&2
  exit 1
fi
curl --fail --silent --show-error --retry 12 --retry-delay 5 \
  "http://127.0.0.1:$http_port/" > /dev/null

ln -sfnT "$release" "$root/current"
echo "Deployed commit $release_sha"
