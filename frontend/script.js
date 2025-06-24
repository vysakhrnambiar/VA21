// frontend/script.js
document.addEventListener('DOMContentLoaded', () => {
    const wsStatusDotElement = document.getElementById('ws-status');
    const displayArea = document.getElementById('display-area');
    let websocket = null;
    let chartInstance = null;
    let contentTimeoutId = null;
    let logoIdleAnimationId = null;

    let connectionStatusBanner = null;
    let callUpdateNotificationArea = null;
    let hideBannerTimeout = null;

    // New state variable to track backend agent's connection status
    let agentBackendConnected = false;

    // Thinking popup state
    let thinkingPopup = null;
    let thinkingContent = null;
    let thinkingBuffer = '';
    let thinkingBufferTimeout = null;

    const IDLE_STATE_TIMEOUT_MS = 5 * 60 * 1000;
    const RECONNECT_DELAY_MS = 5000;

    function createNotificationElements() {
        if (!document.getElementById('connection-status-banner')) {
            connectionStatusBanner = document.createElement('div');
            connectionStatusBanner.id = 'connection-status-banner';
            connectionStatusBanner.className = 'notification-banner';
            document.body.appendChild(connectionStatusBanner);
        } else {
            connectionStatusBanner = document.getElementById('connection-status-banner');
        }

        if (!document.getElementById('call-update-notification-area')) {
            callUpdateNotificationArea = document.createElement('div');
            callUpdateNotificationArea.id = 'call-update-notification-area';
            callUpdateNotificationArea.className = 'notification-banner'; 
            document.body.appendChild(callUpdateNotificationArea);
        } else {
            callUpdateNotificationArea = document.getElementById('call-update-notification-area');
        }
    }
    
    function updateWsStatusIndicator(cssClass) { 
        if (wsStatusDotElement) {
            wsStatusDotElement.className = 'status-indicator-dot'; 
            wsStatusDotElement.classList.add(cssClass);
        }
    }

    function showConnectionStatusBanner(message, type) { 
        if (!connectionStatusBanner) createNotificationElements();
        if (hideBannerTimeout) { clearTimeout(hideBannerTimeout); hideBannerTimeout = null; }
        
        connectionStatusBanner.textContent = message;
        connectionStatusBanner.className = 'notification-banner visible';        
        let bannerClass = '';
        if (type === 'connected') bannerClass = 'status-connected-banner';
        else if (type === 'disconnected') bannerClass = 'status-disconnected-banner';
        else if (type === 'error') bannerClass = 'status-error-banner';
        else if (type === 'info') bannerClass = 'status-info-banner';
        if (bannerClass) connectionStatusBanner.classList.add(bannerClass);

        if (type === 'connected' || type === 'info') {
            hideBannerTimeout = setTimeout(() => {
                if (connectionStatusBanner.classList.contains(bannerClass)) {
                    connectionStatusBanner.classList.remove('visible');
                }
                hideBannerTimeout = null;
            }, 4000);
        }
    }

    function showCallUpdateNotification(contactName, summary, job_id) {
        if (!callUpdateNotificationArea) createNotificationElements();
        callUpdateNotificationArea.innerHTML = `🔔 <strong>Call Update (Job ${job_id}): ${contactName}</strong><br>${summary}`;
        callUpdateNotificationArea.className = 'notification-banner visible call-update-styling'; 
        
        // Clear any existing timeout for this specific notification
        if (callUpdateNotificationArea.hideTimeout) {
            clearTimeout(callUpdateNotificationArea.hideTimeout);
        }
        callUpdateNotificationArea.hideTimeout = setTimeout(() => {
            hideCallUpdateNotification();
        }, 20000); 
    }

    function hideCallUpdateNotification() {
        if (callUpdateNotificationArea) { 
            callUpdateNotificationArea.classList.remove('visible');
            if (callUpdateNotificationArea.hideTimeout) {
                clearTimeout(callUpdateNotificationArea.hideTimeout);
                callUpdateNotificationArea.hideTimeout = null;
            }
        }
    }

    // Thinking popup functions
    function createThinkingPopup() {
        if (thinkingPopup) return; // Already exists
        
        // Create overlay
        thinkingPopup = document.createElement('div');
        thinkingPopup.id = 'thinking-popup-overlay';
        thinkingPopup.className = 'thinking-popup-overlay';
        
        // Create popup container
        const popupContainer = document.createElement('div');
        popupContainer.className = 'thinking-popup-container';
        
        // Create header
        const header = document.createElement('div');
        header.className = 'thinking-popup-header';
        header.innerHTML = '⚡ <span>I am working on the task...</span>';
        
        // Create content area
        thinkingContent = document.createElement('div');
        thinkingContent.className = 'thinking-popup-content';
        thinkingContent.innerHTML = '<div class="thinking-dots">•••</div>';
        
        // Create footer
        const footer = document.createElement('div');
        footer.className = 'thinking-popup-footer';
        footer.textContent = 'Please wait while I process your request';
        
        // Assemble popup
        popupContainer.appendChild(header);
        popupContainer.appendChild(thinkingContent);
        popupContainer.appendChild(footer);
        thinkingPopup.appendChild(popupContainer);
        
        document.body.appendChild(thinkingPopup);
    }

    function showThinkingPopup() {
        createThinkingPopup();
        console.log("Showing thinking popup");
        thinkingBuffer = '';
        thinkingPopup.classList.add('visible');
        
        // Start pulsing animation for dots
        const dots = thinkingContent.querySelector('.thinking-dots');
        if (dots) {
            dots.classList.add('pulsing');
        }
    }

    function updateThinkingContent(content) {
        if (!thinkingPopup || !thinkingContent) return;
        
        // Buffer content to avoid too frequent updates
        thinkingBuffer += content;
        
        // Clear existing timeout
        if (thinkingBufferTimeout) {
            clearTimeout(thinkingBufferTimeout);
        }
        
        // Update content after a small delay (batching)
        thinkingBufferTimeout = setTimeout(() => {
            // Replace dots with actual thinking content
            const dotsElement = thinkingContent.querySelector('.thinking-dots');
            if (dotsElement) {
                dotsElement.remove();
            }
            
            // Create or update thinking text element
            let thinkingText = thinkingContent.querySelector('.thinking-text');
            if (!thinkingText) {
                thinkingText = document.createElement('div');
                thinkingText.className = 'thinking-text';
                thinkingContent.appendChild(thinkingText);
            }
            
            // Process the thinking content for better display
            const processedContent = thinkingBuffer
                .replace(/\n/g, '<br>')
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\*(.*?)\*/g, '<em>$1</em>');
            
            thinkingText.innerHTML = processedContent;
            
            // Auto-scroll to bottom
            thinkingContent.scrollTop = thinkingContent.scrollHeight;
            
            console.log("Updated thinking content:", content.length, "chars");
        }, 100); // 100ms batching delay
    }

    function hideThinkingPopup() {
        if (!thinkingPopup) return;
        
        console.log("Hiding thinking popup");
        
        // Clear any pending buffer updates
        if (thinkingBufferTimeout) {
            clearTimeout(thinkingBufferTimeout);
            thinkingBufferTimeout = null;
        }
        
        // Add fade-out animation
        thinkingPopup.classList.add('fade-out');
        
        // Remove after animation completes
        setTimeout(() => {
            if (thinkingPopup && thinkingPopup.parentNode) {
                thinkingPopup.parentNode.removeChild(thinkingPopup);
            }
            thinkingPopup = null;
            thinkingContent = null;
            thinkingBuffer = '';
        }, 300); // Match CSS animation duration
    }

    function clearAllDynamicContent(withAnimation = false) {
        if (chartInstance) { chartInstance.destroy(); chartInstance = null; }
        if (logoIdleAnimationId) { cancelAnimationFrame(logoIdleAnimationId); logoIdleAnimationId = null; }
        
        if (withAnimation && displayArea.children.length > 0) {
            Array.from(displayArea.children).forEach(child => child.classList.add('animate-fade-out'));
            setTimeout(() => { displayArea.innerHTML = ''; }, 700);
        } else { displayArea.innerHTML = ''; }
        hideCallUpdateNotification(); 
    }
    
    function resetContentTimeout() {
        if (contentTimeoutId) clearTimeout(contentTimeoutId);
        if (displayArea.querySelector('#active-content-wrapper')) {
             contentTimeoutId = setTimeout(showIdleState, IDLE_STATE_TIMEOUT_MS);
        }
    }
    
    function updateIdleScreenMessage() {
        const subtitleElement = document.getElementById('status-message');
        // Only update if the idle screen structure is present
        if (displayArea.querySelector('#idle-state-content') && subtitleElement) {
            if (!websocket || websocket.readyState === WebSocket.CLOSED) {
                subtitleElement.textContent = 'Display service disconnected. Attempting to reconnect...';
                subtitleElement.classList.add('disconnected-message');
            } else if (websocket.readyState === WebSocket.CONNECTING) {
                subtitleElement.textContent = 'Connecting to display service...';
                subtitleElement.classList.remove('disconnected-message');
            } else if (websocket.readyState === WebSocket.OPEN) {
                if (agentBackendConnected) {
                    subtitleElement.textContent = 'Agent ready. Waiting for your command.';
                    subtitleElement.classList.remove('disconnected-message');
                } else {
                    subtitleElement.textContent = 'Display service connected. Waiting for agent status...';
                    subtitleElement.classList.remove('disconnected-message'); 
                }
            }
            console.log("updateIdleScreenMessage: WS State:", websocket ? websocket.readyState : "null", "Agent Backend Connected:", agentBackendConnected, "Text:", subtitleElement.textContent);
        }
    }

    function showIdleState() {
        console.log("Showing idle state.");
        clearAllDynamicContent(true);
        setTimeout(() => {
            const idleContent = document.createElement('div');
            idleContent.id = 'idle-state-content';
            idleContent.classList.add('animate-fade-in');

            const logoImg = document.createElement('img');
            logoImg.id = 'animated-logo-idle';
            logoImg.src = '/static/logo.png';
            idleContent.appendChild(logoImg);

            const titleElement = document.createElement('h2');
            titleElement.textContent = 'Ready to assist';
            idleContent.appendChild(titleElement);

            const subtitleElement = document.createElement('p');
            subtitleElement.id = 'status-message';
            idleContent.appendChild(subtitleElement);
            
            displayArea.appendChild(idleContent);
            updateIdleScreenMessage();

            let scale = 1; let scaleDirection = 0.0005; 
            let translateY = 0; let floatDirection = 0.1; 
            const maxTranslateY = 5;
            function animateLogoIdle() {
                scale += scaleDirection; if (scale > 1.02 || scale < 0.98) { scaleDirection *= -1; scale = Math.max(0.98, Math.min(1.02, scale));}
                translateY += floatDirection; if (translateY > maxTranslateY || translateY < -maxTranslateY) {floatDirection *= -1; translateY = Math.max(-maxTranslateY, Math.min(maxTranslateY, translateY));}
                const currentLogo = document.getElementById('animated-logo-idle');
                if (currentLogo) { currentLogo.style.transform = `translateY(${translateY}px) scale(${scale})`; logoIdleAnimationId = requestAnimationFrame(animateLogoIdle); }
                else { if (logoIdleAnimationId) cancelAnimationFrame(logoIdleAnimationId); logoIdleAnimationId = null; }
            }
            if (logoIdleAnimationId) cancelAnimationFrame(logoIdleAnimationId); 
            animateLogoIdle();
            
            if (contentTimeoutId) clearTimeout(contentTimeoutId);
        }, 700); 
    }
    
    function displayActiveContent(elementProvider) {
        clearAllDynamicContent(true); 
        setTimeout(() => {
            const activeContentWrapper = document.createElement('div'); activeContentWrapper.id = 'active-content-wrapper'; activeContentWrapper.classList.add('animate-fade-in');
            const contentElement = elementProvider(); activeContentWrapper.appendChild(contentElement);
            displayArea.appendChild(activeContentWrapper);
            resetContentTimeout();
        }, 700);
    }

    function renderMarkdown(payload) { 
        displayActiveContent(() => {
            const markdownContainer = document.createElement('div'); markdownContainer.classList.add('markdown-content');
            let htmlOutput = ""; let mainTitleTextFromPayload = "";
            if (payload.title && payload.title.trim() !== "") { mainTitleTextFromPayload = payload.title.trim(); htmlOutput += marked.parse(mainTitleTextFromPayload.startsWith("#") ? mainTitleTextFromPayload : `<h2>${mainTitleTextFromPayload}</h2>`); }
            if (payload.content && payload.content.trim() !== "") {
                let contentToParse = payload.content.trim();
                if (mainTitleTextFromPayload !== "") { const firstLineOfContent = contentToParse.split('\n')[0].trim(); const normalizedMainTitle = mainTitleTextFromPayload.replace(/^#+\s*/, '').toLowerCase(); const normalizedFirstLineContent = firstLineOfContent.replace(/^#+\s*/, '').toLowerCase(); if (normalizedFirstLineContent === normalizedMainTitle) { const lines = contentToParse.split('\n'); lines.shift(); while (lines.length > 0 && lines[0].trim() === "") lines.shift(); contentToParse = lines.join('\n'); } }
                if (contentToParse.trim() !== "") htmlOutput += marked.parse(contentToParse);
            } else if (htmlOutput === "") { htmlOutput += marked.parse("<em>No specific content provided.</em>"); }
            markdownContainer.innerHTML = htmlOutput; return markdownContainer;
        });
    }

// PASTE THIS ENTIRE FUNCTION TO REPLACE THE OLD renderGraph
function renderGraph(type, payload) { 
    displayActiveContent(() => {
        const graphOuterContainer = document.createElement('div'); 
        graphOuterContainer.classList.add('graph-content');
        
        if (payload.title) { 
            const titleElement = document.createElement('h2'); 
            titleElement.classList.add('chart-title'); 
            titleElement.textContent = payload.title; 
            graphOuterContainer.appendChild(titleElement); 
        }
        
        const canvas = document.createElement('canvas'); 
        canvas.style.height = 'clamp(300px, 50vh, 450px)'; 
        canvas.style.width = '100%'; 
        graphOuterContainer.appendChild(canvas);
        
        const ctx = canvas.getContext('2d');
        
        // Enhanced dataset processing
        const datasets = payload.datasets.map(ds => {
            // Start with basic properties
            const datasetConfig = {
                label: ds.label,
                data: ds.values
            };
            
            // Process mixed chart types
            if (type === 'graph_mixed' && ds.chartType) {
                datasetConfig.type = ds.chartType;
            }
            
            // Apply all custom properties from the dataset if defined
            const propertiesToApply = [
                'backgroundColor', 'borderColor', 'borderWidth', 'fill', 'tension',
                'pointStyle', 'pointRadius', 'pointBackgroundColor', 'pointBorderColor',
                'pointHoverBackgroundColor', 'pointHoverBorderColor', 'yAxisID', 
                'xAxisID', 'stack', 'barPercentage', 'categoryPercentage'
            ];
            
            propertiesToApply.forEach(prop => {
                if (ds[prop] !== undefined) {
                    datasetConfig[prop] = ds[prop];
                }
            });
            
            // Apply appropriate defaults based on chart type
            if (type === 'graph_pie' || type === 'graph_doughnut' || type === 'graph_polar') {
                if (datasetConfig.backgroundColor === undefined) {
                    datasetConfig.backgroundColor = [
                        '#3b82f6', '#60a5fa', '#93c5fd', '#bfdbfe', '#dbeafe', '#eff6ff',
                        '#ef4444', '#f87171', '#fca5a5', '#10b981', '#34d399', '#6ee7b7'
                    ].slice(0, ds.values.length);
                }
                if (datasetConfig.borderColor === undefined) {
                    datasetConfig.borderColor = '#100f24';
                }
                if (datasetConfig.borderWidth === undefined) {
                    datasetConfig.borderWidth = 2;
                }
            } else {
                // For bar/line charts
                if (datasetConfig.backgroundColor === undefined) {
                    datasetConfig.backgroundColor = 'rgba(59, 130, 246, 0.3)';
                }
                if (datasetConfig.borderColor === undefined) {
                    datasetConfig.borderColor = 'rgba(59, 130, 246, 1)';
                }
                if (datasetConfig.borderWidth === undefined) {
                    datasetConfig.borderWidth = 1.5;
                }
            }
            
            // Apply line-specific defaults
            if (type === 'graph_line' || ds.chartType === 'line') {
                if (datasetConfig.tension === undefined) {
                    datasetConfig.tension = 0.3;
                }
                
                if (datasetConfig.pointBackgroundColor === undefined) {
                    datasetConfig.pointBackgroundColor = datasetConfig.borderColor;
                }
                if (datasetConfig.pointBorderColor === undefined) {
                    datasetConfig.pointBorderColor = '#fff';
                }
                if (datasetConfig.pointHoverBackgroundColor === undefined) {
                    datasetConfig.pointHoverBackgroundColor = '#fff';
                }
                if (datasetConfig.pointHoverBorderColor === undefined) {
                    datasetConfig.pointHoverBorderColor = datasetConfig.borderColor;
                }
            }
            
            return datasetConfig;
        });
        
        // Determine chart type
        let chartTypeJS;
        if (type === 'graph_mixed') {
            // For mixed charts, individual datasets specify their types
            chartTypeJS = 'bar'; // Default type if not specified
        } else {
            switch(type) {
                case 'graph_bar': chartTypeJS = 'bar'; break;
                case 'graph_line': chartTypeJS = 'line'; break;
                case 'graph_pie': chartTypeJS = 'pie'; break;
                case 'graph_doughnut': chartTypeJS = 'doughnut'; break;
                case 'graph_radar': chartTypeJS = 'radar'; break;
                case 'graph_polar': chartTypeJS = 'polarArea'; break;
                case 'graph_scatter': chartTypeJS = 'scatter'; break;
                case 'graph_bubble': chartTypeJS = 'bubble'; break;
                default: 
                    const errorDiv = document.createElement('div');
                    errorDiv.innerHTML = marked.parse(`<h2>Error</h2><p>Unknown graph type: ${type}</p>`);
                    return errorDiv;
            }
        }
        
        // Prepare chart data
        const chartData = { 
            labels: payload.labels, 
            datasets: datasets 
        };
        
        // Set Chart.js defaults
        Chart.defaults.color = '#9ca3af';
        Chart.defaults.borderColor = '#374151';
        Chart.defaults.font.family = "'Space Grotesk', 'Noto Sans', sans-serif";
        
        // Build chart options
        const chartOptions = {
            responsive: true,
            maintainAspectRatio: false,
            animation: payload.options?.animation || 
                      (payload.options?.animated !== undefined ? 
                      payload.options.animated : 
                      { duration: 800, easing: 'easeInOutQuart' }),
            
            // Set up scales (axes)
            scales: {},
            
            // Set up plugins
            plugins: {
                title: { display: false },
                
                // Configure legend
                legend: {
                    position: 'bottom',
                    display: (payload.datasets.length > 1 && !['graph_pie', 'graph_doughnut', 'graph_polar'].includes(type)) || 
                             (['graph_pie', 'graph_doughnut', 'graph_polar'].includes(type) && payload.labels.length > 1),
                    labels: {
                        color: '#d1d5db',
                        padding: 15,
                        font: {size: 13}
                    }
                },
                
                // Configure tooltip
                tooltip: {
                    backgroundColor: 'rgba(31, 29, 61, 0.9)',
                    titleColor: '#f0f0ff',
                    bodyColor: '#d0d0f0',
                    padding: 12,
                    cornerRadius: 3,
                    titleFont: { weight: 'bold', size: 14 },
                    bodyFont: { size: 13 },
                    boxPadding: 5
                }
            }
        };
        
        // Apply custom scales if provided
        if (payload.options?.scales) {
            chartOptions.scales = payload.options.scales;
        } 
        // Otherwise set up default scales for appropriate chart types
        else if (!['graph_pie', 'graph_doughnut', 'graph_radar', 'graph_polar'].includes(type)) {
            chartOptions.scales.x = {
                title: {
                    display: !!payload.options?.x_axis_label,
                    text: payload.options?.x_axis_label,
                    color: '#d1d5db',
                    font: {size: 13, weight: '500'}
                },
                grid: { color: '#21204b', drawBorder: false },
                ticks: { color: '#9ca3af', font: {size: 12} }
            };
            
            chartOptions.scales.y = {
                title: {
                    display: !!payload.options?.y_axis_label,
                    text: payload.options?.y_axis_label,
                    color: '#d1d5db',
                    font: {size: 13, weight: '500'}
                },
                beginAtZero: true,
                grid: { color: '#21204b', drawBorder: false },
                ticks: {
                    color: '#9ca3af',
                    font: {size: 12},
                    callback: function(value) {
                        if (value >= 1000000) return (value / 1000000) + 'M';
                        if (value >= 1000) return (value / 1000) + 'K';
                        return value;
                    }
                }
            };
        }
        
        // Apply custom tooltip configuration if provided
        if (payload.options?.tooltip) {
            Object.assign(chartOptions.plugins.tooltip, payload.options.tooltip);
            
            // Handle tooltip callbacks for custom formatting
            if (payload.options.tooltip.callbacks) {
                chartOptions.plugins.tooltip.callbacks = {};
                
                Object.entries(payload.options.tooltip.callbacks).forEach(([callbackName, template]) => {
                    chartOptions.plugins.tooltip.callbacks[callbackName] = function(context) {
                        let result = template;
                        
                        // Replace placeholders with actual values
                        if (context.raw !== undefined) {
                            result = result.replace(/\$\{value\}/g, context.raw);
                        }
                        if (context.label !== undefined) {
                            result = result.replace(/\$\{label\}/g, context.label);
                        }
                        if (context.dataset && context.dataset.label !== undefined) {
                            result = result.replace(/\$\{dataset\}/g, context.dataset.label);
                        }
                        
                        return result;
                    };
                });
            }
        }
        
        // Apply custom legend configuration if provided
        if (payload.options?.legend) {
            Object.assign(chartOptions.plugins.legend, payload.options.legend);
        }
        
        // Create the chart
        try {
            if (chartInstance) chartInstance.destroy();
            chartInstance = new Chart(ctx, {
                type: chartTypeJS,
                data: chartData,
                options: chartOptions
            });
        } catch (error) {
            console.error("Chart.js rendering error:", error);
            const errorDiv = document.createElement('div');
            errorDiv.innerHTML = marked.parse(`<h2>Graph Error</h2><p>There was an error rendering the chart. The data or options provided by the assistant might be invalid.</p><p><pre><code>${error.message}</code></pre></p>`);
            graphOuterContainer.innerHTML = '';
            graphOuterContainer.appendChild(errorDiv);
        }
        
        return graphOuterContainer;
    });
}

    function connectWebSocket() {
        const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const wsUrl = `${wsProtocol}//${window.location.host}/ws`;
        
        if (websocket && (websocket.readyState === WebSocket.OPEN || websocket.readyState === WebSocket.CONNECTING)) {
            return;
        }
        
        console.log("Attempting WebSocket connection to web_server.py...");
        if (websocket) { 
            websocket.onopen = null; websocket.onmessage = null; websocket.onerror = null; websocket.onclose = null;
        }
        websocket = null; 
        agentBackendConnected = false; 
        
        updateWsStatusIndicator('status-connecting'); 
        showConnectionStatusBanner("Connecting to display service...", "info");
        updateIdleScreenMessage(); // Should now show "Connecting to display service..."

        websocket = new WebSocket(wsUrl);

        websocket.onopen = () => {
            console.log("WebSocket to web_server.py established.");
            updateWsStatusIndicator('status-connected'); 
            showConnectionStatusBanner("Display service connected.", "connected");
            updateIdleScreenMessage(); // Should now show "Waiting for agent status..."
        };

        websocket.onmessage = (event) => {
            console.log("Message from server (web_server.py): ", event.data);
            try {
                const messageData = JSON.parse(event.data);
                const type = messageData.type;
                const payload = messageData.payload || messageData.status || messageData; 

                if (!type) { console.error("Invalid message: 'type' missing:", messageData); return; }

                if (type === 'connection_status') { 
                    if (payload.connection === 'connected') {
                        agentBackendConnected = true;
                        showConnectionStatusBanner(payload.message || "Agent ready.", "connected");
                    } else { 
                        agentBackendConnected = false;
                        showConnectionStatusBanner(payload.message || "Agent connection issue.", 
                                                   payload.connection === 'disconnected' ? 'disconnected' : 'error');
                    }
                    updateWsStatusIndicator(agentBackendConnected ? 'status-connected' : 'status-disconnected'); // Dot reflects overall agent state now for simplicity
                    updateIdleScreenMessage(); 
                    return; 
                } else if (type === 'new_call_update_available') {
                    if (payload && payload.contact_name && payload.status_summary) {
                        showCallUpdateNotification(payload.contact_name, payload.status_summary, payload.job_id);
                    }
                    return;
                } else if (type === 'thinking_start') {
                    showThinkingPopup();
                    return;
                } else if (type === 'thinking_delta') {
                    if (payload && payload.content) {
                        updateThinkingContent(payload.content);
                    }
                    return;
                } else if (type === 'thinking_end') {
                    hideThinkingPopup();
                    return;
                } else if (type === 'thinking_error') {
                    hideThinkingPopup();
                    if (payload && payload.error) {
                        console.error("Thinking error:", payload.error);
                        showConnectionStatusBanner(`Thinking process error: ${payload.error}`, "error");
                    }
                    return;
                }
                
                if (agentBackendConnected) {
                    if (!messageData.payload && (type === 'markdown' || type.startsWith('graph_') || type === 'html')) { 
                        console.error("Invalid message: 'payload' missing for display type:", messageData);
                        return; 
                    }
                    if (type === 'markdown') renderMarkdown(messageData.payload);
                    else if (type.startsWith('graph_')) renderGraph(type, messageData.payload);
                    else if (type === 'html') { // <<<< NEW CASE
                        const displayPayload = messageData.payload; // Standardizing to use displayPayload for clarity inside this block
        
                        clearAllDynamicContent(true); 
                        setTimeout(() => {
                            const activeContentWrapper = document.createElement('div');
                            activeContentWrapper.id = 'active-content-wrapper';
                            activeContentWrapper.classList.add('animate-fade-in');
                            
                            // displayPayload.content should contain the HTML string
                            if (displayPayload && displayPayload.content && typeof displayPayload.content === 'string') {
                                const htmlContainer = document.createElement('div');
                                htmlContainer.classList.add('html-content-container'); 
                                htmlContainer.style.width = '100%';
                                htmlContainer.style.height = '100%'; 
                                htmlContainer.style.overflow = 'hidden';
        
                                const iframe = document.createElement('iframe');
                                iframe.sandbox = 'allow-scripts'; 
                                
                                iframe.srcdoc = displayPayload.content; 
                                iframe.style.width = '100%';
                                iframe.style.height = '100%'; 
                                iframe.style.border = 'none'; 
                                
                                if (displayPayload.title) {
                                    iframe.setAttribute('title', displayPayload.title);
                                } else {
                                    iframe.setAttribute('title', 'Dynamic HTML Content');
                                }
        
                                htmlContainer.appendChild(iframe);
                                activeContentWrapper.appendChild(htmlContainer);
                            } else {
                                console.error("Received 'html' display type but 'payload.content' was missing or not a string.");
                                const errorDiv = document.createElement('div');
                                errorDiv.innerHTML = (typeof marked !== 'undefined') ?
                                    marked.parse("<h2>Display Error</h2><p>HTML content was missing or invalid.</p>") :
                                    "<h2>Display Error</h2><p>HTML content was missing or invalid.</p>";
                                activeContentWrapper.appendChild(errorDiv);
                            }
                            displayArea.innerHTML = ''; 
                            displayArea.appendChild(activeContentWrapper);
                            resetContentTimeout(); 
                        }, 700); 
                    }

                    else console.warn("Received unhandled display/data message type:", type);
                }
                
                
                else {
                    console.warn("Received display/data message but agent backend is not connected. Ignoring:", messageData);
                }

            } catch (e) { 
                console.error("Failed to parse message or render:", e, "Raw data:", event.data);
            }
        };

        websocket.onclose = (event) => {
            console.log("WebSocket to web_server.py closed. Code:", event.code, "Reason:", event.reason);
            updateWsStatusIndicator('status-disconnected'); 
            agentBackendConnected = false; 
            
            const currentBannerIsError = connectionStatusBanner && connectionStatusBanner.classList.contains('status-error-banner');
            if (!currentBannerIsError) {
                 showConnectionStatusBanner("Display service disconnected. Attempting to reconnect...", "disconnected");
            }
            updateIdleScreenMessage(); 
            
            if (websocket) { websocket.onopen = null; websocket.onmessage = null; websocket.onerror = null; websocket.onclose = null; }
            websocket = null; 
            setTimeout(connectWebSocket, RECONNECT_DELAY_MS);
        };

        websocket.onerror = (event) => {
            console.error("WebSocket error with web_server.py:", event);
            updateWsStatusIndicator('status-error'); 
            agentBackendConnected = false;
            
            showConnectionStatusBanner("Error connecting to display service. Retrying...", "error");
            updateIdleScreenMessage();
            
            if (websocket && (websocket.readyState === WebSocket.OPEN || websocket.readyState === WebSocket.CONNECTING)) {
                // If it's open or connecting and an error occurs, it will likely trigger onclose.
                // No need to call websocket.close() here as it might lead to double onclose handling.
            } else { // If it never opened or is already closed
                if (websocket) { websocket.onopen = null; websocket.onmessage = null; websocket.onerror = null; websocket.onclose = null; }
                websocket = null;
                setTimeout(connectWebSocket, RECONNECT_DELAY_MS);
            }
        };
    }
    
    createNotificationElements(); 
    showIdleState(); 
    connectWebSocket(); 
});