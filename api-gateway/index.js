const express = require('express');
const axios = require('axios');
const { createClient } = require('redis');
const app = express();

// Load environment variables
require('dotenv').config();

const PORT = process.env.PORT || 8080;
const SERV_REST_PORT = process.env.SERV_REST_PORT || 8000;

const SM_REDIS_URL = process.env.SM_REDIS_URL || "redis://sm_redis:6379";

const MAX_TASKS_PER_SERVICE = process.env.MAX_TASKS_PER_SERVICE || 1;
const REQUEST_TIMEOUT_MS = process.env.REQUEST_TIMEOUT_MS || 4000;
const CRTICAL_LOAD_PER_MIN = process.env.CRTICAL_LOAD_PER_MIN || 10;
const CONSEC_FAILURES_THRESHOLD = process.env.CONSEC_FAILURES_THRESHOLD || 3;

// JSON body parsing
app.use(express.json());

// Connect to Redis
const redisClient = createClient({ url: SM_REDIS_URL });
redisClient.connect().catch(console.error);

// Cleanly close Redis connection and server on shutdown - Gracefull Shutdown
async function shutdown(signal) {
    console.log(`LOG: Received ${signal}. Closing Redis and HTTP server...`);
    await redisClient.quit();
    server.close(() => {
        console.log('LOG: Express server closed');
        process.exit(0);
    });
}

['SIGINT', 'SIGTERM'].forEach(signal => process.on(signal, () => shutdown(signal)));

// Retrieve the current registered value of a numerical parameter for a specified IP address
async function getParam(param, ip) {
    const key = `${param}:${ip}`;
    const val = await redisClient.get(key);
    return parseInt(val) || 0;
}

// Increment the current registered value of a numerical parameter for a specified IP address
async function incParam(param, ip) {
    const key = `${param}:${ip}`;
    const newVal = await redisClient.incr(key);
    return newVal;
}

// Decrement the current registered value of a numerical parameter for a specified IP address
async function decParam(param, ip, minVal = 0) {
    const key = `${param}:${ip}`;
    const newValue = await redisClient.decr(key);

    if (newValue < minVal) {
        await redisClient.set(key, minVal);
    }

    return Math.max(newValue, minVal);
}

// Fetch service IPs from Redis
async function getServiceIPs(serviceType) {
    const redisKey = `service:${serviceType}`;
    const ips = await redisClient.lRange(redisKey, 0, -1);
    return ips;
}

// Helper function to remove a service IP from Redis
async function removeServiceIP(serviceType, ip) {
    const redisKey = `service:${serviceType}`;
    await redisClient.lRem(redisKey, 0, ip);
}

// Helper funciton for handling load
async function handleLoad(serviceType, ip) {
    const currentLoad = await getParam('load', ip);
    if (currentLoad > 0) {
        await incParam('load', ip);
    } else {
        await redisClient.set(`load:${ip}`, 1, 'EX', 1);
    }

    if (currentLoad + 1 >= CRTICAL_LOAD_PER_MIN) {
        console.log(`ALERT: Instance ${serviceType}:${ip} experiences load = ${currentLoad + 1} req/min (critical = ${CRTICAL_LOAD_PER_MIN} req/min)`);
    }
}

// Helper function to make a request to a service instance with retries
async function tryInstanceWithRetries(serviceType, ip, method, enpoint, body, headers) {
    let attempts = 0;
    let lastError;

    while (attempts < CONSEC_FAILURES_THRESHOLD) {
        attempts++;
        handleLoad(serviceType, ip);
        console.log(`LOG: Attempt ${attempts}/${CONSEC_FAILURES_THRESHOLD} for ${serviceType}:${ip} ${method} /${enpoint}`);
        const fullUrl = `http://${ip}:${SERV_REST_PORT}/${enpoint}`;

        try {
            const response = await axios({
                method,
                url: fullUrl,
                data: body,
                headers,
                timeout: REQUEST_TIMEOUT_MS,
            });
            return { success: true, response };
        } catch (error) {
            lastError = error;

            if (error.code === 'ECONNABORTED') {
                console.log(`FAILURE TIMEOUT: ${method} | ${fullUrl} - no response in ${REQUEST_TIMEOUT_MS} ms`);
            } else if (error.response?.status >= 500) {
                console.log(`FAILURE 5XX RESPONSE: ${method} | ${fullUrl}`);
            } else if (error.response?.status >= 400) {
                // Don't retry client errors
                return { success: false, error, fatal: true };
            }
            
            if (attempts === CONSEC_FAILURES_THRESHOLD) {
                console.log(`INSTANCE FAILURE: Instance ${serviceType}:${ip} failed all ${CONSEC_FAILURES_THRESHOLD} attempts`);
                return { success: false, error };
            }
        }
    }

    return { success: false, error: lastError };
}

