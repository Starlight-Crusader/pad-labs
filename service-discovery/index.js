const grpc = require('@grpc/grpc-js');
const protoLoader = require('@grpc/proto-loader');
const redis = require('redis');

// Load environment variables
require('dotenv').config();

const PORT = process.env.PORT;
const SM_REDIS_URL = process.env.SM_REDIS_URL;

// Connect to Redis
const redisClient = redis.createClient({ url: SM_REDIS_URL });
redisClient.connect();

// Load protobuf
const PROTO_PATH = './service_discovery.proto';
const packageDefinition = protoLoader.loadSync(PROTO_PATH, {});
const discoveryProto = grpc.loadPackageDefinition(packageDefinition).discovery;

// gRPC Server for service discovery
function registerService(call, callback) {
    const { serviceType, ip } = call.request;
    const redisKey = `service:${serviceType}`;
    
    redisClient.lPush(redisKey, ip)
        .then(() => {
            console.log(`Registered ${redisKey} at IP - ${ip}`);
            callback(null, { success: true, detail: `Service ${serviceType} registered successfully.` });
        })
        .catch(err => {
            console.error('Redis error:', err);
            callback(null, { success: false, detail: 'Failed to register service.' });
        });
}

// Create gRPC server
function startGrpcServer() {
    const server = new grpc.Server();
    server.addService(discoveryProto.ServiceDiscovery.service, { Register: registerService });
    server.bindAsync(`0.0.0.0:${PORT}`, grpc.ServerCredentials.createInsecure(), () => {
        console.log(`gRPC service discovery running at http://0.0.0.0:${PORT}`);
        server.start();
    });
}

// Graceful Shutdown
async function shutdown(signal) {
    console.log(`Received ${signal}. Shutting down gracefully...`);
    
    // Stop accepting new gRPC requests
    server.tryShutdown(async (err) => {
        if (err) {
            console.error('Error shutting down gRPC server:', err);
        } else {
            console.log('gRPC server stopped accepting new requests.');
        }
        
        // Close Redis connection
        try {
            await redisClient.quit();
            console.log('Redis client disconnected.');
        } catch (redisErr) {
            console.error('Error disconnecting Redis client:', redisErr);
        }

        // Exit process after graceful shutdown
        process.exit(0);
    });
}

// Listen for shutdown signals (e.g., SIGINT for Ctrl+C, SIGTERM for Docker stop)
['SIGINT', 'SIGTERM'].forEach(signal => process.on(signal, () => shutdown(signal)));

startGrpcServer();