#!/bin/bash
set -e

# Alpine VM Build and Boot Script
#
# Builds and boots an Alpine Linux VM for integration testing.
#
# The script will:
#   1. Check dependencies
#   2. Build VM image alpine.qcow2 (prompts if exists, reuses it if
#      not running interactively)
#   3. Boot VM with QEMU on port 2222
#   4. Setup workspace (mount 9p filesystem and create symlink)
#
# Pass --build-only to stop after building the image.
#
# To stop the running VM:
#   pkill -f 'qemu-system.*alpine.qcow2'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VM_BUILD_DIR="$REPO_ROOT/.alpine-vm-build"
VM_IMAGE="$VM_BUILD_DIR/alpine.qcow2"
VM_SSH_PORT="2222"
VM_CONSOLE_LOG="vm-console.log"
VM_PACKAGES="bluez openssh uv git"

# alpine-make-vm-image downloads apk.static from gitlab.alpinelinux.org by
# default, which is unreliable, so take it from the apk-tools-static package
# on the package mirror instead. The v3.22 branch is the last one with
# apk-tools 2.x, which is what alpine-make-vm-image uses by default. The
# version is looked up in the APKINDEX since the mirror only keeps the latest
# build, and apk.static is verified against Alpine's signing key instead of
# a pinned hash.
APK_TOOLS_STATIC_REPO="https://dl-cdn.alpinelinux.org/alpine/v3.22/main/x86_64"
ALPINE_KEY_NAME="alpine-devel@lists.alpinelinux.org-6165ee59.rsa.pub"
ALPINE_KEY="-----BEGIN PUBLIC KEY-----
MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEAutQkua2CAig4VFSJ7v54
ALyu/J1WB3oni7qwCZD3veURw7HxpNAj9hR+S5N/pNeZgubQvJWyaPuQDm7PTs1+
tFGiYNfAsiibX6Rv0wci3M+z2XEVAeR9Vzg6v4qoofDyoTbovn2LztaNEjTkB+oK
tlvpNhg1zhou0jDVYFniEXvzjckxswHVb8cT0OMTKHALyLPrPOJzVtM9C1ew2Nnc
3848xLiApMu3NBk0JqfcS3Bo5Y2b1FRVBvdt+2gFoKZix1MnZdAEZ8xQzL/a0YS5
Hd0wj5+EEKHfOd3A75uPa/WQmA+o0cBFfrzm69QDcSJSwGpzWrD1ScH3AK8nWvoj
v7e9gukK/9yl1b4fQQ00vttwJPSgm9EnfPHLAtgXkRloI27H6/PuLoNvSAMQwuCD
hQRlyGLPBETKkHeodfLoULjhDi1K2gKJTMhtbnUcAA7nEphkMhPWkBpgFdrH+5z4
Lxy+3ek0cqcI7K68EtrffU8jtUj9LFTUC8dERaIBs7NgQ/LfDbDfGh9g6qVj1hZl
k9aaIPTm/xsi8v3u+0qaq7KzIBc9s59JOoA8TlpOaYdVgSQhHHLBaahOuAigH+VI
isbC9vmqsThF2QdDtQt37keuqoda2E6sL7PUvIyVXDRfwX7uMDjlzTxHTymvq2Ck
htBqojBnThmjJQFgZXocHG8CAwEAAQ==
-----END PUBLIC KEY-----"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check dependencies
check_dependencies() {
    log_info "Checking dependencies..."
    
    local missing_deps=()
    
    if ! command -v qemu-system-x86_64 &> /dev/null; then
        missing_deps+=("qemu-system-x86_64")
    fi
    
    if ! command -v wget &> /dev/null && ! command -v curl &> /dev/null; then
        missing_deps+=("wget or curl")
    fi
    
    if ! command -v lsof &> /dev/null; then
        missing_deps+=("lsof")
    fi

    if ! command -v curl &> /dev/null; then
        missing_deps+=("curl")
    fi

    if ! command -v openssl &> /dev/null; then
        missing_deps+=("openssl")
    fi

    if [ ${#missing_deps[@]} -ne 0 ]; then
        log_error "Missing dependencies: ${missing_deps[*]}"
        log_info "On Ubuntu/Debian: sudo apt-get install qemu-system-x86 qemu-utils qemu-kvm"
        exit 1
    fi
    
    log_info "All dependencies found"
}

# Fetch alpine-make-vm-image script
fetch_alpine_make_vm_image() {
    mkdir -p "$VM_BUILD_DIR"
    
    if [ -f "$VM_BUILD_DIR/alpine-make-vm-image" ]; then
        log_info "alpine-make-vm-image already exists"
        return 0
    fi
    
    log_info "Fetching alpine-make-vm-image..."
    if command -v wget &> /dev/null; then
        wget -q -O "$VM_BUILD_DIR/alpine-make-vm-image" https://raw.githubusercontent.com/alpinelinux/alpine-make-vm-image/v0.13.3/alpine-make-vm-image
    else
        curl -sS -o "$VM_BUILD_DIR/alpine-make-vm-image" https://raw.githubusercontent.com/alpinelinux/alpine-make-vm-image/v0.13.3/alpine-make-vm-image
    fi
    chmod +x "$VM_BUILD_DIR/alpine-make-vm-image"
    log_info "alpine-make-vm-image fetched"
}

# Fetch apk.static from the apk-tools-static package
fetch_apk_static() {
    local apk_static="$VM_BUILD_DIR/sbin/apk.static"
    local signature="$apk_static.SIGN.RSA.sha256.$ALPINE_KEY_NAME"
    local version

    if [ -f "$apk_static" ]; then
        log_info "apk.static already exists"
        return 0
    fi

    log_info "Fetching apk-tools-static..."
    curl -sSf --retry 5 -o "$VM_BUILD_DIR/APKINDEX.tar.gz" "$APK_TOOLS_STATIC_REPO/APKINDEX.tar.gz"
    version=$(tar -xzOf "$VM_BUILD_DIR/APKINDEX.tar.gz" APKINDEX \
        | awk '/^P:apk-tools-static$/ { found = 1 } found && /^V:/ { print substr($0, 3); exit }')
    rm "$VM_BUILD_DIR/APKINDEX.tar.gz"
    if [ -z "$version" ]; then
        log_error "apk-tools-static not found in $APK_TOOLS_STATIC_REPO"
        exit 1
    fi

    curl -sSf --retry 5 -o "$VM_BUILD_DIR/apk-tools-static.apk" \
        "$APK_TOOLS_STATIC_REPO/apk-tools-static-$version.apk"
    tar -xzf "$VM_BUILD_DIR/apk-tools-static.apk" -C "$VM_BUILD_DIR" --warning=no-unknown-keyword \
        "${apk_static#"$VM_BUILD_DIR"/}" "${signature#"$VM_BUILD_DIR"/}"
    rm "$VM_BUILD_DIR/apk-tools-static.apk"

    if ! openssl dgst -sha256 -verify <(echo "$ALPINE_KEY") -signature "$signature" "$apk_static"; then
        rm -f "$apk_static"
        log_error "apk.static signature verification failed"
        exit 1
    fi
    rm "$signature"
    log_info "apk.static $version fetched"
}

# Build Alpine VM image
build_vm_image() {
    if [ -f "$VM_IMAGE" ]; then
        if [ ! -t 0 ]; then
            log_info "Using existing VM image $VM_IMAGE"
            return 0
        fi
        log_warn "VM image $VM_IMAGE already exists. Delete it to rebuild."
        read -p "Delete and rebuild? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Using existing VM image"
            return 0
        fi
        rm -f "$VM_IMAGE"
    fi
    
    fetch_alpine_make_vm_image
    fetch_apk_static

    log_info "Building Alpine VM image..."
    
    # Check if we need sudo
    if [ -w /dev/loop-control ] 2>/dev/null; then
        SUDO=""
    else
        SUDO="sudo"
        log_warn "Requires sudo for loop device access"
    fi
    
    cd "$VM_BUILD_DIR"
    $SUDO env APK="$VM_BUILD_DIR/sbin/apk.static" ./alpine-make-vm-image \
        --image-format qcow2 \
        --image-size 1G \
        --serial-console \
        --kernel-flavor lts \
        --packages "$VM_PACKAGES" \
        --script-chroot \
        "$VM_IMAGE" \
        "$SCRIPT_DIR/alpine-vm-setup.sh"
    
    if [ -n "$SUDO" ]; then
        $SUDO chown $USER:$USER "$VM_IMAGE"
    fi
    
    log_info "VM image built: $VM_IMAGE ($(du -h "$VM_IMAGE" | cut -f1))"
}

# Boot Alpine VM with QEMU
boot_vm() {
    log_info "Booting Alpine VM with QEMU..."
    
    # Check if KVM is available
    if [ -e /dev/kvm ] && [ -r /dev/kvm ] && [ -w /dev/kvm ]; then
        log_info "KVM is available, using hardware acceleration"
        KVM_FLAGS="-enable-kvm -cpu host"
    else
        log_warn "KVM not available, using software emulation (slower)"
        KVM_FLAGS=""
    fi
    
    # Check if VM is already running
    if command -v lsof &> /dev/null && lsof -i :$VM_SSH_PORT &> /dev/null; then
        log_warn "Port $VM_SSH_PORT is already in use. VM seems to be running."
        read -p "Stop the running VM? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            log_info "Stopping VM..."
            pkill -f "qemu-system.*$VM_IMAGE" || true
            sleep 2
            log_info "VM stopped"
        else
            log_error "Cannot start VM while port is in use"
            exit 1
        fi
    fi
    
    # Start QEMU with serial console output to file and 9p filesystem sharing
    qemu-system-x86_64 \
        -m 2G \
        -smp 2 \
        $KVM_FLAGS \
        -display none \
        -serial file:$VM_CONSOLE_LOG \
        -drive file=$VM_IMAGE,format=qcow2,if=virtio,cache=unsafe \
        -netdev user,id=net0,hostfwd=tcp::$VM_SSH_PORT-:22 \
        -device virtio-net-pci,netdev=net0 \
        -virtfs local,path="$REPO_ROOT",mount_tag=host0,security_model=mapped-xattr,id=host0 \
        -daemonize
    
    log_info "QEMU started (PID: $(pgrep -f "qemu-system.*$VM_IMAGE" || echo 'unknown'))"
    log_info "Monitoring VM boot process..."
    echo "========================================"
    
    # Function to test SSH connection
    check_ssh() {
        ssh -o StrictHostKeyChecking=no \
            -o UserKnownHostsFile=/dev/null \
            -o ConnectTimeout=5 \
            -p $VM_SSH_PORT \
            builder@localhost \
            'echo VM is ready' 2>/dev/null
    }
        
    # Tail the console log in background
    tail -f $VM_CONSOLE_LOG &
    TAIL_PID=$!
    
    # Wait for VM to boot and SSH to be ready
    MAX_ATTEMPTS=12
    ATTEMPT=0
    while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
        if check_ssh; then
            echo ""
            echo "========================================"
            log_info "✓ VM is ready!"
            kill $TAIL_PID 2>/dev/null || true
            
            # Setup workspace in VM
            log_info "Setting up workspace in VM..."
            ssh -o StrictHostKeyChecking=no \
                -o UserKnownHostsFile=/dev/null \
                -p $VM_SSH_PORT \
                builder@localhost << 'EOFSETUP'
sudo mkdir -p /home/builder/repo
sudo mount -t 9p -o trans=virtio,version=9p2000.L host0 /home/builder/repo || echo "Already mounted"
sudo chown -R builder:builder /home/builder/repo
sudo chmod 755 /home/builder/repo
EOFSETUP
            log_info "✓ Workspace setup complete"
                        
            log_info "SSH connection: ssh -p $VM_SSH_PORT builder@localhost"
            log_info "To stop VM: pkill -f 'qemu-system.*$VM_IMAGE'"
            
            return 0
        fi
        ATTEMPT=$((ATTEMPT + 1))
        sleep 5
    done
    
    # VM failed to start
    kill $TAIL_PID 2>/dev/null || true
    log_error "VM failed to start properly after $MAX_ATTEMPTS attempts"
    echo "Full console log:"
    cat $VM_CONSOLE_LOG
    exit 1
}

# Main execution
main() {
    log_info "Alpine VM Build and Boot Script"
    log_info "Repository root: $REPO_ROOT"
    log_info "VM image: $VM_IMAGE"
    
    cd "$REPO_ROOT"
    
    check_dependencies
    build_vm_image

    if [ "${1:-}" = "--build-only" ]; then
        return 0
    fi

    boot_vm
    
    log_info "Alpine VM setup complete!"
}

main "$@"
