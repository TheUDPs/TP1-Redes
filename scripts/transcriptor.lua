-- Wireshark Transcription Plugin

local simple_trans = Proto("simple_trans", "Simple Data Transcription")
local f_breakdown = ProtoField.string("simple_trans.breakdown")
simple_trans.fields = {f_breakdown}

-- Function to identify Ethernet protocols
local function analyze_ethernet(buffer, tree)
    if buffer:len() < 14 then
        tree:add("Packet too short to be Ethernet")
        return nil
    end
    
    local eth_tree = tree:add("Ethernet Header (14 bytes)")
    
    -- Destination MAC address
    local mac_dst = string.format("%02X:%02X:%02X:%02X:%02X:%02X", 
        buffer(0,1):uint(), buffer(1,1):uint(), buffer(2,1):uint(),
        buffer(3,1):uint(), buffer(4,1):uint(), buffer(5,1):uint())
    eth_tree:add(string.format("Destination MAC: %s", mac_dst))
    
    -- Source MAC address
    local mac_src = string.format("%02X:%02X:%02X:%02X:%02X:%02X", 
        buffer(6,1):uint(), buffer(7,1):uint(), buffer(8,1):uint(),
        buffer(9,1):uint(), buffer(10,1):uint(), buffer(11,1):uint())
    eth_tree:add(string.format("Source MAC: %s", mac_src))
    
    -- Ethernet Type / Length
    local eth_type = buffer(12,2):uint()
    if eth_type <= 1500 then
        eth_tree:add(string.format("Length: %d bytes", eth_type))
    else
        local tipo = "Unknown"
        if eth_type == 0x0800 then tipo = "IPv4"
        elseif eth_type == 0x0806 then tipo = "ARP"
        elseif eth_type == 0x86DD then tipo = "IPv6"
        elseif eth_type == 0x8100 then tipo = "VLAN"
        end
        eth_tree:add(string.format("Type: 0x%04X (%s)", eth_type, tipo))
    end
    
    return eth_type, 14  -- Return type and offset where Ethernet header ends
end

-- Function to analyze IPv4
local function analyze_ipv4(buffer, tree, offset)
    if buffer:len() < offset + 20 then
        tree:add("Packet too short to be IPv4")
        return nil
    end
    
    local ip_tree = tree:add("IPv4 Header")
    
    -- Version and IHL (Internet Header Length)
    local ver_ihl = buffer(offset,1):uint()
    local version = bit.rshift(ver_ihl, 4)
    local ihl = bit.band(ver_ihl, 0x0F) * 4  -- IHL is in 32-bit words (4 bytes)
    ip_tree:add(string.format("Version: %d", version))
    ip_tree:add(string.format("Header Length (IHL): %d bytes", ihl))
    
    -- ToS (Type of Service) or DSCP+ECN
    local tos = buffer(offset+1,1):uint()
    ip_tree:add(string.format("Type of Service: 0x%02X", tos))
    
    -- Total Length
    local total_len = buffer(offset+2,2):uint()
    ip_tree:add(string.format("Total Length: %d bytes", total_len))
    
    -- Identification
    local id = buffer(offset+4,2):uint()
    ip_tree:add(string.format("Identification: 0x%04X", id))
    
    -- Flags and Fragment Offset
    local flags_offset = buffer(offset+6,2):uint()
    local flags = bit.rshift(flags_offset, 13)
    local offset_val = bit.band(flags_offset, 0x1FFF) * 8  -- Fragment offset is in units of 8 bytes
    
    local flags_str = ""
    if bit.band(flags, 0x1) ~= 0 then flags_str = flags_str .. "MF " end  -- More Fragments
    if bit.band(flags, 0x2) ~= 0 then flags_str = flags_str .. "DF " end  -- Don't Fragment
    if flags_str == "" then flags_str = "None" end
    
    ip_tree:add(string.format("Flags: 0x%X (%s)", flags, flags_str))
    ip_tree:add(string.format("Fragment Offset: %d bytes", offset_val))
    
    -- TTL (Time to Live)
    local ttl = buffer(offset+8,1):uint()
    ip_tree:add(string.format("TTL: %d", ttl))
    
    -- Protocol
    local proto = buffer(offset+9,1):uint()
    local proto_str = "Unknown"
    if proto == 1 then proto_str = "ICMP"
    elseif proto == 6 then proto_str = "TCP"
    elseif proto == 17 then proto_str = "UDP"
    elseif proto == 2 then proto_str = "IGMP"
    elseif proto == 89 then proto_str = "OSPF"
    end
    ip_tree:add(string.format("Protocol: %d (%s)", proto, proto_str))
    
    -- Checksum
    local checksum = buffer(offset+10,2):uint()
    ip_tree:add(string.format("Checksum: 0x%04X", checksum))
    
    -- Source IP
    local ip_src = string.format("%d.%d.%d.%d", 
        buffer(offset+12,1):uint(), buffer(offset+13,1):uint(),
        buffer(offset+14,1):uint(), buffer(offset+15,1):uint())
    ip_tree:add(string.format("Source IP: %s", ip_src))
    
    -- Destination IP
    local ip_dst = string.format("%d.%d.%d.%d", 
        buffer(offset+16,1):uint(), buffer(offset+17,1):uint(),
        buffer(offset+18,1):uint(), buffer(offset+19,1):uint())
    ip_tree:add(string.format("Destination IP: %s", ip_dst))
    
    -- Options (if any)
    if ihl > 20 then
        local options = ""
        for i = offset+20, offset+ihl-1 do
            if i < buffer:len() then
                options = options .. string.format("%02X ", buffer(i,1):uint())
            end
        end
        ip_tree:add(string.format("Options: %s", options))
    end
    
    return proto, offset + ihl  -- Return protocol and offset where IP header ends
