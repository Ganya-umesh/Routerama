import subprocess
import redis
import socket
import time
import re

class BirdRedisInterface:
    def __init__(self, redis_host='redis', redis_port=6379, redis_db=0):
        try:
            self.redis_client = redis.Redis(host=redis_host, port=redis_port, db=redis_db)
            self.redis_client.ping()
            print("Connected to Redis successfully.")
        except redis.ConnectionError as e:
            print(f"Error connecting to Redis: {e}")
            raise

        self.hostname = socket.gethostname()
        self.container_id = self.hostname

    def get_bird_routes(self):
        try:
            result = subprocess.run(['birdc', 'show', 'route'], capture_output=True, text=True, check=True)
            print(f"BIRD route command output: {result.stdout}")
            return result.stdout
        except subprocess.CalledProcessError as e:
            print(f"Error running BIRD route command: {e}")
            return None

    def parse_bird_routes(self, bird_output):
        routes = []
        lines = bird_output.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith('BIRD') or line.startswith('Table'):
                i += 1
                continue

            if line and line[0].isdigit():
                parts = line.split()
                route = {
                    'destination': parts[0],
                    'type': parts[1],
                    'protocol': parts[2].strip('[]'),
                    'status': '*' if '*' in line else ('!' if '!' in line else ''),
                    'metric': None,
                    'next_hop': None,
                    'interface': None,
                    'container': self.container_id
                }

                # Extract metric
                metric_match = re.search(r'\((\d+)\)', line)
                if metric_match:
                    route['metric'] = int(metric_match.group(1))

                # Look for next hop info in the next line
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if next_line.startswith('via'):
                        via_parts = next_line.split()
                        route['next_hop'] = via_parts[1]
                        if len(via_parts) > 3:
                            route['interface'] = via_parts[3]
                        i += 1  # Skip the next line as we've processed it
                    elif next_line.startswith('dev'):
                        dev_parts = next_line.split()
                        route['interface'] = dev_parts[1]
                        i += 1  # Skip the next line as we've processed it

                routes.append(route)
            i += 1

        print(f"Parsed {len(routes)} routes")
        return routes

    def send_routes_to_redis(self, routes):
        pipeline = self.redis_client.pipeline()

        # First, remove all existing routes for this container
        existing_keys = self.redis_client.keys(f"route:{self.container_id}:*")
        if existing_keys:
            pipeline.delete(*existing_keys)
            print(f"Deleted {len(existing_keys)} existing keys")

        for route in routes:
            key = f"route:{self.container_id}:{route['destination']}"
            print(f"Preparing to store route in Redis: {key}")

            # Convert None values to empty strings or appropriate default values
            for k, v in route.items():
                if v is None:
                    route[k] = ''

            # Delete the key if it exists and is not a hash
            if self.redis_client.exists(key):
                key_type = self.redis_client.type(key)
                print(f"Existing key type for {key}: {key_type}")
                if key_type != b'hash':
                    print(f"Deleting non-hash key: {key}")
                    pipeline.delete(key)

            pipeline.hset(key, mapping=route)
            pipeline.expire(key, 60)  # Set expiry to 60 seconds

        print("Executing Redis pipeline")
        pipeline.execute()
        print(f"Sent {len(routes)} routes to Redis from container {self.container_id}")

        # Verify the writes
        for route in routes:
            key = f"route:{self.container_id}:{route['destination']}"
            stored_type = self.redis_client.type(key)
            print(f"Verified key {key} - Type: {stored_type}")
            if stored_type == b'hash':
                stored_data = self.redis_client.hgetall(key)
                print(f"Stored data for {key}: {stored_data}")
            else:
                print(f"WARNING: Key {key} is not a hash!")

        print("Route storage and verification complete")

    def cleanup_via_keys(self):
        via_keys = self.redis_client.keys(f"route:{self.container_id}:via")
        if via_keys:
            self.redis_client.delete(*via_keys)
        print(f"Cleaned up {len(via_keys)} 'via' keys")

    def run(self):
        while True:
            print("Fetching BIRD routes...")
            route_output = self.get_bird_routes()
            if route_output:
                print("Routes fetched successfully, parsing...")
                routes = self.parse_bird_routes(route_output)
                print(f"Parsed routes: {routes}")
                print("Sending routes to Redis...")
                self.send_routes_to_redis(routes)
                self.cleanup_via_keys()
            else:
                print("No routes found or error in getting routes")
            print("Waiting for 30 seconds before next update")
            time.sleep(30)

if __name__ == "__main__":
    try:
        print("Script started")
        interface = BirdRedisInterface()
        interface.run()
    except Exception as e:
        print(f"An error occurred: {e}")

