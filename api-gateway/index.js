const express = require('express');
const axios = require('axios');
const rateLimit = require('express-rate-limit');
const timeout = require('connect-timeout');

// Load environment variables
require('dotenv').config();

const app = express();
const port = process.env.PORT;
const SERVICE_A_URL = process.env.A_BASE_URL;
const SERVICE_B_URL = process.env.B_BASE_URL;

// Middleware for concurrent task limits
const limiter = rateLimit({
    windowMs: 60 * 1000, // 1 minute
    max: 100, // Limit each IP to 100 requests per windowMs
    message: 'Too many requests from this IP, please try again after a minute.'
});

// Middleware for request timeouts
const haltOnTimedout = (req, res, next) => {
    if (!req.timedout) next();
};

// Apply rate limiter globally
app.use(limiter);

// Timeout middleware (5 seconds)
app.use(timeout('5s'));

// Status endpoint
app.get('/ping', haltOnTimedout, (req, res) => {
    res.status(200).json({ message: 'API Gateway running on 8080 is alive!' });
});

// Route to Service A
app.use('/sA', async (req, res, next) => {
    try {
        const serviceUrl = `${SERVICE_A_URL}${req.url.slice(1)}`;

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
        const serviceUrl = `${SERVICE_B_URL}${req.url.slice(1)}`;

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

app.listen(port, () => {
    console.log(`API Gateway listening at http://localhost:${port}`);
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
