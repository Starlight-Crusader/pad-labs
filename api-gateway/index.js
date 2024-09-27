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

// Status endpoint
app.get('/ping', (req, res) => {
    res.status(200).json({ detail: `API Gateway running on ${PORT} is alive!` });
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
app.use('/sA', taskLimiter, async (req, res, next) => {
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
            timeout: SERVER_TIMEOUT_MS,
        });

        res.status(response.status).send(response.data);
    } catch (error) {
        if (error.code === 'ECONNABORTED') {
            res.status(504).json({ detail: "Request timed out." });
        } else {
            res.status(error.response?.status || 500).json({ detail: error.response?.data?.detail || error.message });
        }
    }
});

// Route to Service B
app.use('/sB', taskLimiter, async (req, res, next) => {
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
            timeout: SERVER_TIMEOUT_MS,
        });

        res.status(response.status).send(response.data);
    } catch (error) {
        if (error.code === 'ECONNABORTED') {
            res.status(503).json({ detail: "Service is not available. Please try again later." });
        } else {
            res.status(error.response?.status || 500).json({ detail: error.message });
        }
    }
});

app.listen(PORT, () => {
    console.log(`API Gateway listening at http://localhost:${PORT}`);
});