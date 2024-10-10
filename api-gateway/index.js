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
const CRTICAL_LOAD_FOR_SERVICE = process.env.CRTICAL_LOAD_FOR_SERVICE;

// Circuit breaker configuration
const FAILURES_THRESHOLD = 3;                          // Number of errors before tripping the circuit
const FAILURES_TIMEOUT_MS = SERVER_TIMEOUT_MS * 5;     // Time window to track errors

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
    return newFailuresCount
}

// Helper function to remove a service IP from Redis
async function removeServiceIP(serviceType, ip) {
    const redisKey = `service:${serviceType}`;
    await redisClient.lRem(redisKey, 0, ip);  // Remove the IP from the list
    console.log(`${ip} removed from discovered ${serviceType}-s`);
}

// Function to handle errors and trip the circuit breaker
const handleServiceFailure = async (serviceType, ip) => {
    const failuresCount = await incrementFailuresCount(ip);
    if (failuresCount >= FAILURES_THRESHOLD) {
        console.log(`Circuit breaker tripped for ${serviceType} instance at ${ip}`);
        await removeServiceIP(serviceType, ip);
    }
};

app.use(express.json());

// Status endpoint
app.get('/ping', (req, res) => {
    res.status(200).json({ message: `API Gateway running at http://127.0.0.1:${PORT} is alive!` });
});

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

// Helper function to get the current load on a specific IP
async function getLoad(ip) {
    const loadKey = `load:${ip}`;
    const load = await redisClient.get(loadKey);
    return parseInt(load) || 0;
}

// Helper function to increment the load for a specific IP
async function incrementLoad(ip) {
    const loadKey = `load:${ip}`;
    const currentLoad = await getLoad(ip);
    await redisClient.set(loadKey, currentLoad + 1);
    return currentLoad + 1;
}

// Helper function to decrement the load for a specific IP
async function decrementLoad(ip) {
    const loadKey = `load:${ip}`;
    const currentLoad = await getLoad(ip);
    await redisClient.set(loadKey, Math.max(0, currentLoad - 1));
}

// Helper function to find the IP with the lowest load
async function getLowestLoadIP(serviceType) {
    const serviceIPs = await getServiceIPs(serviceType);
    let lowestLoadIP = serviceIPs[0];
    let lowestLoad = await getLoad(lowestLoadIP);

    for (const ip of serviceIPs) {
        const load = await getLoad(ip);
        if (load < lowestLoad) {
            lowestLoad = load;
            lowestLoadIP = ip;
        }
    }

    return lowestLoadIP;
}

// Middleware for load-based routing and load limit checking
const loadBalancerForService = (serviceType) => async (req, res, next) => {
    try {
        const serviceIPs = await getServiceIPs(serviceType);
        if (serviceIPs.length === 0) {
            return res.status(503).json({ detail: `${serviceType} is not available.` });
        }

        // Get the IP with the lowest load
        const ip = await getLowestLoadIP(serviceType);
        const currentLoad = await incrementLoad(ip);

        // Check if the load exceeds the maximum limit
        if (currentLoad >= CRTICAL_LOAD_FOR_SERVICE) {
            console.log(`Current load for ${serviceType} instance at ${ip} = ${currentLoad} req-s - has exceeded critical number = ${CRTICAL_LOAD_FOR_SERVICE} req-s`)
        }

        req.serviceIP = ip;                         // Attach selected IP to the request for use in the route handler
        res.on('finish', () => decrementLoad(ip));  // Decrement load after response is finished

        next();
    } catch (error) {
        console.error(`Error in load balancing for ${serviceType}:`, error);
        res.status(500).json({ detail: "Internal server error" });
    }
};

// Route to Service A (Round-robin LB code - commented)
app.use('/sA', taskLimiter, loadBalancerForService('A'), async (req, res, next) => {
    const serviceUrl = `http://${req.serviceIP}:${SERV_REST_PORT}/${req.url.slice(1)}`;
    try {
        console.log(`${req.method} -> A - ${serviceUrl}`);
        
        const response = await axios({
            method: req.method,
            url: serviceUrl,
            data: req.body,
            headers: req.headers,
            timeout: SERVER_TIMEOUT_MS,
        });

        res.status(response.status).send(response.data);
    } catch (error) {
        if (error.code === 'ECONNABORTED') {
            res.status(504).json({ detail: "Request timed out." });
        } else {
            res.status(error.response?.status || 500).json({ detail: error.response?.data?.detail || error.message });
        }

        await handleServiceFailure('A', req.serviceIP)
    }
});

// Route to Service B (Round-robin LB code - commented)
app.use('/sB', taskLimiter, loadBalancerForService('B'), async (req, res, next) => {
    const serviceUrl = `http://${req.serviceIP}:${SERV_REST_PORT}/${req.url.slice(1)}`;
    try {
        const response = await axios({
            method: req.method,
            url: serviceUrl,
            data: req.body,
            headers: req.headers,
            timeout: SERVER_TIMEOUT_MS,
        });

        res.status(response.status).send(response.data);
    } catch (error) {
        if (error.code === 'ECONNABORTED') {
            res.status(504).json({ detail: "Request timed out." });
        } else {
            res.status(error.response?.status || 500).json({ detail: error.response?.data?.detail || error.message });
        }

        await handleServiceFailure('B', req.serviceIP);
    }
});

app.listen(PORT, () => {
    console.log(`API Gateway listening at http://127.0.0.1:${PORT}`);
});