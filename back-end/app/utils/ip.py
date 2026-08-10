from fastapi import Request


def get_client_ip(request: Request) -> str:
    """Extract the client's public IP address from the request.

    Checks ``X-Forwarded-For`` first (for reverse proxy / load balancer
    scenarios), falling back to ``Request.client.host``.
    """
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        # X-Forwarded-For may contain a comma-separated list of IPs;
        # the first one is the original client.
        return forwarded_for.split(",")[0].strip()

    if request.client:
        return request.client.host

    return ""
