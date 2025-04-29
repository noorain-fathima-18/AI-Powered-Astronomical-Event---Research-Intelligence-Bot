const express = require('express');
const axios = require('axios');
const bodyParser = require('body-parser');
const path = require('path');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;
const API_URL = process.env.API_URL || 'http://localhost:8000';

// Middleware
app.use(bodyParser.urlencoded({ extended: true }));
app.use(bodyParser.json());
app.use(express.static(path.join(__dirname, 'public')));

// Set view engine
app.set('view engine', 'ejs');

// Routes
app.get('/', (req, res) => {
    res.render('index', { title: 'Astronomy Intelligence Bot' });
});

// API endpoints
app.post('/api/generate-report', async (req, res) => {
    try {
        const { topic, temperature, processType } = req.body;
        
        const response = await axios.post(`${API_URL}/generate-report`, {
            topic: topic,
            temperature: parseFloat(temperature) || 0.7,
            process_type: processType || 'hierarchical'
        });
        
        res.json(response.data);
    } catch (error) {
        console.error('Error generating report:', error);
        res.status(500).json({ 
            error: 'Failed to generate report',
            details: error.response?.data?.detail || error.message 
        });
    }
});

app.get('/api/report/:taskId', async (req, res) => {
    try {
        const { taskId } = req.params;
        const response = await axios.get(`${API_URL}/report/${taskId}`);
        res.json(response.data);
    } catch (error) {
        console.error('Error fetching report:', error);
        res.status(500).json({ 
            error: 'Failed to fetch report',
            details: error.response?.data?.detail || error.message 
        });
    }
});

// Download report as text
app.get('/api/download/text/:taskId', async (req, res) => {
    try {
        const { taskId } = req.params;
        const response = await axios.get(`${API_URL}/report/${taskId}`);
        
        if (response.data.status !== 'completed') {
            return res.status(400).json({ error: 'Report not ready yet' });
        }
        
        const filename = `astronomy_report_${response.data.topic.replace(/\s+/g, '_')}.txt`;
        
        res.setHeader('Content-disposition', `attachment; filename=${filename}`);
        res.setHeader('Content-type', 'text/plain');
        res.send(response.data.report_text);
    } catch (error) {
        console.error('Error downloading report:', error);
        res.status(500).json({ error: 'Failed to download report' });
    }
});

// Download report as PDF
app.get('/api/download/pdf/:taskId', async (req, res) => {
    try {
        const { taskId } = req.params;
        const response = await axios.get(`${API_URL}/report/${taskId}`);
        
        if (response.data.status !== 'completed' || !response.data.pdf_base64) {
            return res.status(400).json({ error: 'PDF not ready yet' });
        }
        
        const filename = `astronomy_report_${response.data.topic.replace(/\s+/g, '_')}.pdf`;
        const pdfBuffer = Buffer.from(response.data.pdf_base64, 'base64');
        
        res.setHeader('Content-disposition', `attachment; filename=${filename}`);
        res.setHeader('Content-type', 'application/pdf');
        res.send(pdfBuffer);
    } catch (error) {
        console.error('Error downloading PDF:', error);
        res.status(500).json({ error: 'Failed to download PDF' });
    }
});

// Start server
app.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
});