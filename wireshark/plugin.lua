local p_format = Proto("PacketFormat", "TP1 Packet Format")
-- Campos corregidos (atención al campo 'pr')
local fields = {
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
    sequence_number = ProtoField.uint32("packetformat.sequence_number", "Sequence Number (GBN)", base.DEC),
    ack_number = ProtoField.uint32("packetformat.ack_number", "Acknowledge Number (GBN)", base.DEC),
    data = ProtoField.bytes("packetformat.data", "Data")
}

p_format.fields = fields

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

        -- For GBN protocol, we need to handle sequence and ack numbers
        if protocol_type == 1 then
            if buffer:len() >= data_start + 8 then
                subtree:add(fields.sequence_number, buffer(data_start, 4))
                subtree:add(fields.ack_number, buffer(data_start + 4, 4))

                local seq_num = buffer(data_start, 4):uint()
                local ack_num = buffer(data_start + 4, 4):uint()
                info_string = info_string .. " Seq=" .. seq_num
                if is_ack then
                    info_string = info_string .. " Ack=" .. ack_num
                end

                data_start = data_start + 8
            else
                subtree:add(fields.sequence_number, 0):append_text(" [MISSING]")
                subtree:add(fields.ack_number, 0):append_text(" [MISSING]")
            end
        end

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

local udp_table = DissectorTable.get("udp.port")
for port = 1, 65535 do
    udp_table:add(port, p_format)
end
