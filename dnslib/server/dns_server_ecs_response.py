#!/usr/bin/env python

import socket

from dnslib import A, AAAA, CNAME, MX, RR, TXT
from dnslib import DNSHeader, DNSRecord, QTYPE, EDNSOption, RR

AF_INET = 2
SOCK_DGRAM = 2


IPV6 = (0,) * 16
# MSG = "gevent_server.py"


def dns_handler(s, peer, data):
    request = DNSRecord.parse(data)
    id = request.header.id
    qname = request.q.qname
    qtype = request.q.qtype
    print "------ Request (%s): %r (%s)" % (str(peer),
            qname.label, QTYPE[qtype])
    print "\n".join([ "  %s" % l for l in str(request).split("\n")])
    print ', '.join(str(x) for x in request.ar)

    def get_ecs_option(req):
        for record in request.ar:
            if type(record) is RR:
                for opt in record.rdata:
                    if type(opt) is EDNSOption:
                        if opt.code == 8:
                            return opt

    def ip_from_edns_subnet(req):
        opt = get_ecs_option(req)
        if opt is not None:
            data = opt.data[4:].ljust(4, '\0')
            data = socket.inet_ntoa(data)
            subnetlen = str(ord(opt.data[2]))
            print "Got ECS:", data, subnetlen
            return [data, data+"/"+subnetlen]
        return ["99.99.99.99", "0/0"]

    [IP, MSG] = ip_from_edns_subnet(request)

    reply = DNSRecord(DNSHeader(id=id, qr=1, aa=1, ra=1), q=request.q)
    if qtype == QTYPE.A:
        reply.add_answer(RR(qname, qtype,       rdata=A(IP)))
    elif qtype == QTYPE.AAAA:
        reply.add_answer(RR(qname, qtype,       rdata=AAAA(IPV6)))
    elif qtype == QTYPE['*']:
        reply.add_answer(RR(qname, QTYPE.A,     rdata=A(IP)))
        reply.add_answer(RR(qname, QTYPE.MX,    rdata=MX(IP)))
        reply.add_answer(RR(qname, QTYPE.TXT,   rdata=TXT(MSG)))
    else:
        reply.add_answer(RR(qname, QTYPE.CNAME, rdata=CNAME(MSG)))

    reply.add_answer(RR(qname, QTYPE.TXT,   rdata=TXT(MSG)))

    print "------ Reply"
    print "\n".join([ "  %s" % l for l in str(reply).split("\n")])

    s.sendto(reply.pack(), peer)

s = socket.socket(AF_INET, SOCK_DGRAM)
s.bind(('', 5053))

while True:
    print "====== Waiting for connection"
    data, peer = s.recvfrom(8192)
    dns_handler(s,peer,data)