end

-- Function to analyze TCP
local function analyze_tcp(buffer, tree, offset)
    if buffer:len() < offset + 20 then
        tree:add("Packet too short to be TCP")
        return nil
    end
    
    local tcp_tree = tree:add("TCP Header")
    
    -- Source Port
    local port_src = buffer(offset,2):uint()
    tcp_tree:add(string.format("Source Port: %d", port_src))
    
    -- Destination Port
    local port_dst = buffer(offset+2,2):uint()
    tcp_tree:add(string.format("Destination Port: %d", port_dst))
    
    -- Sequence Number
    local seq_num = buffer(offset+4,4):uint()
    tcp_tree:add(string.format("Sequence Number: %u", seq_num))
    
    -- ACK Number
    local ack_num = buffer(offset+8,4):uint()
    tcp_tree:add(string.format("ACK Number: %u", ack_num))
    
    -- Data Offset, Reserved and Flags
    local offset_flags = buffer(offset+12,2):uint()
    local data_offset = bit.rshift(bit.band(offset_flags, 0xF000), 12) * 4  -- In 32-bit words (4 bytes)
    
    tcp_tree:add(string.format("Data Offset: %d bytes", data_offset))
    
    -- Flags
    local flags = bit.band(offset_flags, 0x01FF)
    local flags_str = ""
    if bit.band(flags, 0x001) ~= 0 then flags_str = flags_str .. "FIN " end
    if bit.band(flags, 0x002) ~= 0 then flags_str = flags_str .. "SYN " end
    if bit.band(flags, 0x004) ~= 0 then flags_str = flags_str .. "RST " end
    if bit.band(flags, 0x008) ~= 0 then flags_str = flags_str .. "PSH " end
    if bit.band(flags, 0x010) ~= 0 then flags_str = flags_str .. "ACK " end
    if bit.band(flags, 0x020) ~= 0 then flags_str = flags_str .. "URG " end
    if bit.band(flags, 0x040) ~= 0 then flags_str = flags_str .. "ECE " end
    if bit.band(flags, 0x080) ~= 0 then flags_str = flags_str .. "CWR " end
    if bit.band(flags, 0x100) ~= 0 then flags_str = flags_str .. "NS " end
    if flags_str == "" then flags_str = "None" end
    
    tcp_tree:add(string.format("Flags: 0x%03X (%s)", flags, flags_str))
    
    -- Window
    local window = buffer(offset+14,2):uint()
    tcp_tree:add(string.format("Window: %d", window))
    
    -- Checksum
    local checksum = buffer(offset+16,2):uint()
    tcp_tree:add(string.format("Checksum: 0x%04X", checksum))
    
    -- Urgent Pointer
    local urgent = buffer(offset+18,2):uint()
    tcp_tree:add(string.format("Urgent Pointer: %d", urgent))
    
    -- Options (if any)
    if data_offset > 20 then
        local options = ""
        for i = offset+20, offset+data_offset-1 do
            if i < buffer:len() then
                options = options .. string.format("%02X ", buffer(i,1):uint())
            end
        end
        tcp_tree:add(string.format("Options: %s", options))
    end
    
    return {port_src=port_src, port_dst=port_dst}, offset + data_offset
end

-- Function to analyze UDP
local function analyze_udp(buffer, tree, offset)
    if buffer:len() < offset + 8 then
        tree:add("Packet too short to be UDP")
        return nil
    end
    
    local udp_tree = tree:add("UDP Header")
    
    -- Source Port
    local port_src = buffer(offset,2):uint()
    udp_tree:add(string.format("Source Port: %d", port_src))
    
    -- Destination Port
    local port_dst = buffer(offset+2,2):uint()
    udp_tree:add(string.format("Destination Port: %d", port_dst))
    
    -- Length
    local length = buffer(offset+4,2):uint()
    udp_tree:add(string.format("Length: %d bytes", length))
    
    -- Checksum
    local checksum = buffer(offset+6,2):uint()
    udp_tree:add(string.format("Checksum: 0x%04X", checksum))
    
    return {port_src=port_src, port_dst=port_dst}, offset + 8
