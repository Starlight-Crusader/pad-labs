const express = require('express');
const axios = require('axios');
const { createClient } = require('redis');
const winston = require('winston');
const fetch = require('node-fetch');

const app = express();
require('dotenv').config();

const PORT = process.env.PORT || 8080;
const SERV_REST_PORT = process.env.SERV_REST_PORT || 8000;

const SM_REDIS_URL = process.env.SM_REDIS_URL || "redis://sm_redis:6379";

const MAX_TASKS_PER_SERVICE = process.env.MAX_TASKS_PER_SERVICE || 1;
const REQUEST_TIMEOUT_MS = process.env.REQUEST_TIMEOUT_MS || 4000;
const CRTICAL_LOAD_PER_MIN = process.env.CRTICAL_LOAD_PER_MIN || 10;
const MAX_RETRIES = process.env.MAX_RETRIES || 3;
const MAX_REDIRECTS = process.env.MAX_REDIRECTS || 3;

const LOGSTASH_HOST = process.env.LOGSTASH_HOST || "logstash";
const LOGSTASH_HTTP_PORT = process.env.LOGSTASH_HTTP_PORT || 6000;

const ROOT_PASS = process.env.ROOT_PASS;

const LOGGING = parseInt(process.env.LOGGING);

// Initialize Winston logger
const logger = winston.createLogger({
    transports: [
        // new winston.transports.Console(),
        new winston.transports.Http({
            host: LOGSTASH_HOST,
            port: LOGSTASH_HTTP_PORT,
            level: 'info',
        })
    ],
});

// Quick logs
function logMsg(msg) {
    if (LOGGING) {
        logger.info(JSON.stringify({
            "service": "api_gateway",
            "msg": msg
        }));
    }
}

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
        console.log('LOG: API Gateway closed');
        logMsg('LOG: API Gateway closed');
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
        logMsg(`ALERT: Instance ${serviceType}:${ip} experiences load = ${currentLoad + 1} req/min (critical = ${CRTICAL_LOAD_PER_MIN} req/min)`);
    }
}

