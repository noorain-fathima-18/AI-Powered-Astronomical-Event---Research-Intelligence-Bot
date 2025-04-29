document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const temperatureSlider = document.getElementById('temperature');
    const tempValue = document.getElementById('temp-value');
    const processTypeSelect = document.getElementById('processType');
    const topicInput = document.getElementById('topicInput');
    const generateButton = document.getElementById('generateButton');
    const progressCard = document.getElementById('progressCard');
    const progressBar = document.getElementById('progressBar');
    const statusText = document.getElementById('statusText');
    const reportCard = document.getElementById('reportCard');
    const reportContent = document.getElementById('reportContent');
    const downloadTextBtn = document.getElementById('downloadText');
    const downloadPdfBtn = document.getElementById('downloadPdf');
    
    // Current task ID
    let currentTaskId = null;
    
    // Update temperature value display
    temperatureSlider.addEventListener('input', function() {
        tempValue.textContent = this.value;
    });
    
    // Generate report
    generateButton.addEventListener('click', async function() {
        const topic = topicInput.value.trim();
        if (!topic) {
            alert('Please enter an astronomy topic');
            return;
        }
        
        // Show progress
        progressCard.style.display = 'block';
        reportCard.style.display = 'none';
        progressBar.style.width = '10%';
        statusText.textContent = 'Submitting request...';
        generateButton.disabled = true;
        
        try {
            // Submit report request
            const response = await fetch('/api/generate-report', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    topic: topic,
                    temperature: temperatureSlider.value,
                    processType: processTypeSelect.value
                })
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.details || 'Failed to start report generation');
            }
            
            currentTaskId = data.task_id;
            statusText.textContent = 'Report generation started. This may take a few minutes...';
            progressBar.style.width = '25%';
            
            // Poll for results
            pollReportStatus();
            
        } catch (error) {
            console.error('Error:', error);
            statusText.textContent = `Error: ${error.message}`;
            progressBar.className = 'progress-bar bg-danger';
            generateButton.disabled = false;
        }
    });
    
    // Poll for report status
    async function pollReportStatus() {
        if (!currentTaskId) return;
        
        try {
            const response = await fetch(`/api/report/${currentTaskId}`);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error('Failed to fetch report status');
            }
            
            if (data.status === 'processing') {
                // Still processing, update progress and continue polling
                progressBar.style.width = '50%';
                setTimeout(pollReportStatus, 5000);
            } else if (data.status === 'completed') {
                // Report is ready
                progressBar.style.width = '100%';
                statusText.textContent = 'Report generation complete!';
                progressBar.className = 'progress-bar bg-success';
                
                // Display the report
                displayReport(data);
                
                // Enable buttons
                generateButton.disabled = false;
            } else {
                // Failed
                statusText.textContent = `Error: ${data.report_text}`;
                progressBar.className = 'progress-bar bg-danger';
                generateButton.disabled = false;
            }
            
        } catch (error) {
            console.error('Error polling status:', error);
            statusText.textContent = `Error: ${error.message}`;
            progressBar.className = 'progress-bar bg-danger';
            generateButton.disabled = false;
        }
    }
    
    // Display the report
    function displayReport(reportData) {
        reportCard.style.display = 'block';
        
        // Parse markdown to HTML
        reportContent.innerHTML = marked.parse(reportData.report_text);
        
        // Set the topic in the input if it changed
        if (reportData.topic && reportData.topic !== topicInput.value) {
            topicInput.value = reportData.topic;
        }
        
        // Set up download links
        downloadTextBtn.onclick = function() {
            window.location.href = `/api/download/text/${currentTaskId}`;
        };
        
        downloadPdfBtn.onclick = function() {
            window.location.href = `/api/download/pdf/${currentTaskId}`;
        };
    }
});
