import grpc
import socket
import os
from service_discovery_pb2 import RegisterRequest
from service_discovery_pb2_grpc import ServiceDiscoveryStub


def register_service(service_type, sd_host, sd_port):
    # Get the local service IP address
    local_ip = socket.gethostbyname(socket.gethostname())
    
    # Create a gRPC channel
    with grpc.insecure_channel(f'{sd_host}:{sd_port}') as channel:
        stub = ServiceDiscoveryStub(channel)
        request = RegisterRequest(serviceType=service_type, ip=local_ip)

        # Register the service
        response = stub.Register(request)
        if response.success:
            print(f"SUCCESS: Successfully registered service '{service_type}' with IP '{local_ip}'")
        else:
            print(f"FAILURE: Failed to register service '{service_type}': {response.message}")


if __name__ == "__main__":
    # Get service type and discovery server info from environment variables
    SERVICE_TYPE = os.getenv('SERVICE_TYPE')
    SD_HOST = os.getenv('SD_HOST')
    SD_PORT = os.getenv('SD_PORT')
    
    register_service(SERVICE_TYPE, SD_HOST, SD_PORT)