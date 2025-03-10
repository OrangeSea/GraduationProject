from scapy.all import *


class indus_feature_header(Packet):
    fields_desc = [
        BitField('feature_0', 0, 16),
        BitField('feature_1', 0, 16),
        BitField('feature_2', 0, 16),
        BitField('feature_3', 0, 16),
        BitField('feature_4', 0, 16),
        BitField('feature_5', 0, 16),
        BitField('feature_6', 0, 16),
        BitField('feature_7', 0, 16),
    ]
bind_layers(IP, indus_feature_header)