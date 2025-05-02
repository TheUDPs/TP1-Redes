local p_format = Proto("PacketFormatSAW", "TP1 Stop-and-Wait Packet Format")
local p_format_gbn = Proto("PacketFormatGBN", "TP1 Go-Back-N Packet Format")
-- Campos corregidos (atención al campo 'pr')
local fields = {
    flags = ProtoField.uint16("packetformatsaw.flags", "Flags", base.HEX),
    protocol = ProtoField.uint8("packetformatsaw.protocol", "Protocol", base.DEC, {
        [0] = "Stop-and-Wait",
        [1] = "Go-Back-N"
    }, 0xC0),                                                                    -- Máscara para 2 bits (11000000)
    seq_num = ProtoField.uint8("packetformatsaw.seq_num", "Sequence Number", base.DEC, nil, 0x20), -- Changed from bool to uint8
    ack = ProtoField.bool("packetformatsaw.ack", "ACK flag", 8, nil, 0x10),
    syn = ProtoField.bool("packetformatsaw.syn", "SYN flag", 8, nil, 0x08),
    fin = ProtoField.bool("packetformatsaw.fin", "FIN flag", 8, nil, 0x04),
    unused = ProtoField.uint16("packetformatsaw.unused", "Unused", base.HEX, nil, 0x3FF8),
    port = ProtoField.uint16("packetformatsaw.port", "Port", base.DEC),
    payload_length = ProtoField.uint16("packetformatsaw.payload_length", "Payload length", base.DEC),
    data = ProtoField.bytes("packetformatsaw.data", "Data")
}

local fields_gbn = {
    protocol = ProtoField.uint8("packetformatgbn.protocol", "Protocol", base.DEC, {
        [0] = "Stop-and-Wait",
        [1] = "Go-Back-N"
    }, 0xC0),
    syn = ProtoField.bool("packetformatgbn.syn", "SYN flag", 8, nil, 0x08),
    ack = ProtoField.bool("packetformatgbn.ack", "ACK flag", 8, nil, 0x10),
    fin = ProtoField.bool("packetformatgbn.fin", "FIN flag", 8, nil, 0x04),
    unused = ProtoField.uint16("packetformatgbn.unused", "Unused", base.HEX, nil, 0x3FE0),  -- Bits 5-15 (00111111 11100000)
    port = ProtoField.uint16("packetformatgbn.port", "Port", base.DEC),
    payload_length = ProtoField.uint32("packetformatgbn.payload_length", "Payload length", base.DEC),
    sequence_number = ProtoField.uint32("packetformatgbn.sequence_number", "Sequence Number (GBN)", base.DEC),
    ack_number = ProtoField.uint32("packetformatgbn.ack_number", "Acknowledge Number (GBN)", base.DEC),
    data = ProtoField.bytes("packetformatgbn.data", "Data")
}

p_format.fields = fields
p_format_gbn.fields = fields_gbn

-- Define coloring rules
local function set_color_filter_rules()
    local colorfilters = {
        { "SAW SYN packets", "packetformatsaw.syn == 1", "Green",  "Black" },
        { "SAW ACK packets", "packetformatsaw.ack == 1", "Yellow", "Black" },
        { "SAW FIN packets", "packetformatsaw.fin == 1", "Red",    "Black" },
        { "GBN SYN packets", "packetformatgbn.syn == 1", "Green",  "Black" },
        { "GBN ACK packets", "packetformatgbn.ack == 1", "Yellow", "Black" },
        { "GBN FIN packets", "packetformatgbn.fin == 1", "Red",    "Black" },
    }

    -- Find and add the colorfilters file
    local colorfile = Dir.personal_config_path() .. "colorfilters"
    local file = io.open(colorfile, "r")
    if file then
        file:close()
        -- Add our rules to the file
        file = io.open(colorfile, "a")
        if file then
            for _, rule in ipairs(colorfilters) do
                file:write('@"' .. rule[1] .. '" ' .. rule[2] .. ' "' .. rule[3] .. '" "' .. rule[4] .. '"\n')
            end
            file:close()
        end
    end
