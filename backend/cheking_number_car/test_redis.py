import redis

r = redis.Redis(host='localhost', port=6379, db=0, socket_timeout=5)
r.ping()
print("OK")
