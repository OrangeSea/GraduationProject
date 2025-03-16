/*************************************************************************
*********************** H E A D E R S  ***********************************
*************************************************************************/

const bit<16> TYPE_IPV4 = 0x800;
const bit<8>  TYPE_INDUS = 0x27; 

typedef bit<9>  egressSpec_t;
typedef bit<48> macAddr_t;
typedef bit<32> ip4Addr_t;


header ethernet_t {
    macAddr_t dstAddr;
    macAddr_t srcAddr;
    bit<16>   etherType;
}

header ipv4_t {
    bit<4>    version;
    bit<4>    ihl;
    bit<6>    dscp;
    bit<2>    ecn;
    bit<16>   totalLen;
    bit<16>   identification;
    bit<3>    flags;
    bit<13>   fragOffset;
    bit<8>    ttl;
    bit<8>    protocol;
    bit<16>   hdrChecksum;
    ip4Addr_t srcAddr;
    ip4Addr_t dstAddr;
}

header indus_t {
    bit<16>     feature_0;
    bit<16>     feature_1;
    bit<16>     feature_2;
    bit<16>     feature_3;
    bit<16>     feature_4;
    bit<16>     feature_5;
    bit<16>     feature_6;
    bit<16>     feature_7;
    bit<16>     feature_8;
    bit<16>     feature_9;
    bit<16>     feature_10;
    bit<16>     feature_11;
    bit<16>     feature_12;
    bit<16>     feature_13;
    bit<16>     feature_14;
    bit<8>      result  ;

}

header time_t {
    bit<48> delay;
}

header tcp_t{
    bit<16> srcPort;
    bit<16> dstPort;
    bit<32> seqNo;
    bit<32> ackNo;
    bit<4>  dataOffset;
    bit<4>  res;
    bit<1>  cwr;
    bit<1>  ece;
    bit<1>  urg;
    bit<1>  ack;
    bit<1>  psh;
    bit<1>  rst;
    bit<1>  syn;
    bit<1>  fin;
    bit<16> window;
    bit<16> checksum;
    bit<16> urgentPtr;
}

header udp_t {
    bit<16>  src_port;
    bit<16>  dst_port;
    bit<16>  hdr_length;
    bit<16>  checksum;
}

struct metadata {
    bit<14> ecmp_hash;
    bit<14> ecmp_group_id;
    bit<3>  type;
    bit<1>  is_ingress_border;
    bit<1>  is_egress_border;
}

struct headers {
    ethernet_t   ethernet;
    ipv4_t       ipv4;
    time_t       time;
    indus_t      indus;
    tcp_t        tcp;
    udp_t        udp;
}

