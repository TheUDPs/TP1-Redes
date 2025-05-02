local p_format = Proto("PacketFormat", "TP1 Packet Format")
-- Campos corregidos (atención al campo 'pr')
local fields_saw = {
    flags = ProtoField.uint16("packetformat.flags", "Flags", base.HEX),
    protocol = ProtoField.uint8("packetformat.protocol", "Protocol", base.DEC, {
        [0] = "Stop-and-Wait",
        [1] = "Go-Back-N"
    }, 0xC0),                                                                    -- Máscara para 2 bits (11000000)
    seq_num = ProtoField.uint8("packetformat.seq_num", "Sequence Number", base.DEC, nil, 0x20), -- Changed from bool to uint8
    ack = ProtoField.bool("packetformat.ack", "ACK flag", 8, nil, 0x10),
    syn = ProtoField.bool("packetformat.syn", "SYN flag", 8, nil, 0x08),
    fin = ProtoField.bool("packetformat.fin", "FIN flag", 8, nil, 0x04),
    unused = ProtoField.uint16("packetformat.unused", "Unused", base.HEX, nil, 0x3FF8),
    port = ProtoField.uint16("packetformat.port", "Port", base.DEC),
    payload_length = ProtoField.uint16("packetformat.payload_length", "Payload length", base.DEC),
    data = ProtoField.bytes("packetformat.data", "Data")
}

local fields_gbn = {
    protocol = ProtoField.uint8("packetformat.protocol", "Protocol", base.DEC, {
        [0] = "Stop-and-Wait",
        [1] = "Go-Back-N"
    }, 0xC0),  -- Bits 0-1 (11000000)
    syn = ProtoField.bool("packetformat.syn", "SYN flag", 8, nil, 0x08),  
    ack = ProtoField.bool("packetformat.ack", "ACK flag", 8, nil, 0x10),  
    fin = ProtoField.bool("packetformat.fin", "FIN flag", 8, nil, 0x04),  
    unused = ProtoField.uint16("packetformat.unused", "Unused", base.HEX, nil, 0x3FE0),  -- Bits 5-15 (00111111 11100000)
    port = ProtoField.uint16("packetformat.port", "Port", base.DEC),  
    payload_length = ProtoField.uint32("packetformat.payload_length", "Payload length", base.DEC),
    sequence_number = ProtoField.uint32("packetformat.sequence_number", "Sequence Number (GBN)", base.DEC),
    ack_number = ProtoField.uint32("packetformat.ack_number", "Acknowledge Number (GBN)", base.DEC),
    data = ProtoField.bytes("packetformat.data", "Data")
}

