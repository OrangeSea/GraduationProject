/* -*- P4_16 -*- */
#include <core.p4>
#include <v1model.p4>

//My includes
#include "include/headers.p4"
#include "include/parsers.p4"

register<bit<16>>(15) indus_features;
register<bit<16>>(1)   fwd_packet_cnt;
register<bit<16>>(1)   bwd_packet_cnt;

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

    counter(1024, CounterType.packets) fwd_counter;

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

        // indus_features.write(1, 65535);
        // indus_features.write(3, 65535);
    }

    action set_is_ingress_border(){
        meta.is_ingress_border = (bit<1>)1;
    }

    action set_feature2digest() {
        meta.feature.protocol          = hdr.indus.feature_0    ;
        meta.feature.fwd_pkt_len_min   = hdr.indus.feature_1    ;
        meta.feature.fwd_pkt_len_mean  = hdr.indus.feature_2    ;
        meta.feature.bwd_pkt_len_min   = hdr.indus.feature_3    ;
        meta.feature.bwd_pkt_len_std   = hdr.indus.feature_4    ;
        meta.feature.flow_pkts_s       = hdr.indus.feature_5    ;
        meta.feature.fwd_pkts_s        = hdr.indus.feature_6    ;
        meta.feature.pkt_len_mean      = hdr.indus.feature_7    ;
        meta.feature.pkt_len_std       = hdr.indus.feature_8    ;
        meta.feature.fin_flag_cnt      = hdr.indus.feature_9    ;
        meta.feature.rst_flag_cnt      = hdr.indus.feature_10   ;
        meta.feature.pkt_size_avg      = hdr.indus.feature_11   ;
        meta.feature.fwd_seg_size_avg  = hdr.indus.feature_12   ;
        meta.feature.init_fwd_win_byts = hdr.indus.feature_13   ;
        meta.feature.init_bwd_win_byts = hdr.indus.feature_14   ;

        digest(1, meta.feature);
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
                fwd_counter.count((bit<32>)standard_metadata.ingress_port);
                // 读取数据流中每秒数据包个数
                bit<16> flow_pkt_per_sec;
                indus_features.read(flow_pkt_per_sec, 5);
                hdr.indus.feature_5 = flow_pkt_per_sec;
                // 读取前向数据流中每秒数据包个数
                bit<16> fwd_pkt_per_sec;
                indus_features.read(fwd_pkt_per_sec, 6);
                hdr.indus.feature_6 = fwd_pkt_per_sec;
                if (hdr.indus.isValid()) {
                    if (hdr.ipv4.srcAddr == 0x0a010102 && hdr.ipv4.dstAddr == 0x0a020402) { // 前向数据包最小长度统计
                        bit<16> fwd_packet_min = 0;
                        if (hdr.tcp.isValid()) {
                            if (hdr.tcp.syn == 1) {
                                hdr.indus.feature_13 = hdr.tcp.window;
                                // 初始化前向数据包个数
                                fwd_packet_cnt.write(0, 1);
                            }
                            bit<16> tcp_header_len = (bit<16>)hdr.tcp.dataOffset << 2;
                            fwd_packet_min = (bit<16>)standard_metadata.packet_length - 34 - tcp_header_len;
                        } else if (hdr.udp.isValid()) {
                            fwd_packet_min = (bit<16>)standard_metadata.packet_length - 42;
                        }
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

                        bit<16> bwd_init_win_bytes;
                        indus_features.read(bwd_init_win_bytes, 14);
                        hdr.indus.feature_14 = bwd_init_win_bytes;
                    } else if (hdr.ipv4.srcAddr == 0x0a020402 && hdr.ipv4.dstAddr == 0x0a010102) { // 反向数据包最小长度统计
                        bit<16> bwd_packet_min = 0;
                        if (hdr.tcp.isValid()) {
                            hdr.indus.feature_14 = hdr.tcp.window;
                            bwd_packet_min = (bit<16>)standard_metadata.packet_length - 54;
                        } else if (hdr.udp.isValid()) {
                            bwd_packet_min = (bit<16>)standard_metadata.packet_length - 42;
                        }
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

                        bit<16> fwd_init_win_bytes;
                        indus_features.read(fwd_init_win_bytes, 13);
                        hdr.indus.feature_13 = fwd_init_win_bytes;
                    }
                }
                // 直接从寄存器中读取特征值
                bit<16> feature;
                indus_features.read(feature, 0);
                hdr.indus.feature_0 = feature;

                indus_features.read(feature, 1);
                hdr.indus.feature_1 = feature;

                indus_features.read(feature, 2);
                hdr.indus.feature_2 = feature;

                indus_features.read(feature, 3);
                hdr.indus.feature_3 = feature;

                indus_features.read(feature, 4);
                hdr.indus.feature_4 = feature;

                indus_features.read(feature, 5);
                hdr.indus.feature_5 = feature;

                indus_features.read(feature, 6);
                hdr.indus.feature_6 = feature;

                indus_features.read(feature, 7);
                hdr.indus.feature_7 = feature;

                indus_features.read(feature, 8);
                hdr.indus.feature_8 = feature;

                indus_features.read(feature, 9);
                hdr.indus.feature_9 = feature;

                indus_features.read(feature, 10);
                hdr.indus.feature_10 = feature;

                indus_features.read(feature, 11);
                hdr.indus.feature_11 = feature;

                indus_features.read(feature, 12);
                hdr.indus.feature_12 = feature;

                indus_features.read(feature, 13);
                hdr.indus.feature_13 = feature;

                indus_features.read(feature, 14);
                hdr.indus.feature_14 = feature;

                set_feature2digest();

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
            // if (hdr.ipv4.srcAddr == 0x0a010102 && hdr.ipv4.dstAddr == 0x0a020402) {
            //     indus_features.write(1, (bit<16>)hdr.indus.feature_1);
            //     bit<16> length;
            //     indus_features.read(length, 3);
            //     hdr.indus.feature_3 = length;

            //     // 写入FWD init win Bytes
            //     indus_features.write(13, (bit<16>)hdr.indus.feature_13);
            // } else if (hdr.ipv4.srcAddr == 0x0a020402 && hdr.ipv4.dstAddr == 0x0a010102) {
            //     indus_features.write(3, (bit<16>)hdr.indus.feature_3);
            //     bit<16> length;
            //     indus_features.read(length, 1);
            //     hdr.indus.feature_1 = length;

            //     // 写入BWD init win Bytes
            //     indus_features.write(14, (bit<16>)hdr.indus.feature_14);
            // }
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