// Helper function to make a request to a service instance with retries
async function tryInstanceWithRetries(serviceType, ip, method, enpoint, body, headers) {
    let attempts = 0;
    let lastError;

    while (attempts < MAX_RETRIES) {
        attempts++;
        handleLoad(serviceType, ip);
        console.log(`LOG: Attempt ${attempts}/${MAX_RETRIES} for ${serviceType}:${ip} ${method} /${enpoint}`);
        logMsg(`LOG: Attempt ${attempts}/${MAX_RETRIES} for ${serviceType}:${ip} ${method} /${enpoint}`);
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
                console.log(`FAILURE TIMEOUT: ${method} | ${fullUrl} - no response in ${REQUEST_TIMEOUT_MS} ms!`);
                logMsg(`FAILURE TIMEOUT: ${method} | ${fullUrl} - no response in ${REQUEST_TIMEOUT_MS} ms!`);
            } else if (error.response?.status >= 500) {
                console.log(`FAILURE 5XX RESPONSE: ${method} | ${fullUrl}!`);
                logMsg(`FAILURE 5XX RESPONSE: ${method} | ${fullUrl}!`);
            } else if (error.response?.status >= 400) {
                // Don't retry client errors
                return { success: false, error, fatal: true };
            }
            
            if (attempts === MAX_RETRIES) {
                console.log(`INSTANCE FAILURE: Instance ${serviceType}:${ip} failed all ${MAX_RETRIES} attempts!`);
                logMsg(`INSTANCE FAILURE: Instance ${serviceType}:${ip} failed all ${MAX_RETRIES} attempts!`);
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
            load: await getParam('load', ip)
        }))
    );

    // Can comment this out to demonstrate how requests are passed from one busy instance to another
    // until they reach an available instance
    instancesWithLoad.sort((a, b) => a.load - b.load);

    // Try each instance in order of load
    for (const { ip } of instancesWithLoad.slice(0, MAX_REDIRECTS)) {
        logMsg(`${ip}`);
        logMsg(`${endpoint}`);
        
        // Check if instance can handle more tasks
        const currentTasks = await getParam('tasks', ip);
        if (currentTasks >= MAX_TASKS_PER_SERVICE) {
            console.log(`ALERT: Instance ${serviceType}:${ip} is currently busy, trying next instance`);
            logMsg(`ALERT: Instance ${serviceType}:${ip} is currently busy, trying next instance`);
            continue;
        }

        logMsg(`${ip}`); logMsg(`/${endpoint}`);

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
            logMsg(`LOG: s${serviceType}:${ip} discarded after failing all attempts`);

        } finally {
            await decParam('tasks', ip);
        }
    }

    console.log(`CLUSTER FAILURE: ${MAX_REDIRECTS} least busy ${serviceType} instances failed to handle the request!`);
    logMsg(`CLUSTER FAILURE: ${MAX_REDIRECTS} least busy ${serviceType} instances failed to handle the request!`);
    throw new Error(`${MAX_REDIRECTS} least busy ${serviceType} instances failed to handle the request.`);
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
            const detail = error.response.data?.detail 
                ? error.response.data.detail 
                : error.response.data;
            res.status(error.response.status).json({ 
                detail 
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
            const detail = error.response.data?.detail 
                ? error.response.data.detail 
                : error.response.data;
            res.status(error.response.status).json({ 
                detail 
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

app.delete('/saga/full-user-removal', async (req, res) => {
    // Extract token from Authorization header
    const authHeader = req.headers.authorization;
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
        return res.status(401).json({ error: 'No valid auth. credentials were provided.' });
    }

    try {
        // Step 1: Validate token and get user info
        const serviceAIPs = await getServiceIPs('A');
        if (serviceAIPs.length === 0) throw new Error('No service A instances available.');

        const validateResponse = await fetch(`http://${serviceAIPs[0]}:${SERV_REST_PORT}/api/utilities/validate-token`, {
            method: 'GET',
            headers: {
                'X-Root-Password': ROOT_PASS,
                'Authorization': authHeader
            }
        });

        if (!validateResponse.ok) {
            throw new Error('Token validation failed');
        }

        const userData = await validateResponse.json();
        const { id, username } = userData;

        // Step 2: Delete user's game records
        const serviceBIPs = await getServiceIPs('B');
        if (serviceBIPs.length === 0) throw new Error('No service B instances available.');

        const deleteRecordsResponse = await fetch(
            `http://${serviceBIPs[0]}:${SERV_REST_PORT}/api/records/user-delete?username=${encodeURIComponent(username)}`,
            {
                method: 'DELETE',
                headers: {
                    'X-Root-Password': ROOT_PASS
                }
            }
        );

        if (!deleteRecordsResponse.ok) {
            throw new Error('Failed to delete user records');
        }

        const deletedData = await deleteRecordsResponse.json();
        const deletedRecords = deletedData.deleted_records;

        // Step 3: Delete user account
        try {
            const deleteUserResponse = await fetch(
                `http://${serviceAIPs[0]}:${SERV_REST_PORT}/api/users/${id}/destroy`,
                {
                    method: 'DELETE',
                    headers: {
                        'X-Root-Password': ROOT_PASS
                    }
                }
            );

            if (!deleteUserResponse.ok) {
                throw new Error('Failed to delete user account');
            }

            // Success - return confirmation
            return res.status(200).json({
                message: 'All data associated with the user removed.'
            });
        } catch (userDeletionError) {
            // Rollback: Restore deleted records
            const rollbackRecords = deletedRecords.map(record => {
                const { id, ...recordWithoutId } = record;
                return recordWithoutId;
            });

            // Attempt rollback
            const rollbackResponse = await fetch(
                `http://${serviceBIPs[0]}:${SERV_REST_PORT}/api/records/save`,
                {
                    method: 'POST',
                    headers: {
                        'X-Root-Password': ROOT_PASS,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(rollbackRecords)
                }
            );

            if (!rollbackResponse.ok) {
                // Critical error: Rollback failed
                return res.status(500).json({
                    error: 'Critical error: User deletion failed and rollback failed.',
                    details: userDeletionError.message,
                    rollbackError: 'Failed to restore the data deleted in the first phase.'
                });
            }

            // Rollback succeeded but original operation failed
            return res.status(500).json({
                error: 'User deletion failed - records have been restored.',
                details: userDeletionError.message
            });
        }
    } catch (error) {
        return res.status(500).json({
            error: 'Saga transaction failed.',
            details: error.message
        });
    }
});

app.listen(PORT, () => {
    console.log(`LOG: API Gateway listening at http://127.0.0.1:${PORT}`);
    logMsg(`LOG: API Gateway listening at http://127.0.0.1:${PORT}`);
});