#!/usr/bin/env bash
# Fixed input-only launcher, called only through replay_coordinator.py.
set -euo pipefail
task_input_fd=$1
task_worker_fd=$2
task_size=$3
task_sha=$4
mount --make-rprivate /
mount -t proc -o nosuid,nodev,noexec proc /proc
mount -t tmpfs -o size=96m,mode=1777,nosuid,nodev tmpfs /tmp
task_jail=$(mktemp -d /tmp/cyber-input-jail-XXXXXX)
mkdir -p "$task_jail"/{usr,etc,dev/shm,proc,tmp,run,var,home/private}
for task_path in /usr/bin /usr/lib/x86_64-linux-gnu /usr/lib64 /usr/lib/python3.12; do
  mkdir -p "$task_jail$task_path"
  mount --bind "$task_path" "$task_jail$task_path"
  mount -o remount,bind,ro,nosuid,nodev "$task_jail$task_path"
done
ln -s usr/bin "$task_jail/bin"
ln -s usr/lib "$task_jail/lib"
ln -s usr/lib64 "$task_jail/lib64"
touch "$task_jail/etc/ld.so.cache"
mount --bind /etc/ld.so.cache "$task_jail/etc/ld.so.cache"
mount -o remount,bind,ro,nosuid,nodev "$task_jail/etc/ld.so.cache"
for task_node in null zero random urandom; do
  touch "$task_jail/dev/$task_node"
  mount --bind "/dev/$task_node" "$task_jail/dev/$task_node"
done
mount -t tmpfs -o size=64m,mode=1777,nosuid,nodev tmpfs "$task_jail/dev/shm"
mount -t proc -o nosuid,nodev,noexec proc "$task_jail/proc"
cd "$task_jail"
exec /usr/sbin/chroot "$task_jail" /usr/bin/setpriv --no-new-privs --bounding-set=-all --inh-caps=-all --ambient-caps=-all \
  /usr/bin/env -i HOME=/home/private PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 \
  /usr/bin/python3 -I -S -B "/proc/self/fd/$task_worker_fd" "$task_input_fd" "$task_size" "$task_sha"
