from itsdangerous import TimedJSONWebSignatureSerializer


def issue(payload: dict, secret: str) -> str:
    serializer = TimedJSONWebSignatureSerializer(secret, expires_in=3600)
    token = serializer.dumps(payload)
    if isinstance(token, bytes):
        return token.decode()
    return token


def read(token: str, secret: str) -> dict:
    serializer = TimedJSONWebSignatureSerializer(secret, expires_in=3600)
    return serializer.loads(token)
