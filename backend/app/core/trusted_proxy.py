from ipaddress import ip_address, ip_network


def client_ip(request, cidrs=""):
    try:
        peer = ip_address(request.client.host) if request.client else None
        trusted = [ip_network(c.strip()) for c in cidrs.split(",") if c.strip()]
        chain = [ip_address(v.strip()) for v in request.headers.get("x-forwarded-for", "").split(",") if v.strip()]
        while peer and any(peer in network for network in trusted) and chain:
            peer = chain.pop()
        return str(peer) if peer else None
    except ValueError:
        return None
