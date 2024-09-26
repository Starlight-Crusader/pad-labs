const express = require('express');
const axios = require('axios');
const timeout = require('connect-timeout');
const grpc = require('@grpc/grpc-js');
const protoLoader = require('@grpc/proto-loader');
const redis = require('redis');

// Load environment variables
require('dotenv').config();

const app = express();
const grpcPort = process.env.GRPC_PORT || 50051;
const restPort = process.env.REST_PORT || 8080;
const SM_REDIS_URL = process.env.SM_REDIS_URL;
const SERV_REST_PORT = process.env.SERV_REST_PORT;

// Connect to Redis
const redisClient = redis.createClient({ url: SM_REDIS_URL });
redisClient.connect();

// Middleware for concurrent task limits
let activeRequests = 0;
const MAX_CONCURRENT_REQUESTS = 20;

const concurrentLimitMiddleware = (req, res, next) => {
    if (activeRequests >= MAX_CONCURRENT_REQUESTS) {
        res.status(503).json({ detail: 'Server is busy, please try again later.' });
    } else {
        activeRequests++;
        res.on('finish', () => activeRequests--); // Decrement count when request finishes
        next();
    }
};

app.use(concurrentLimitMiddleware);

// Middleware for request timeouts
const haltOnTimedout = (req, res, next) => {
    if (!req.timedout) next();
};

// Timeout middleware (5 seconds)
app.use(timeout('5s'));

// Parse incoming JSON payloads
app.use(express.json());

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
            console.log(`Registered service:${serviceType} at IP: ${ip}`);
            callback(null, { success: true, detail: `Service registered successfully.` });
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
    server.bindAsync(`0.0.0.0:${grpcPort}`, grpc.ServerCredentials.createInsecure(), () => {
        console.log(`gRPC service discovery running at http://0.0.0.0:${grpcPort}`);
        server.start();
    });
}

// Start gRPC server
startGrpcServer();

// Status endpoint
app.get('/ping', haltOnTimedout, (req, res) => {
    res.status(200).json({ detail: 'API Gateway running on 8080 is alive!' });
});

// Round-robin stuff
let serviceAIndex = 0;
let serviceBIndex = 0;

// Fetch service IPs from Redis
async function getServiceIPs(serviceType) {
    const redisKey = `service:${serviceType}`;
    const ips = await redisClient.lRange(redisKey, 0, -1); // Get all IPs
    return ips;
}

// Route to Service A
app.use('/sA', async (req, res, next) => {
    try {
        const serviceIPs = await getServiceIPs('A');
        if (serviceIPs.length === 0) {
            return res.status(503).json({ detail: 'Service A is not available.' });
        }

        // Round-robin logic
        const serviceUrl = `http://${serviceIPs[serviceAIndex]}:${SERV_REST_PORT}/${req.url.slice(1)}`;
        serviceAIndex = (serviceAIndex + 1) % serviceIPs.length;

        const response = await axios({
            method: req.method,
            url: serviceUrl,
            data: req.body,
            headers: req.headers,
        });

        res.status(response.status).send(response.data);
    } catch (error) {
        next(error); // Pass the error to the global error handler
    }
}, haltOnTimedout);

// Route to Service B
app.use('/sB', async (req, res, next) => {
    try {
        const serviceIPs = await getServiceIPs('B');
        if (serviceIPs.length === 0) {
            return res.status(503).json({ detail: 'Service B is not available.' });
        }

        // Round-robin logic
        const serviceUrl = `http://${serviceIPs[serviceBIndex]}:${SERV_REST_PORT}/${req.url.slice(1)}`;
        serviceBIndex = (serviceBIndex + 1) % serviceIPs.length;

        const response = await axios({
            method: req.method,
            url: serviceUrl,
            data: req.body,
            headers: req.headers,
        });

        res.status(response.status).send(response.data);
    } catch (error) {
        next(error); // Pass the error to the global error handler
    }
}, haltOnTimedout);

// Global error handler for unhandled errors
app.use((err, req, res, next) => {
    if (req.timedout) {
        res.status(504).json({ detail: 'Request timed out.' });
    } else if (err.response) {
        // Return the status and the message provided by the service
        res.status(err.response.status).send(err.response.data);
    } else {
        res.status(err.status || 500).json({ detail: err.message });
    }
});

app.listen(restPort, () => {
    console.log(`API Gateway listening at http://localhost:${restPort}`);
});

// Graceful shutdown
const shutdown = () => {
    console.log('Received kill signal, shutting down gracefully.');
    server.close(() => {
        console.log('Closed out remaining connections.');
        process.exit(0);
    });
  
    // Force shutdown after 10 seconds if still running
    setTimeout(() => {
        console.error('Forcing shutdown due to pending connections.');
        process.exit(1);
    }, 10000);
};

// Listen for termination signals
process.on('SIGTERM', shutdown);
process.on('SIGINT', shutdown);