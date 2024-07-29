import redis
import socket
import subprocess
import tempfile

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

    def add_route(self, destination, next_hop):
        key = f"route:{self.container_id}:{destination}"
        route_info = {
            'destination': destination,
            'next_hop': next_hop,
            'container': self.container_id,
            'protocol': 'static'
        }

        # Store the route in Redis as a hash
        for field, value in route_info.items():
            self.redis_client.hset(key, field, value)
        self.redis_client.expire(key, 60)  # Set expiry to 60 seconds

        print(f"Route to {destination} added successfully to Redis.")

        # Update bird.conf
        self.update_bird_conf(destination, next_hop)

    def update_bird_conf(self, destination, next_hop):
        # Read the current bird.conf
        with open("/etc/bird/bird.conf", "r") as f:
            bird_conf = f.readlines()

        static_section_start = -1
        static_section_end = -1

        for i, line in enumerate(bird_conf):
            if 'protocol static' in line:
                static_section_start = i
            if static_section_start != -1 and '}' in line:
                static_section_end = i
                break

        if static_section_start == -1 or static_section_end == -1:
            print("Error: Could not find the static protocol section in bird.conf.")
            return

        # Prepare the new route line
        new_route_line = f"    route {destination} via {next_hop};\n"

        # Insert the new route into the static protocol section
        bird_conf.insert(static_section_end, new_route_line)

        # Write the updated bird.conf to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, mode='w') as temp_file:
            temp_file.writelines(bird_conf)
            temp_file_path = temp_file.name

        # Replace the original bird.conf with the updated one
        subprocess.run(["mv", temp_file_path, "/etc/bird/bird.conf"])

        # Reconfigure BIRD with the new configuration
        result = subprocess.run(["birdc", "configure"], capture_output=True, text=True)
        if result.returncode == 0:
            print("BIRD configuration reloaded successfully.")
        else:
            print(f"Error reloading BIRD configuration: {result.stderr}")

    def delete_route(self, destination):
        key = f"route:{self.container_id}:{destination}"
        if self.redis_client.exists(key):
            route = self.redis_client.hgetall(key)
            print(f"Deleting route from Redis: {route}")

            self.redis_client.delete(key)
            if not self.redis_client.exists(key):
                print(f"Route to {destination} deleted successfully from Redis.")
            else:
                print(f"Error: Route to {destination} still exists in Redis.")

            # Remove the route from BIRD configuration
            self.remove_route_from_bird(destination)
        else:
            print(f"Error: Route to {destination} does not exist in Redis.")
            return False

    def remove_route_from_bird(self, destination):
        # Read the current bird.conf
        with open("/etc/bird/bird.conf", "r") as f:
            bird_conf = f.readlines()

        static_section_start = -1
        static_section_end = -1

        for i, line in enumerate(bird_conf):
            if 'protocol static' in line:
                static_section_start = i
            if static_section_start != -1 and '}' in line:
                static_section_end = i
                break

        if static_section_start == -1 or static_section_end == -1:
            print("Error: Could not find the static protocol section in bird.conf.")
            return

        # Find and remove the route line
        route_found = False
        for i in range(static_section_start, static_section_end):
            if f"route {destination}" in bird_conf[i]:
                del bird_conf[i]
                route_found = True
                break

        if not route_found:
            print(f"Route to {destination} not found in BIRD configuration.")
            return

        # Write the updated bird.conf to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, mode='w') as temp_file:
            temp_file.writelines(bird_conf)
            temp_file_path = temp_file.name

        # Replace the original bird.conf with the updated one
        subprocess.run(["mv", temp_file_path, "/etc/bird/bird.conf"])

        # Reconfigure BIRD with the new configuration
        result = subprocess.run(["birdc", "configure"], capture_output=True, text=True)
        if result.returncode == 0:
            print("BIRD configuration reloaded successfully.")
        else:
            print(f"Error reloading BIRD configuration: {result.stderr}")

        print(f"Route to {destination} removed from BIRD configuration.")

    def interactive_mode(self):
        while True:
            print("\nBIRD Redis Interface")
            print("1. Add route")
            print("2. Delete route")
            print("3. Exit")
            choice = input("Enter your choice (1-3): ")

            if choice == '1':
                destination = input("Enter destination: ")
                next_hop = input("Enter next hop: ")
                self.add_route(destination, next_hop)

            elif choice == '2':
                destination = input("Enter destination to delete: ")
                self.delete_route(destination)

            elif choice == '3':
                print("Exiting interactive mode.")
                break

            else:
                print("Invalid choice. Please try again.")

if __name__ == "__main__":
    try:
        print("Script started")
        interface = BirdRedisInterface()
        interface.interactive_mode()
    except Exception as e:
        print(f"An error occurred: {e}")
