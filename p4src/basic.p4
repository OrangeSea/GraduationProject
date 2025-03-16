/* -*- P4_16 -*- */
#include <core.p4>
#include <v1model.p4>

//My includes
#include "include/headers.p4"
#include "include/parsers.p4"

register<bit<16>>(15) indus_features;

/*************************************************************************
************   C H E C K S U M    V E R I F I C A T I O N   *************
*************************************************************************/

control MyVerifyChecksum(inout headers hdr, inout metadata meta) {
    apply {  }
}

/*************************************************************************
**************  I N G R E S S   P R O C E S S I N G   *******************
*************************************************************************/

control MyIngress(inout headers hdr,
                  inout metadata meta,
                  inout standard_metadata_t standard_metadata) {

    // register<bit<16>>(15) indus_features;

    action drop() {
        mark_to_drop(standard_metadata);
    }

    action ecmp_group(bit<14> ecmp_group_id, bit<16> num_nhops){
        hash(meta.ecmp_hash,
	    HashAlgorithm.crc16,
	    (bit<1>)0,
	    { hdr.ipv4.srcAddr,
	      hdr.ipv4.dstAddr,
          hdr.tcp.srcPort,
          hdr.tcp.dstPort,
          hdr.ipv4.protocol},
	    num_nhops);

	    meta.ecmp_group_id = ecmp_group_id;
    }

    action set_nhop(macAddr_t dstAddr, egressSpec_t port) {
        //set the src mac address as the previous dst, this is not correct right?
        hdr.ethernet.srcAddr = hdr.ethernet.dstAddr;

       //set the destination mac address that we got from the match in the table
        hdr.ethernet.dstAddr = dstAddr;

        //set the output port that we also get from the table
        standard_metadata.egress_spec = port;

        //decrease ttl by 1
        hdr.ipv4.ttl = hdr.ipv4.ttl - 1;
    }

    action set_indus_feature() {
        indus_features.write(0, (bit<16>)hdr.ipv4.protocol);
        hdr.indus.setValid();
        hdr.ipv4.protocol = 27;
        bit<16> protocol;
        indus_features.read(protocol, 0);
        hdr.indus.feature_0 = protocol;

        indus_features.write(1, 65535);
        indus_features.write(3, 65535);
    }

    action set_is_ingress_border(){
        meta.is_ingress_border = (bit<1>)1;
    }

    table ecmp_group_to_nhop {
        key = {
            meta.ecmp_group_id:    exact;
            meta.ecmp_hash: exact;
        }
        actions = {
            drop;
            set_nhop;
        }
        size = 1024;
    }

    table ipv4_lpm {
        key = {
            hdr.ipv4.dstAddr: lpm;
        }
        actions = {
            set_nhop;
            ecmp_group;
            drop;
        }
        size = 1024;
        default_action = drop;
    }

    table set_indus_valid{
        actions = {
            set_indus_feature;
            drop;
        }
        key = {
            hdr.ipv4.dstAddr: exact;
        }
        size = 1024;
        default_action = drop;
    }

    table check_is_ingress_border {
        actions = {
            NoAction;
            set_is_ingress_border;
        }
        key = {
            standard_metadata.ingress_port: exact;
        }
        size = 1024;
        default_action = NoAction;
    }

    apply {
        check_is_ingress_border.apply();

        if (meta.is_ingress_border == 1) {
            if (hdr.ipv4.isValid()) {
                set_indus_valid.apply();
                if (hdr.indus.isValid()) {
                    if (hdr.ipv4.srcAddr == 0x0a010102 && hdr.ipv4.dstAddr == 0x0a020402) { // 前向数据包最小长度统计
                        bit<16> fwd_packet_min = (bit<16>)standard_metadata.packet_length;
                        bit<16> length;
                        indus_features.read(length, 1);
                        if (fwd_packet_min < length) {
                            indus_features.write(1, fwd_packet_min);
                        } else {
                            fwd_packet_min = length;
                        }
                        hdr.indus.feature_1 = fwd_packet_min;

                        bit<16> bwd_packet_min;
                        indus_features.read(bwd_packet_min, 3);
                        hdr.indus.feature_3 = bwd_packet_min;
                    } else if (hdr.ipv4.srcAddr == 0x0a020402 && hdr.ipv4.dstAddr == 0x0a010102) { // 反向数据包最小长度统计
                        bit<16> bwd_packet_min = (bit<16>)standard_metadata.packet_length;
                        bit<16> length;
                        indus_features.read(length, 3);
                        if (bwd_packet_min < length) {
                            indus_features.write(3, bwd_packet_min);
                        } else {
                            bwd_packet_min = length;
                        }
                        hdr.indus.feature_3 = bwd_packet_min;

                        bit<16> fwd_packet_min;
                        indus_features.read(fwd_packet_min, 1);
                        hdr.indus.feature_1 = fwd_packet_min;
                    }
                }
            }
        }
        if (hdr.ipv4.isValid()){
            switch (ipv4_lpm.apply().action_run){
                ecmp_group: {
                    ecmp_group_to_nhop.apply();
                }
            }
        }


    }
}

/*************************************************************************
****************  E G R E S S   P R O C E S S I N G   *******************
*************************************************************************/

control MyEgress(inout headers hdr,
                 inout metadata meta,
                 inout standard_metadata_t standard_metadata) {

    // register<bit<16>>(15) indus_features;
    action drop() {
        mark_to_drop(standard_metadata);
    }

    action is_egress_border() {
        indus_features.write(0, (bit<16>)hdr.indus.feature_0);

        hdr.indus.setInvalid();
        bit<16> protocol;
        indus_features.read(protocol, 0);
        hdr.ipv4.protocol = (bit<8>)protocol;
        meta.is_egress_border = 1;
    }

    table check_is_egress_border {
        key = {
            standard_metadata.egress_port: exact;
        }
        actions = {
            NoAction;
            is_egress_border;
        }
        default_action = NoAction;
        size = 1024;
    }


    apply {
        if (hdr.indus.isValid()) {
            indus_features.write(1, (bit<16>)hdr.indus.feature_1);
            indus_features.write(3, (bit<16>)hdr.indus.feature_3);
            check_is_egress_border.apply();
        }
    }
}

/*************************************************************************
*************   C H E C K S U M    C O M P U T A T I O N   **************
*************************************************************************/

control MyComputeChecksum(inout headers hdr, inout metadata meta) {
     apply {
	update_checksum(
	    hdr.ipv4.isValid(),
            { hdr.ipv4.version,
	          hdr.ipv4.ihl,
              hdr.ipv4.dscp,
              hdr.ipv4.ecn,
              hdr.ipv4.totalLen,
              hdr.ipv4.identification,
              hdr.ipv4.flags,
              hdr.ipv4.fragOffset,
              hdr.ipv4.ttl,
              hdr.ipv4.protocol,
              hdr.ipv4.srcAddr,
              hdr.ipv4.dstAddr },
              hdr.ipv4.hdrChecksum,
              HashAlgorithm.csum16);
    }
}

/*************************************************************************
***********************  S W I T C H  *******************************
*************************************************************************/

//switch architecture
V1Switch(
MyParser(),
MyVerifyChecksum(),
MyIngress(),
MyEgress(),
MyComputeChecksum(),
MyDeparser()
) main;