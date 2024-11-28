const grpc = require('@grpc/grpc-js');
const protoLoader = require('@grpc/proto-loader');
const redis = require('redis');
const winston = require('winston');

// Load environment variables
require('dotenv').config();

const PORT = process.env.PORT;
const SM_REDIS_URL = process.env.SM_REDIS_URL;

const LOGGING = parseInt(process.env.LOGGING);

// Initialize Winston logger
const logger = winston.createLogger({
    transports: [
        new winston.transports.Console(),
        new winston.transports.File({
            filename: './logs/service_discovery.log',
            level: 'info',
        })
    ],
});

// Quick logs
function logMsg(msg) {
    if (LOGGING) {
        logger.info(JSON.stringify({
            "service": "service_discovery",
            "msg": msg
        }));
    }
}

// Connect to Redis
const redisClient = redis.createClient({ url: SM_REDIS_URL });
redisClient.connect();

// Load protobuf
const PROTO_PATH_DISCOVERY = './service_discovery.proto';
const PROTO_PATH_PING = './ping.proto';
const packageDefinitionDiscovery = protoLoader.loadSync(PROTO_PATH_DISCOVERY, {});
const packageDefinitionPing = protoLoader.loadSync(PROTO_PATH_PING, {});
const discoveryProto = grpc.loadPackageDefinition(packageDefinitionDiscovery).discovery;
const pingProto = grpc.loadPackageDefinition(packageDefinitionPing).ping;

// gRPC Server for service discovery
function registerService(call, callback) {
    const { serviceType, ip } = call.request;
    const redisKey = `service:${serviceType}`;
    
    redisClient.lPush(redisKey, ip)
        .then(() => {
            console.log(`LOG: Registered ${redisKey} at IP - ${ip}`);
            logMsg(`LOG: Registered ${redisKey} at IP - ${ip}`);
            callback(null, { success: true, detail: `Service ${serviceType} registered successfully.` });
        })
        .catch(err => {
            console.error('Redis error:', err);
            logMsg('An error occured. Check container logs');

            callback(null, { success: false, detail: 'Failed to register service.' });
        });
}

// gRPC ping
function ping(call, callback) {
    callback(null, {message: `Service Discovery running at http://0.0.0.0:${PORT} is alive!`})
}

// Create gRPC server
function startGrpcServer() {
    const server = new grpc.Server();
    
    server.addService(pingProto.Ping.service, { Ping: ping });
    server.addService(discoveryProto.ServiceDiscovery.service, { Register: registerService });
    
    server.bindAsync(`0.0.0.0:${PORT}`, grpc.ServerCredentials.createInsecure(), () => {
        console.log(`LOG: gRPC service discovery running at http://0.0.0.0:${PORT}`);
        logMsg(`LOG: gRPC service discovery running at http://0.0.0.0:${PORT}`);

        server.start();
    });

    // Graceful Shutdown
    async function shutdown(signal) {
        console.log(`Received ${signal}. Shutting down gracefully...`);
        
        // Stop accepting new gRPC requests
        server.tryShutdown(async (err) => {
            if (err) {
                console.error('Error shutting down gRPC server:', err);
                logMsg('An error occured. Check container logs');
            } else {
                console.log('gRPC server stopped accepting new requests.');
            }
            
            // Close Redis connection
            try {
                await redisClient.quit();
                console.log('Redis client disconnected.');
            } catch (redisErr) {
                console.error('Error disconnecting Redis client:', redisErr);
                logMsg('An error occured. Check container logs');
            }

            console.log('LOG: Service Discovery closed');
                logMsg('LOG: Service Discovery closed');

            // Exit process after graceful shutdown
            process.exit(0);
        });
    }

    // Listen for shutdown signals (e.g., SIGINT for Ctrl+C, SIGTERM for Docker stop)
    ['SIGINT', 'SIGTERM'].forEach(signal => process.on(signal, () => shutdown(signal)));
}

startGrpcServer();