#!/bin/sh

_step_counter=0
step() {
	_step_counter=$(( _step_counter + 1 ))
	printf '\n\033[1;36m%d) %s\033[0m\n' $_step_counter "$@" >&2  # bold cyan
}

# Setup script for Alpine VM image

# Set up networking to use DHCP on eth0
step 'Set up networking'
cat > /etc/network/interfaces <<-EOF
	iface lo inet loopback
	iface eth0 inet dhcp
EOF
ln -s networking /etc/init.d/net.lo
ln -s networking /etc/init.d/net.eth0

step 'Enable service for networking'
rc-update add net.eth0 default
rc-update add net.lo boot

# Enable bluetooth and dbus services
step 'Enable bluetooth and dbus services'
rc-update add bluetooth default
rc-update add dbus default

# Configure vhci kernel module to load at boot
step 'Configure VHCI kernel module for boot'
echo "hci_vhci" >> /etc/modules

# Enable SSH service
step 'Enable SSH service'
rc-update add sshd default

# Configure SSH for password-less access
step 'Configure SSH for password-less builder user'
sed -i 's/#PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/#PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config
sed -i 's/#PermitEmptyPasswords.*/PermitEmptyPasswords yes/' /etc/ssh/sshd_config
sed -i 's/#LogLevel.*/LogLevel VERBOSE/' /etc/ssh/sshd_config

# Create non-root user
step 'Create user "builder"'
adduser -D -s /bin/sh builder

# Set empty password for builder (allow login without password)
passwd -d builder

# Configure VHCI access for user "builder"
step 'Configure VHCI access for user "builder"'
addgroup -S bluetooth 2>/dev/null || true
addgroup builder bluetooth

# Create init script to set vhci permissions (Alpine uses mdev, not udev)
cat > /etc/local.d/vhci-permissions.start <<'EOF'
#!/bin/sh
# Set permissions for /dev/vhci
chgrp bluetooth /dev/vhci
chmod 0660 /dev/vhci
EOF
chmod +x /etc/local.d/vhci-permissions.start
rc-update add local default

# Configure sudo access for user "builder" without password
step 'Configure sudo access for user "builder" without password'
apk add sudo
if ! getent group sudo >/dev/null 2>&1; then
	addgroup sudo
fi
addgroup builder sudo
echo '%sudo ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/sudo

# Verify the service is added
step 'Verify services'
rc-status -a

