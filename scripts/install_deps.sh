# A helper function to add color to a string message
print_colored_message() {
    shift
    printf "\e[1;33m$@\e[0m\n"
}

print_colored_message "══ Installing mininet ══"

sudo apt install mininet

print_colored_message "══ Installing OpenVSwitch ══"

sudo apt install openvswitch-testcontroller

print_colored_message "══ Enabling OpenVSwitch ══"

sudo systemctl enable --now openvswitch-switch

print_colored_message "══ Installing TCPDump ══" # To capture packets for fragmentation item

sudo apt install tcpdump
