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

// Middleware to limit tasks per IP
const taskLimiter = async (req, res, next) => {
    try {
        const currentTasks = await getParam('tasks',  req.serviceIP);

        if (currentTasks && parseInt(currentTasks) >= MAX_TASKS_PER_SERVICE) {
            throw new Error(`Reached task limit for ${req.serviceIP}`);
        }

        await incParam('tasks', req.serviceIP);

        next();
    } catch (error) {
        if (error.message === `Reached task limit for ${req.serviceIP}`)
        {
            console.log("ALERT:", error.message);
            res.status(503).json({ detail: error.message });
        } else {
            console.error(`Failed task limiting for ${serviceType}:`, error);
            res.status(500).json({ detail: "Gateway error." });
        }
    }
}

// Helper function to find the IP with the lowest load
async function getLowestLoadIP(serviceType) {
    const serviceIPs = await getServiceIPs(serviceType);

    if (serviceIPs.length == 0)
    {
        throw new Error(`No ${serviceType} instances available`)
    }

    let lowestLoadIP = serviceIPs[0];
    let lowestLoad = await getParam('tasks', lowestLoadIP);

    for (const ip of serviceIPs) {
        const load = await getParam('tasks', ip);
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
        // Get the IP with the lowest load
        const ip = await getLowestLoadIP(serviceType);
        const currentLoad = await incParam('load', ip);

        // Check if the load exceeds the maximum limit
        if (currentLoad >= CRTICAL_LOAD_PER_MIN) {
            console.log(`ALERT: Load at ${ip} = ${currentLoad} req/min - has exceeded critical = ${CRTICAL_LOAD_PER_MIN} req/min`)
        }

        // Attach selected IP to the request for use in the route handler
        req.serviceIP = ip;

        next();
    } catch (error) {
        if (error.message === `No ${serviceType} instances available`)
        {
            res.status(503).json({detail: error.message + "."});
        } else {
            console.error(`Failed load balancing for ${serviceType}:`, error);
            res.status(500).json({ detail: "Gateway error." });
        }
    }
};

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

// Status endpoint
app.get('/ping', (req, res) => {
    res.status(202).json({ message: `API Gateway running at http://127.0.0.1:${PORT} is alive!` });
});

// Route to Service A
app.use('/sA', loadBalancerForService('A'), taskLimiter, async (req, res, next) => {
    const url = `http://${req.serviceIP}:${SERV_REST_PORT}/${req.url.slice(1)}`;
    console.log(`${req.method} | /sA/${req.url.slice(1)} -> ${req.serviceIP}`);
    const reqData = {
        method: req.method,
        url: url,
        data: req.body,
        headers: req.headers,
        timeout: REQUEST_TIMEOUT_MS,
    };

    let attempt = 0;
    let lastError;

    // Circuit breaker (3 retries)
    try {
        while (attempt < CONSEC_FAILURES_THRESHOLD) {
            try {
                const response = await axios(reqData);
                return res.status(response.status).send(response.data); // Exit on success
            } catch (error) {
                lastError = error;

                if (error.code === 'ECONNABORTED') {
                    console.log(`TIMEOUT: ${req.method} | ${url} - no response in ${REQUEST_TIMEOUT_MS} ms`);
                } else if (error.response && error.response.status >= 500 && error.response.status < 600) {
                    console.log(`5XX RESPONSE: ${req.method} | ${url}`);
                } else if (error.response && error.response.status >= 400 && error.response.status < 500) {
                    // For 4XX errors, log and break the loop immediately
                    console.log(`4XX RESPONSE: ${req.method} | ${url}`);
                    break; // Exit the loop without retrying
                }
                attempt++;
            }
        }

        // After exhausting retries, handle the last error if it exists
        if (lastError) {
            if (attempt == CONSEC_FAILURES_THRESHOLD) {
                console.log(`LOG: ${req.method} | ${url} - failed after ${CONSEC_FAILURES_THRESHOLD} attempts`);
                await removeServiceIP('A', req.serviceIP);
                console.log(`LOG: sA:${req.serviceIP} discarded`);
            }

            if (lastError.message === `timeout of ${REQUEST_TIMEOUT_MS}ms exceeded`) {
                lastError.message = "Request timed out.";
            }

            return res.status(lastError.response?.status || 500).json({ detail: lastError.response?.data?.detail || lastError.message });
        }
    } finally {
        // Always decrement the task counter, whether success or failure
        await decParam('tasks', req.serviceIP);
    }
});

// Route to Service B
app.use('/sB', loadBalancerForService('B'), taskLimiter, async (req, res, next) => {
    const url = `http://${req.serviceIP}:${SERV_REST_PORT}/${req.url.slice(1)}`;
    console.log(`${req.method} | /sB/${req.url.slice(1)} -> ${req.serviceIP}`);
    const reqData = {
        method: req.method,
        url: url,
        data: req.body,
        headers: req.headers,
        timeout: REQUEST_TIMEOUT_MS,
    };

    let attempt = 0;
    let lastError;

    // Circuit breaker (3 retries)
    try {
        while (attempt < CONSEC_FAILURES_THRESHOLD) {
            try {
                const response = await axios(reqData);
                return res.status(response.status).send(response.data); // Exit on success
            } catch (error) {
                lastError = error;

                if (error.code === 'ECONNABORTED') {
                    console.log(`TIMEOUT: ${req.method} | ${url} - no response in ${REQUEST_TIMEOUT_MS} ms`);
                } else if (error.response && error.response.status >= 500 && error.response.status < 600) {
                    console.log(`5XX RESPONSE: ${req.method} | ${url}`);
                } else if (error.response && error.response.status >= 400 && error.response.status < 500) {
                    // For 4XX errors, log and break the loop immediately
                    console.log(`4XX RESPONSE: ${req.method} | ${url}`);
                    break; // Exit the loop without retrying
                }
                attempt++;
            }
        }

        // After exhausting retries, handle the last error if it exists
        if (lastError) {
            if (attempt == CONSEC_FAILURES_THRESHOLD) {
                console.log(`LOG: ${req.method} | ${url} - failed after ${CONSEC_FAILURES_THRESHOLD} attempts`);
                await removeServiceIP('B', req.serviceIP);
                console.log(`LOG: sB:${req.serviceIP} discarded`);
            }

            if (lastError.message === `timeout of ${REQUEST_TIMEOUT_MS}ms exceeded`) {
                lastError.message = "Request timed out.";
            }

            return res.status(lastError.response?.status || 500).json({ detail: lastError.response?.data?.detail || lastError.message });
        }
    } finally {
        // Always decrement the task counter, whether success or failure
        await decParam('tasks', req.serviceIP);
    }
});

app.listen(PORT, () => {
    console.log(`API Gateway listening at http://127.0.0.1:${PORT}`);
});