// Main request handler
async function handleServiceRequest(serviceType, method, endpoint, body, headers) {
    const serviceIPs = await getServiceIPs(serviceType);
    
    if (serviceIPs.length === 0) {
        throw new Error(`No ${serviceType} instances available.`);
    }

    // Sort instances by current load
    const instancesWithLoad = await Promise.all(
        serviceIPs.map(async ip => ({
            ip,
            load: await getParam('tasks', ip)
        }))
    );
    
    // Can comment this out to demonstrate how requests are passed from one busy instance to another
    // until they reach an available instance
    instancesWithLoad.sort((a, b) => a.load - b.load);

    // Try each instance in order of load
    for (const { ip } of instancesWithLoad) {
        // Check if instance can handle more tasks
        const currentTasks = await getParam('tasks', ip);
        if (currentTasks >= MAX_TASKS_PER_SERVICE) {
            console.log(`ALERT: Instance ${serviceType}:${ip} is currently busy, trying next instance`);
            continue;
        }

        // Track the task
        await incParam('tasks', ip);
        
        try {
            // Try this instance with retries
            const result = await tryInstanceWithRetries(serviceType, ip, method, endpoint, body, headers);
            
            if (result.success) {
                return result.response;
            }
            
            // If it's a client error, don't try other instances
            if (result.fatal) {
                throw result.error;
            }
            
            // Instance failed all retries, remove it and try next one
            await removeServiceIP(serviceType, ip);
            console.log(`LOG: s${serviceType}:${ip} discarded after failing all attempts`);
            
        } finally {
            await decParam('tasks', ip);
        }
    }

    console.log(`CLUSTER FAILURE: All ${serviceType} instances failed to handle the request.`);
    throw new Error(`All ${serviceType} instances failed to handle the request.`);
}

// Status endpoint
app.get('/ping', (req, res) => {
    res.status(202).json({ message: `API Gateway running at http://127.0.0.1:${PORT} is alive!` });
});

// Route handlers
app.use('/sA/:path(*)', async (req, res) => {
    try {
        const response = await handleServiceRequest(
            'A',
            req.method,
            req.params.path + req.url.slice(1),
            req.body,
            req.headers
        );
        res.status(response.status).send(response.data);
    } catch (error) {
        if (error.response?.status) {
            res.status(error.response.status).json({ 
                detail: error.response.data?.detail || error.message 
            });
        } else {
            res.status(500).json({ 
                detail: error.message === `timeout of ${REQUEST_TIMEOUT_MS}ms exceeded` 
                    ? "Request timed out." 
                    : error.message 
            });
        }
    }
});

app.use('/sB/:path(*)', async (req, res) => {
    try {
        const response = await handleServiceRequest(
            'B',
            req.method,
            req.params.path + req.url.slice(1),
            req.body,
            req.headers
        );
        res.status(response.status).send(response.data);
    } catch (error) {
        if (error.response?.status) {
            res.status(error.response.status).json({ 
                detail: error.response.data?.detail || error.message 
            });
        } else {
            res.status(500).json({ 
                detail: error.message === `timeout of ${REQUEST_TIMEOUT_MS}ms exceeded` 
                    ? "Request timed out." 
                    : error.message 
            });
        }
    }
});

app.listen(PORT, () => {
    console.log(`LOG: API Gateway listening at http://127.0.0.1:${PORT}`);
});