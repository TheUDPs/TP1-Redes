local saw_proto_format = Proto("SAWPacketFormat", "SAWproto")
local gbn_proto_format = Proto("GBNPacketFormat", "GBNproto")


-- Campos corregidos (atención al campo 'pr')
local fields_saw = {
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

saw_proto_format.fields = fields_saw


-- Campos para Go-Back-N (GBN)
local fields_gbn = {
    flags = ProtoField.uint16("packetformatgbn.flags", "Flags", base.HEX),
  protocol = ProtoField.uint8("packetformatgbn.protocol", "Protocol", base.DEC, {
        [0] = "Stop-and-Wait",
        [1] = "Go-Back-N"
    }, 0xC0),
    ack = ProtoField.bool("packetformatgbn.ack", "ACK flag", 8, nil, 0x20),  -- Bit 3 (00010000)
    syn = ProtoField.bool("packetformatgbn.syn", "SYN flag", 8, nil, 0x10),  -- Bit 4 (00001000)
    fin = ProtoField.bool("packetformatgbn.fin", "FIN flag", 8, nil, 0x08),  -- Bit 4 (00001000)
    unused = ProtoField.uint16("packetformatgbn.unused", "Unused", base.HEX, nil, 0x3FE0),
    port = ProtoField.uint16("packetformatgbn.port", "Port", base.DEC),
    payload_length = ProtoField.uint32("packetformatgbn.payload_length", "Payload length", base.DEC),
    seq_number = ProtoField.uint32("packetformatgbn.seq_number", "Sequence Number", base.DEC),
    ack_number = ProtoField.uint32("packetformatgbn.ack_number", "Acknowledge Number", base.DEC),
    data = ProtoField.bytes("packetformatgbn.data", "Data")
}

gbn_proto_format.fields = fields_gbn

local function dissect_saw(buffer, pinfo, tree)
    local byte1 = buffer(0, 1):uint()

    local subtree = tree:add(saw_proto_format, buffer(), "SAW Protocol")
    pinfo.cols.protocol = "SAW"
    local info_string = "(SAW)"

    subtree:add(fields_saw.protocol, buffer(0, 1))

    -- Flags individuales
    local is_ack = bit.band(byte1, 0x10) ~= 0
    local is_syn = bit.band(byte1, 0x08) ~= 0
    local is_fin = bit.band(byte1, 0x04) ~= 0

    subtree:add(fields_saw.ack, buffer(0, 1)):append_text(is_ack and " (SET)" or " (NOT SET)")
    subtree:add(fields_saw.syn, buffer(0, 1)):append_text(is_syn and " (SET)" or " (NOT SET)")
    subtree:add(fields_saw.fin, buffer(0, 1)):append_text(is_fin and " (SET)" or " (NOT SET)")

    -- Add flag info to the info column
    if is_syn then info_string = info_string .. " [SYN]" end
    if is_ack then info_string = info_string .. " [ACK]" end
    if is_fin then info_string = info_string .. " [FIN]" end

    pinfo.cols.info = info_string

    -- Sequence number as int (0 or 1)
    local seq_value = bit.band(byte1, 0x20) ~= 0 and 1 or 0
    local seq_item = subtree:add(fields_saw.seq_num, buffer(0, 1))
    seq_item:set_text("Sequence number: " .. seq_value)
    info_string = info_string .. " SEQ=" .. seq_value

    -- Unused bits
    subtree:add(fields_saw.unused, buffer(0, 2))

    -- Puerto y longitud
    subtree:add(fields_saw.port, buffer(2, 2))

    -- Read payload length (should be there even if it's 0)
    local plen_start = 4  -- Payload length starts at byte 4

    -- Make sure we have at least the bytes containing the length field
    if buffer:len() >= plen_start + 2 then
        local plen = buffer(plen_start, 2):uint()
        subtree:add(fields_saw.payload_length, buffer(plen_start, 2))

        -- Check if there's payload data and we have enough bytes to show it
        local data_start = 6  -- Data starts at byte 6 (not 8 as before)

        -- Show payload if it exists and we have enough bytes
        if plen > 0 and buffer:len() >= data_start + plen then
            subtree:add(fields_saw.data, buffer(data_start, plen))
            info_string = info_string .. " Data(" .. plen .. ")"
            pinfo.cols.info = info_string
        elseif plen > 0 then
            -- Payload specified but not enough bytes in packet
            subtree:add(fields_saw.data, buffer(data_start)):append_text(" [TRUNCATED]")
            info_string = info_string .. " Data(" .. plen .. ") [TRUNCATED]"
            pinfo.cols.info = info_string
        end
    else
        -- Not enough bytes for the length field
        subtree:add(fields_saw.payload_length, 0):append_text(" [MISSING]")
    end

end


local function dissect_gbn(buffer, pinfo, tree)
    local subtree = tree:add(gbn_proto_format, buffer(), "GBN Protocol")
    -- Configurar columnas
    pinfo.cols.protocol = "GBN"
    local info_string = "(GBN)"

    -- Protocol type
    subtree:add(fields_gbn.protocol, buffer(0, 1))

    local is_ack = bit.band(buffer(0, 1):uint(), 0x20) ~= 0  -- Bit 5
    local is_syn = bit.band(buffer(0, 1):uint(), 0x10) ~= 0  -- Bit 4
    local is_fin = bit.band(buffer(0, 1):uint(), 0x08) ~= 0  -- Bit 4

    -- Visualización en el árbol (ya correcta)
    subtree:add(fields_gbn.ack, buffer(0, 1)):append_text(is_ack and " (SET)" or " (NOT SET)")
    subtree:add(fields_gbn.syn, buffer(0, 1)):append_text(is_syn and " (SET)" or " (NOT SET)")
    subtree:add(fields_gbn.fin, buffer(0, 1)):append_text(is_fin and " (SET)" or " (NOT SET)")

    if is_syn then info_string = info_string .. " [SYN]" end
    if is_ack then info_string = info_string .. " [ACK]" end
    if is_fin then info_string = info_string .. " [FIN]" end

    subtree:add(fields_gbn.unused, buffer(0, 2))

    local port = buffer(2, 2):uint()
    subtree:add(fields_gbn.port, buffer(2, 2))
    --info_string = info_string .. " Port:" .. port

    local payload_length = 0
    if buffer:len() >= 8 then
        payload_length = buffer(4, 4):uint()
        subtree:add(fields_gbn.payload_length, buffer(4, 4))
    else
        subtree:add(fields_gbn.payload_length, 0):append_text(" [MISSING]")
    end

    local seq_num = 0
    if buffer:len() >= 12 then
        seq_num = buffer(8, 4):uint()
        subtree:add(fields_gbn.seq_number, buffer(8, 4))
        info_string = info_string .. " SEQ=" .. seq_num
    else
        subtree:add(fields_gbn.seq_number, 0):append_text(" [MISSING]")
    end

    local ack_num = 0
    if buffer:len() >= 16 then
        ack_num = buffer(12, 4):uint()
        subtree:add(fields_gbn.ack_number, buffer(12, 4))
        info_string = info_string .. " ACK=" .. ack_num
    else
        subtree:add(fields_gbn.ack_number, 0):append_text(" [MISSING]")
    end

    local data_start = 16
    if payload_length > 0 and buffer:len() >= data_start + payload_length then
        subtree:add(fields_gbn.data, buffer(data_start, payload_length))
        info_string = info_string .. " Data(" .. payload_length .. ")"
    elseif payload_length > 0 then
        local available_data = math.max(0, buffer:len() - data_start)
        subtree:add(fields_gbn.data, buffer(data_start, available_data)):append_text(" [TRUNCATED]")
        info_string = info_string .. " Data(" .. payload_length .. ") [TRUNCATED]"
    end

    pinfo.cols.info = info_string
end

-- Disector principal
function gbn_proto_format.dissector(buffer, pinfo, tree)
    if buffer:len() < 2 then
        pinfo.cols.info:set("Packet too short")
        return false
    end

    local protocol_type = bit.rshift(bit.band(buffer(0, 1):uint(), 0xC0), 6)

    if protocol_type == 01 then
        if buffer:len() < 16 then
            pinfo.cols.info:set("Truncated GBN packet")
            return false
        end
        dissect_gbn(buffer, pinfo, tree)
        return true
    else
        return false
    end
end

function saw_proto_format.dissector(buffer, pinfo, tree)
    if buffer:len() < 2 then
        pinfo.cols.info:set("Packet too short")
        return false
    end

    local protocol_type = bit.rshift(bit.band(buffer(0, 1):uint(), 0xC0), 6)
    if protocol_type == 00 then
        if buffer:len() < 6 then
            pinfo.cols.info:set("Truncated SAW packet")
            return false
        end
        dissect_saw(buffer, pinfo, tree)
        return true

    elseif protocol_type == 01 then
        if buffer:len() < 16 then
            pinfo.cols.info:set("Truncated GBN packet")
            return false
        end
        dissect_gbn(buffer, pinfo, tree)
        return true
    else
        return false
    end
end

-- Define coloring rules
local function set_color_filter_rules_saw()
    local colorfilters = {
        { "SAW SYN packets", "packetformatsaw.syn == 1", "Green",  "Black" },
        { "SAW ACK packets", "packetformatsaw.ack == 1", "Yellow", "Black" },
        { "SAW FIN packets", "packetformatsaw.fin == 1", "Red",    "Black" },
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

-- Define coloring rules
local function set_color_filter_rules_gbn()
    local colorfilters = {
        { "SYN packets", "packetformatgbn.syn == 1", "Green",  "Black" },
        { "ACK packets", "packetformatgbn.ack == 1", "Yellow", "Black" },
        { "FIN packets", "packetformatgbn.fin == 1", "Red",    "Black" },
    }

    local colorfile = Dir.personal_config_path() .. "colorfilters"
    local file = io.open(colorfile, "r")
    if file then
        file:close()
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
register_menu("Add GBN Coloring Rules", set_color_filter_rules_gbn, MENU_TOOLS_UNSORTED)

-- Register for initialization after Wireshark loads
register_menu("Add SAW Coloring Rules", set_color_filter_rules_saw, MENU_TOOLS_UNSORTED)

local udp_table = DissectorTable.get("udp.port")
for port = 1, 65535 do
    udp_table:add(port, gbn_proto_format)
    udp_table:add(port, saw_proto_format)

end
