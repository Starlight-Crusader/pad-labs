const express = require('express');
const axios = require('axios');
const redis = require('redis');
const app = express();

// Load environment variables
require('dotenv').config();

const PORT = process.env.PORT;
const SM_REDIS_URL = process.env.SM_REDIS_URL;
const SERV_REST_PORT = process.env.SERV_REST_PORT;
const SERVER_TIMEOUT_MS = process.env.SERVER_TIMEOUT_MS;
const MAX_CONCURRENT_REQUESTS = process.env.MAX_CONCURRENT_REQUESTS;

// Circuit breaker configuration
const FAILURES_THRESHOLD = 3;                          // Number of errors before tripping the circuit
const FAILURES_TIMEOUT_MS = SERVER_TIMEOUT_MS * 5;     // Time window to track errors
const CIRCUIT_RESET_TIMEOUT_MS = 60000;             // 1 minute to reset the circuit breaker after being tripped

let concurrentRequests = 0;

// Connect to Redis
const redisClient = redis.createClient({ url: SM_REDIS_URL });
redisClient.connect();

// Cleanly close Redis connection and server on shutdown - Gracefull Shutdown
async function shutdown(signal) {
    console.log(`Received ${signal}. Closing Redis and HTTP server...`);
    await redisClient.quit();
    server.close(() => {
        console.log('Express server closed.');
        process.exit(0);
    });
}

['SIGINT', 'SIGTERM'].forEach(signal => process.on(signal, () => shutdown(signal)));

// Helper function to get failures count for a specific IP
async function getFailuresCount(ip) {
    const failuresKey = `failures:${ip}`;
    const count = await redisClient.get(failuresKey);
    return parseInt(count) || 0;
}

// Helper function to increment failures count for a specific IP
async function incrementFailuresCount(ip) {
    const failuresKey = `failures:${ip}`;
    const failuresCount = await getFailuresCount(ip);
    const newFailuresCount = failuresCount + 1;
    await redisClient.set(failuresKey, newFailuresCount, { EX: FAILURES_TIMEOUT_MS / 1000 }); // Set expiry on failuress
    return newFailuresCount;
}

// Helper function to reset failures count for a specific IP
async function resetFailuresCount(serviceType, ip) {
    const failuresKey = `failures:${serviceType}:${ip}`;
    await redisClient.del(failuresKey);
}

// Helper function to trip the circuit breaker for a specific IP
async function tripCircuit(serviceType, ip) {
    const circuitKey = `circuit:${serviceType}:${ip}`;
    await redisClient.set(circuitKey, 'open', { EX: CIRCUIT_RESET_TIMEOUT_MS / 1000 });
}

// Helper function to check if circuit breaker is open for a specific IP
async function isCircuitOpen(serviceType, ip) {
    const circuitKey = `circuit:${serviceType}:${ip}`;
    const status = await redisClient.get(circuitKey);
    return status === 'open';
}

// Function to handle errors and trip the circuit breaker
const handleServiceFailure = async (serviceType, ip) => {
    const failuresCount = await incrementFailuresCount(serviceType, ip);
    if (failuresCount >= FAILURES_THRESHOLD) {
        console.log(`Circuit breaker tripped for ${serviceType} instance at ${ip}`);
        await tripCircuit(serviceType, ip);
    }
};

// Circuit Breaker Middleware for Service A
const circuitBreakerForServiceA = async (req, res, next) => {
    const serviceIPs = await getServiceIPs('A');
    const ip = serviceIPs[serviceAIndex]; // Current IP in round-robin
    if (await isCircuitOpen('A', ip)) {
        return res.status(503).json({ detail: `Service A instance at ${ip} is temporarily unavailable.` });
    }
    next();
};

// Circuit Breaker Middleware for Service B
const circuitBreakerForServiceB = async (req, res, next) => {
    const serviceIPs = await getServiceIPs('B');
    const ip = serviceIPs[serviceBIndex]; // Current IP in round-robin
    if (await isCircuitOpen('B', ip)) {
        return res.status(503).json({ detail: `Service B instance at ${ip} is temporarily unavailable.` });
    }
    next();
};

app.use(express.json());

// Status endpoint
app.get('/ping', (req, res) => {
    res.status(200).json({ message: `API Gateway running at http://127.0.0.1:${PORT} is alive!` });
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

// Middleware for limiting concurrent tasks
const taskLimiter = (req, res, next) => {
    if (concurrentRequests >= MAX_CONCURRENT_REQUESTS) {
        return res.status(503).json({ detail: "API Gateway is busy. Please try again later." });
    }
    concurrentRequests++;
    res.on('finish', () => {  // Decrease the counter when the request is finished
        concurrentRequests--;
    });
    next();
};

// Route to Service A
app.use('/sA', taskLimiter, circuitBreakerForServiceA, async (req, res, next) => {
    try {
        const serviceIPs = await getServiceIPs('A');
        if (serviceIPs.length === 0) {
            return res.status(503).json({ detail: 'Service A is not available.' });
        }

        const serviceUrl = `http://${serviceIPs[serviceAIndex]}:${SERV_REST_PORT}/${req.url.slice(1)}`;

        const response = await axios({
            method: req.method,
            url: serviceUrl,
            data: req.body,
            headers: req.headers,
            timeout: SERVER_TIMEOUT_MS,
        });

        res.status(response.status).send(response.data);

        serviceAIndex = (serviceAIndex + 1) % serviceIPs.length;
    } catch (error) {
        const serviceIPs = await getServiceIPs('A');
        const ip = serviceIPs[serviceAIndex];           // Still current IP in round-robin

        serviceAIndex = (serviceAIndex + 1) % serviceIPs.length;

        if (error.code === 'ECONNABORTED') {
            res.status(504).json({ detail: "Request timed out." });
        } else {
            res.status(error.response?.status || 500).json({ detail: error.response?.data?.detail || error.message });
        }

        // Handle service failure and possibly trip circuit breaker for the IP
        await handleServiceFailure('A', ip);
    }
});

// Route to Service B
app.use('/sB', taskLimiter, circuitBreakerForServiceB, async (req, res, next) => {
    try {
        const serviceIPs = await getServiceIPs('B');
        if (serviceIPs.length === 0) {
            return res.status(503).json({ detail: 'Service B is not available.' });
        }

        const serviceUrl = `http://${serviceIPs[serviceBIndex]}:${SERV_REST_PORT}/${req.url.slice(1)}`;

        const response = await axios({
            method: req.method,
            url: serviceUrl,
            data: req.body,
            headers: req.headers,
            timeout: SERVER_TIMEOUT_MS,
        });

        res.status(response.status).send(response.data);

        serviceBIndex = (serviceBIndex + 1) % serviceIPs.length;
    } catch (error) {
        const serviceIPs = await getServiceIPs('B');
        const ip = serviceIPs[serviceBIndex];           // Still current IP in round-robin

        serviceBIndex = (serviceBIndex + 1) % serviceIPs.length;

        if (error.code === 'ECONNABORTED') {
            res.status(504).json({ detail: "Request timed out." });
        } else {
            res.status(error.response?.status || 500).json({ detail: error.response?.data?.detail || error.message });
        }

        await handleServiceFailure('B', ip);
    }
});

app.listen(PORT, () => {
    console.log(`API Gateway listening at http://127.0.0.1:${PORT}`);
});