end

-- Analyze application layer content based on known ports
local function analyze_application(buffer, tree, offset, ports)
    if offset >= buffer:len() then
        return
    end
    
    local app_tree = tree:add("Application Data")
    local app_len = buffer:len() - offset
    
    app_tree:add(string.format("Length: %d bytes", app_len))
    
    -- Try to identify protocol by port
    local known_port = nil
    if ports then
        if ports.port_src == 80 or ports.port_dst == 80 then
            known_port = "HTTP"
        elseif ports.port_src == 443 or ports.port_dst == 443 then
            known_port = "HTTPS"
        elseif ports.port_src == 53 or ports.port_dst == 53 then
            known_port = "DNS"
        elseif ports.port_src == 21 or ports.port_dst == 21 then
            known_port = "FTP (Control)"
        elseif ports.port_src == 20 or ports.port_dst == 20 then
            known_port = "FTP (Data)"
        elseif ports.port_src == 25 or ports.port_dst == 25 then
            known_port = "SMTP"
        elseif ports.port_src == 110 or ports.port_dst == 110 then
            known_port = "POP3"
        elseif ports.port_src == 23 or ports.port_dst == 23 then
            known_port = "Telnet"
        elseif ports.port_src == 22 or ports.port_dst == 22 then
            known_port = "SSH"
        end
    end
    
    if known_port then
        app_tree:add(string.format("Probable Protocol: %s", known_port))
    end
    
    -- Show first bytes in hexadecimal
    local max_show = math.min(app_len, 32)  -- Show maximum 32 bytes
    local payload_hex = ""
    for i = offset, offset + max_show - 1 do
        payload_hex = payload_hex .. string.format("%02X ", buffer(i,1):uint())
    end
    
    if max_show < app_len then
        payload_hex = payload_hex .. "..."
    end
    
    app_tree:add(string.format("Payload (Hex): %s", payload_hex))
    
    -- Attempt to show as ASCII
    local payload_ascii = ""
    for i = offset, offset + max_show - 1 do
        local b = buffer(i,1):uint()
        if b >= 32 and b <= 126 then
            payload_ascii = payload_ascii .. string.char(b)
        else
            payload_ascii = payload_ascii .. "."
        end
    end
    
    if max_show < app_len then
        payload_ascii = payload_ascii .. "..."
    end
    
    app_tree:add(string.format("Payload (ASCII): %s", payload_ascii))
end

-- Function to make a detailed breakdown of the packet
local function breakdown(buffer, tree)
    -- Step 1: Analyze Ethernet header
    local eth_type, offset = analyze_ethernet(buffer, tree)
    if not eth_type then return end
    
    -- Step 2: Analyze according to Ethernet type
    local next_proto = nil
    local next_offset = offset
    local ports = nil
    
    if eth_type == 0x0800 then  -- IPv4
        next_proto, next_offset = analyze_ipv4(buffer, tree, offset)
        
        -- Step 3: Analyze transport layer protocol
        if next_proto == 6 then  -- TCP
            ports, next_offset = analyze_tcp(buffer, tree, next_offset)
        elseif next_proto == 17 then  -- UDP
            ports, next_offset = analyze_udp(buffer, tree, next_offset)
        end
        
        -- Step 4: Analyze application data
        analyze_application(buffer, tree, next_offset, ports)
        
    elseif eth_type == 0x0806 then  -- ARP
        tree:add("ARP Packet - Analysis not implemented")
    elseif eth_type == 0x86DD then  -- IPv6
        tree:add("IPv6 Packet - Analysis not implemented")
    else
        tree:add(string.format("Unknown protocol (0x%04X) - Analysis not implemented", eth_type))
    end
end

-- Variable to count processed packets
local packets_processed = 0

-- Main dissector function
function simple_trans.dissector(tvb, pinfo, tree)
    -- Increment packet counter
    packets_processed = packets_processed + 1
    
    -- Add to main tree
    local simple_tree = tree:add(simple_trans, tvb(), "Transcriptor")
    
    -- If we have data, display it
    if tvb:len() > 0 then
        -- Create tree for detailed breakdown
        local breakdown_tree = simple_tree:add(f_breakdown, "Packet Breakdown")
        
        -- Break down the packet
        breakdown(tvb, breakdown_tree)
        
        -- Add additional debug information
        simple_tree:add("Packet length: " .. tvb:len() .. " bytes")
    else
        simple_tree:add("No data to display")
    end
    
    -- We don't consume the packet, allow other dissectors to process it
    return false
end

-- Register as post-dissector (runs for all packets)
register_postdissector(simple_trans)