end

-- Register for initialization after Wireshark loads
register_menu("Add SAW/GBN Coloring Rules", set_color_filter_rules, MENU_TOOLS_UNSORTED)

function p_format.dissector(buffer, pinfo, tree)
    -- Verificación mínima de tamaño (header size is 8 bytes)
    if buffer:len() < 6 then
        return false  -- Not enough bytes for minimum header
    end

    -- Crear árbol de protocolo
    local subtree = tree:add(p_format, buffer(), "SAW")

    -- Leer flags (primeros 2 bytes)
    local byte1 = buffer(0, 1):uint()

    -- Set protocol column
    pinfo.cols.protocol = "SAW"

    -- Set info column with flags info for coloring
    local info_string = "SAW"

    -- Protocol type (bits 7-8)
    subtree:add(fields.protocol, buffer(0, 1))

    -- Sequence number as int (0 or 1)
    local seq_value = bit.band(byte1, 0x20) ~= 0 and 1 or 0
    local seq_item = subtree:add(fields.seq_num, buffer(0, 1))
    seq_item:set_text("Sequence number: " .. seq_value)
    info_string = info_string .. " SEQ=" .. seq_value

    -- Flags individuales
    local is_ack = bit.band(byte1, 0x10) ~= 0
    local is_syn = bit.band(byte1, 0x08) ~= 0
    local is_fin = bit.band(byte1, 0x04) ~= 0

    subtree:add(fields.ack, buffer(0, 1)):append_text(is_ack and " (SET)" or " (NOT SET)")
    subtree:add(fields.syn, buffer(0, 1)):append_text(is_syn and " (SET)" or " (NOT SET)")
    subtree:add(fields.fin, buffer(0, 1)):append_text(is_fin and " (SET)" or " (NOT SET)")

    -- Add flag info to the info column
    if is_syn then info_string = info_string .. " SYN" end
    if is_ack then info_string = info_string .. " ACK" end
    if is_fin then info_string = info_string .. " FIN" end

    pinfo.cols.info = info_string

    -- Unused bits
    subtree:add(fields.unused, buffer(0, 2))

    -- Puerto y longitud
    subtree:add(fields.port, buffer(2, 2))

    -- Read payload length (should be there even if it's 0)
    local plen_start = 4  -- Payload length starts at byte 4

    -- Make sure we have at least the bytes containing the length field
    if buffer:len() >= plen_start + 2 then
        local plen = buffer(plen_start, 2):uint()
        subtree:add(fields.payload_length, buffer(plen_start, 2))

        -- Check if there's payload data and we have enough bytes to show it
        local data_start = 6  -- Data starts at byte 6 (not 8 as before)

        -- Show payload if it exists and we have enough bytes
        if plen > 0 and buffer:len() >= data_start + plen then
            subtree:add(fields.data, buffer(data_start, plen))
            info_string = info_string .. " Data(" .. plen .. ")"
            pinfo.cols.info = info_string
        elseif plen > 0 then
            -- Payload specified but not enough bytes in packet
            subtree:add(fields.data, buffer(data_start)):append_text(" [TRUNCATED]")
            info_string = info_string .. " Data(" .. plen .. ") [TRUNCATED]"
            pinfo.cols.info = info_string
        end
    else
        -- Not enough bytes for the length field
        subtree:add(fields.payload_length, 0):append_text(" [MISSING]")
    end

    return true
end

-- GBN Protocol Dissector Implementation
function p_format_gbn.dissector(buffer, pinfo, tree)
    if buffer:len() < 6 then
        return false
    end

    -- Check protocol type in the first byte (bits 7-8)
    local byte1 = buffer(0, 1):uint()
    local protocol_type = bit.rshift(bit.band(byte1, 0xC0), 6)

    -- Only process if it's a GBN packet (protocol = 1)
    if protocol_type ~= 1 then
        return false
    end

    -- Crear árbol de protocolo
    local subtree = tree:add(p_format_gbn, buffer(), "GBN")

    -- Set protocol column
    pinfo.cols.protocol = "GBN"

    -- Set info column with flags info for coloring
    local info_string = "GBN"

    -- Protocol type (bits 7-8)
    subtree:add(fields_gbn.protocol, buffer(0, 1))

    -- Flags individuales
    local is_ack = bit.band(byte1, 0x10) ~= 0
    local is_syn = bit.band(byte1, 0x08) ~= 0
    local is_fin = bit.band(byte1, 0x04) ~= 0

    subtree:add(fields_gbn.ack, buffer(0, 1)):append_text(is_ack and " (SET)" or " (NOT SET)")
    subtree:add(fields_gbn.syn, buffer(0, 1)):append_text(is_syn and " (SET)" or " (NOT SET)")
    subtree:add(fields_gbn.fin, buffer(0, 1)):append_text(is_fin and " (SET)" or " (NOT SET)")

    -- Add flag info to the info column
    if is_syn then info_string = info_string .. " SYN" end
    if is_ack then info_string = info_string .. " ACK" end
    if is_fin then info_string = info_string .. " FIN" end

    pinfo.cols.info = info_string

    -- Unused bits
    subtree:add(fields_gbn.unused, buffer(0, 2))

    -- Port
    subtree:add(fields_gbn.port, buffer(2, 2))

    -- Sequence Number (4 bytes)
    local seq_num = buffer(4, 4):uint()
    subtree:add(fields_gbn.sequence_number, buffer(4, 4))
    info_string = info_string .. " SEQ=" .. seq_num

    -- Acknowledge Number (4 bytes)
    local ack_num = buffer(8, 4):uint()
    subtree:add(fields_gbn.ack_number, buffer(8, 4))
    if is_ack then
        info_string = info_string .. " ACK=" .. ack_num
    end

    -- Payload Length (4 bytes)
    local plen = buffer(12, 4):uint()
    subtree:add(fields_gbn.payload_length, buffer(12, 4))

    pinfo.cols.info = info_string

    -- Check if there's payload data and we have enough bytes to show it
    local data_start = 16  -- Data starts at byte 16 for GBN

    -- Show payload if it exists and we have enough bytes
    if plen > 0 and buffer:len() >= data_start + plen then
        subtree:add(fields_gbn.data, buffer(data_start, plen))
        info_string = info_string .. " Data(" .. plen .. ")"
        pinfo.cols.info = info_string
    elseif plen > 0 then
        -- Payload specified but not enough bytes in packet
        subtree:add(fields_gbn.data, buffer(data_start)):append_text(" [TRUNCATED]")
        info_string = info_string .. " Data(" .. plen .. ") [TRUNCATED]"
        pinfo.cols.info = info_string
    end

    return true
end

-- Function to determine which dissector to use based on the protocol field
local function protocol_dissector(buffer, pinfo, tree)
    if buffer:len() < 1 then
        return false
    end

    -- Check protocol type in the first byte (bits 7-8)
    local byte1 = buffer(0, 1):uint()
    local protocol_type = bit.rshift(bit.band(byte1, 0xC0), 6)

    if protocol_type == 0 then
        return p_format.dissector(buffer, pinfo, tree)
    elseif protocol_type == 1 then
        return p_format_gbn.dissector(buffer, pinfo, tree)
    else
        return false
    end
end

-- Create a proper dissector object from our function
local protocol_dissector_proto = Proto("TP1Protocol", "TP1 Protocol")
function protocol_dissector_proto.dissector(buffer, pinfo, tree)
    return protocol_dissector(buffer, pinfo, tree)
end

-- Register the protocol dissector
local udp_table = DissectorTable.get("udp.port")
for port = 1, 65535 do
    udp_table:add(port, protocol_dissector_proto)
end