-- Define coloring rules
local function set_color_filter_rules()
    local colorfilters = {
        { "SYN packets", "packetformat.syn == 1", "Green",  "Black" },
        { "ACK packets", "packetformat.ack == 1", "Yellow", "Black" },
        { "FIN packets", "packetformat.fin == 1", "Red",    "Black" },
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
register_menu("Add Coloring Rules", set_color_filter_rules, MENU_TOOLS_UNSORTED)

function p_format.dissector(buffer, pinfo, tree)
    -- Verificación mínima de tamaño (header size is 8 bytes)
    if buffer:len() < 6 then
        return false  -- Not enough bytes for minimum header
    end

    -- Crear árbol de protocolo
    local protocol_type = bit.rshift(bit.band(buffer(0, 1):uint(), 0xC0), 6)
    local protocol_name = protocol_type == 0 and "SAW" or "GBN"

    if protocol_name == "SAW" then
        p_format.fields = fields_saw
        p_format_saw.dissector(buffer, pinfo, tree, protocol_name)
    elseif protocol_name == "GBN" then
        p_format.fields = fields_gbn
        p_format_gbn.dissector(buffer, pinfo, tree, protocol_name)
    return true
end

function p_format_saw.dissector(buffer, pinfo, tree, protocol_name)
    local subtree = tree:add(p_format, buffer(), protocol_name)

    -- Leer flags (primeros 2 bytes)
    local byte1 = buffer(0, 1):uint()

    -- Set protocol column
    pinfo.cols.protocol = protocol_name

    -- Set info column with flags info for coloring
    local info_string = protocol_name

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

        local data_start = 6

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
end

function p_format_gbn.dissector(buffer, pinfo, tree, protocol_name)
    local subtree = tree:add(p_format, buffer(), protocol_name)

    -- Set protocol column
    pinfo.cols.protocol = protocol_name

    -- Start building info string for packet details
    local info_string = protocol_name

    -- First 32-bit word (bytes 0-3)
    local flags_word = buffer(0, 4):uint()

    -- Protocol type (bits 0-1)
    subtree:add(fields_gbn.protocol, buffer(0, 1))

    -- Flags (bits 2-4)
    local is_syn = bit.band(buffer(0, 1):uint(), 0x08) ~= 0
    local is_ack = bit.band(buffer(0, 1):uint(), 0x10) ~= 0
    local is_fin = bit.band(buffer(0, 1):uint(), 0x04) ~= 0

    subtree:add(fields_gbn.syn, buffer(0, 1)):append_text(is_syn and " (SET)" or " (NOT SET)")
    subtree:add(fields_gbn.ack, buffer(0, 1)):append_text(is_ack and " (SET)" or " (NOT SET)")
    subtree:add(fields_gbn.fin, buffer(0, 1)):append_text(is_fin and " (SET)" or " (NOT SET)")

    -- Add flag info to the info column
    if is_syn then info_string = info_string .. " SYN" end
    if is_ack then info_string = info_string .. " ACK" end
    if is_fin then info_string = info_string .. " FIN" end

    -- Unused bits (bits 5-15)
    subtree:add(fields_gbn.unused, buffer(0, 2))

    -- Port (bits 16-31)
    local port = buffer(2, 2):uint()
    subtree:add(fields_gbn.port, buffer(2, 2))
    info_string = info_string .. " Port:" .. port

    -- Second 32-bit word: Payload length (bytes 4-7)
    local payload_length = 0
    if buffer:len() >= 8 then
        payload_length = buffer(4, 4):uint()
        subtree:add(fields_gbn.payload_length, buffer(4, 4))
    else
        subtree:add(fields_gbn.payload_length, 0):append_text(" [MISSING]")
    end

    -- Third 32-bit word: Sequence number (bytes 8-11)
    local seq_num = 0
    if buffer:len() >= 12 then
        seq_num = buffer(8, 4):uint()
        subtree:add(fields_gbn.sequence_number, buffer(8, 4))
        info_string = info_string .. " SEQ=" .. seq_num
    else
        subtree:add(fields_gbn.sequence_number, 0):append_text(" [MISSING]")
    end

    -- Fourth 32-bit word: Acknowledge number (bytes 12-15)
    local ack_num = 0
    if buffer:len() >= 16 then
        ack_num = buffer(12, 4):uint()
        subtree:add(fields_gbn.ack_number, buffer(12, 4))
        info_string = info_string .. " ACK=" .. ack_num
    else
        subtree:add(fields_gbn.ack_number, 0):append_text(" [MISSING]")
    end

    -- Data (starts at byte 16)
    local data_start = 16
    if payload_length > 0 and buffer:len() >= data_start + payload_length then
        subtree:add(fields_gbn.data, buffer(data_start, payload_length))
        info_string = info_string .. " Data(" .. payload_length .. ")"
    elseif payload_length > 0 then
        -- Payload specified but not enough bytes in packet
        local available_data = math.max(0, buffer:len() - data_start)
        subtree:add(fields_gbn.data, buffer(data_start, available_data)):append_text(" [TRUNCATED]")
        info_string = info_string .. " Data(" .. payload_length .. ") [TRUNCATED]"
    end

    -- Update packet info column
    pinfo.cols.info = info_string
end

local udp_table = DissectorTable.get("udp.port")
for port = 1, 65535 do
    udp_table:add(port, p_format)
end
