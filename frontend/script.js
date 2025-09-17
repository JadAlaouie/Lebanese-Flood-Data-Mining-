// Flood Data Mining - JavaScript Functionality
// DOM Elements
const searchForm = document.getElementById('searchForm');
const queryInput = document.getElementById('query');
const resultsContainer = document.getElementById('results');
const loadingIndicator = document.getElementById('loading');
const analyzingIndicator = document.getElementById('analyzingLoading');
const flaggedLoadingIndicator = document.getElementById('flaggedLoading');
const analyzeBtn = document.getElementById('analyzeBtn');
const flaggedBtn = document.getElementById('flaggedBtn');
const resultsCount = document.getElementById('resultsCount');
const emptyState = document.getElementById('emptyState');

// Query generation elements
const generateQueriesBtn = document.getElementById('generateQueriesBtn');
const queryGeneration = document.getElementById('queryGeneration');
const keywordsInput = document.getElementById('keywordsInput');
const queryCount = document.getElementById('queryCount');
const languagePreference = document.getElementById('languagePreference');
const generateBtn = document.getElementById('generateBtn');
const cancelGenerateBtn = document.getElementById('cancelGenerateBtn');
const generatedQueries = document.getElementById('generatedQueries');
const queriesList = document.getElementById('queriesList');
const copyQueriesBtn = document.getElementById('copyQueriesBtn');
const newGenerationBtn = document.getElementById('newGenerationBtn');

// ========================================
// SEARCH FUNCTIONALITY
// ========================================

searchForm.addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const query = queryInput.value.trim();
    if (!query) return;

    // Show loading state with progress
    loadingIndicator.style.display = 'block';
    document.getElementById('loadingSubtitle').textContent = 'Starting search...';
    document.getElementById('progressFill').style.width = '0%';
    resultsContainer.innerHTML = '';
    resultsCount.textContent = '';
    emptyState.style.display = 'none';

    // Start the search request (non-blocking)
    const searchPromise = fetch('http://localhost:5000/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query })
    });

    // Start progress polling
    const progressInterval = setInterval(async () => {
        try {
            const progressResponse = await fetch('http://localhost:5000/search-progress');
            const progress = await progressResponse.json();
            
            updateProgressDisplay(progress);
            
            // If completed or error, stop polling
            if (progress.status === 'completed' || progress.status === 'error') {
                clearInterval(progressInterval);
                
                if (progress.status === 'completed') {
                    // Wait a moment then hide loading and show results
                    setTimeout(() => {
                        loadingIndicator.style.display = 'none';
                        if (progress.final_results) {
                            displayResults(progress.final_results);
                        }
                    }, 1000);
                } else if (progress.status === 'error') {
                    loadingIndicator.style.display = 'none';
                    alert('Search failed: ' + (progress.error || 'Unknown error'));
                }
            }
        } catch (error) {
            console.error('Error polling progress:', error);
        }
    }, 1000);

    // Handle the main search response
    try {
        const response = await searchPromise;
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        // The results will be handled by progress polling
    } catch (error) {
        clearInterval(progressInterval);
        loadingIndicator.style.display = 'none';
        console.error('Search error:', error);
        alert('Search failed. Please check if the backend server is running.');
    }
});

// ========================================
// ANALYSIS FUNCTIONALITY
// ========================================

analyzeBtn.addEventListener('click', async function() {
    analyzingIndicator.style.display = 'block';
    resultsContainer.innerHTML = '';
    resultsCount.textContent = '';
    emptyState.style.display = 'none';

    try {
        const response = await fetch('http://localhost:5000/analyze');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        analyzingIndicator.style.display = 'none';
        
        if (data.success) {
            displayAnalysisResults(data);
        } else {
            alert('Analysis failed: ' + (data.error || 'Unknown error'));
        }
    } catch (error) {
        analyzingIndicator.style.display = 'none';
        console.error('Analysis error:', error);
        alert('Analysis failed. Please check if the backend server is running.');
    }
});

// ========================================
// FLAGGED ARTICLES FUNCTIONALITY
// ========================================

flaggedBtn.addEventListener('click', async function() {
    flaggedLoadingIndicator.style.display = 'block';
    resultsContainer.innerHTML = '';
    resultsCount.textContent = '';
    emptyState.style.display = 'none';

    try {
        const response = await fetch('http://localhost:5000/flagged-articles');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        flaggedLoadingIndicator.style.display = 'none';
        
        if (data.success) {
            displayFlaggedResults(data.articles);
        } else {
            alert('Failed to load flagged articles: ' + (data.error || 'Unknown error'));
        }
    } catch (error) {
        flaggedLoadingIndicator.style.display = 'none';
        console.error('Flagged articles error:', error);
        alert('Failed to load flagged articles. Please check if the backend server is running.');
    }
});

// ========================================
// QUERY GENERATION FUNCTIONALITY
// ========================================

// Query Generation Event Listeners
generateQueriesBtn.addEventListener('click', function() {
    queryGeneration.style.display = 'block';
    generatedQueries.style.display = 'none';
    keywordsInput.focus();
});

newGenerationBtn.addEventListener('click', function() {
    generatedQueries.style.display = 'none';
    keywordsInput.focus();
});

cancelGenerateBtn.addEventListener('click', function() {
    queryGeneration.style.display = 'none';
    keywordsInput.value = '';
    document.getElementById('contextInput').value = '';
});

generateBtn.addEventListener('click', async function() {
    const keywords = keywordsInput.value.trim();
    const context = document.getElementById('contextInput').value.trim();
    
    if (!keywords) {
        alert('Please enter some keywords');
        return;
    }

    const keywordList = keywords.split(',').map(k => k.trim()).filter(k => k.length > 0);
    const count = parseInt(queryCount.value);
    const language = languagePreference.value;
    const model = document.getElementById('modelSelection').value;

    try {
        generateBtn.disabled = true;
        generateBtn.textContent = '🤖 Agent Thinking...';
        
        // Show loading in queries list
        queriesList.innerHTML = `
            <div class="query-loading">
                <div class="spinner"></div>
                <p>AI Agent is analyzing context and generating strategic search queries...</p>
                <p class="loading-details">Processing ${count} queries with ${language} language focus</p>
            </div>
        `;
        generatedQueries.style.display = 'block';

        const response = await fetch('http://localhost:5000/generate-queries', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                keywords: keywordList,
                context: context,
                count: count,
                language: language,
                model: model
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        
        if (result.error) {
            throw new Error(result.error);
        }

        displayGeneratedQueries(result);
        
    } catch (error) {
        console.error('Query generation error:', error);
        queriesList.innerHTML = `
            <div style="text-align: center; padding: 20px; color: #f44336;">
                <p><strong>❌ Agent Query Generation Failed</strong></p>
                <p>${error.message}</p>
                <p><small>Make sure the backend server and AI model are running</small></p>
            </div>
        `;
    } finally {
        generateBtn.disabled = false;
        generateBtn.textContent = '🚀 Generate Agent Queries';
    }
});

copyQueriesBtn.addEventListener('click', function() {
    const queries = Array.from(document.querySelectorAll('.query-text'))
        .map(el => el.textContent)
        .join('\n');
    
    navigator.clipboard.writeText(queries).then(function() {
        const originalText = copyQueriesBtn.textContent;
        copyQueriesBtn.textContent = '✅ Copied!';
        copyQueriesBtn.style.background = '#4CAF50';
        
        setTimeout(() => {
            copyQueriesBtn.textContent = originalText;
            copyQueriesBtn.style.background = '';
        }, 2000);
    }).catch(function() {
        alert('Failed to copy queries to clipboard');
    });
});

// ========================================
// DISPLAY FUNCTIONS
// ========================================

function displayGeneratedQueries(data) {
    const queries = data.queries || [];
    const queryStrategies = data.query_strategies || [];
    const searchFocus = data.search_focus || [];
    const languages = data.languages || [];
    
    if (queries.length === 0) {
        queriesList.innerHTML = `
            <div style="text-align: center; padding: 20px; color: #666;">
                <p>No queries generated. Try different keywords or context.</p>
            </div>
        `;
        return;
    }

    // Display agent reasoning if available
    const reasoningElement = document.getElementById('agentReasoning');
    const reasoningContent = document.getElementById('reasoningContent');
    if (data.agent_reasoning) {
        reasoningContent.innerHTML = `<p class="reasoning-text">${data.agent_reasoning}</p>`;
        reasoningElement.style.display = 'block';
    } else {
        reasoningElement.style.display = 'none';
    }

    // Display query strategies if available
    const strategiesDisplay = document.getElementById('queryStrategiesDisplay');
    const strategiesList = document.getElementById('strategiesList');
    if (queryStrategies && queryStrategies.length > 0) {
        const uniqueStrategies = [...new Set(queryStrategies)];
        strategiesList.innerHTML = uniqueStrategies.map(strategy => 
            `<span class="strategy-tag">${strategy}</span>`
        ).join('');
        strategiesDisplay.style.display = 'block';
    } else {
        strategiesDisplay.style.display = 'none';
    }

    // Display search focus areas if available
    const focusDisplay = document.getElementById('searchFocusDisplay');
    const focusList = document.getElementById('focusList');
    if (searchFocus && searchFocus.length > 0) {
        const uniqueFocus = [...new Set(searchFocus)];
        focusList.innerHTML = uniqueFocus.map(focus => 
            `<span class="focus-tag">${focus}</span>`
        ).join('');
        focusDisplay.style.display = 'block';
    } else {
        focusDisplay.style.display = 'none';
    }

    // Display query statistics
    const queriesStats = document.getElementById('queriesStats');
    queriesStats.innerHTML = `
        <div class="stats-summary">
            <div class="stat-item">
                <span class="stat-number">${queries.length}</span>
                <span class="stat-label">Total Queries</span>
            </div>
            <div class="stat-item">
                <span class="stat-number">${data.model_used || 'AI'}</span>
                <span class="stat-label">Model Used</span>
            </div>
            <div class="stat-item">
                <span class="stat-number">${data.language_preference}</span>
                <span class="stat-label">Language</span>
            </div>
            <div class="stat-item">
                <span class="stat-number">${data.agent_mode ? 'Agent' : 'Standard'}</span>
                <span class="stat-label">Mode</span>
            </div>
        </div>
    `;

    // Display queries with enhanced information
    let html = '';
    queries.forEach((query, index) => {
        const strategy = queryStrategies[index] || 'general';
        const focus = searchFocus[index] || 'flood data';
        const lang = languages[index] || 'mixed';
        
        html += `
            <div class="query-item enhanced" data-query="${query.replace(/"/g, '&quot;')}" style="cursor: pointer;">
                <div class="query-text">${query}</div>
                <div class="query-meta enhanced">
                    <span class="query-strategy-tag">${strategy}</span>
                    <span class="query-focus-tag">${focus}</span>
                    <span class="query-language-tag">${lang}</span>
                    <span class="copy-hint">Click to copy</span>
                </div>
            </div>
        `;
    });

    if (data.agent_fallback_queries && data.agent_fallback_queries.length > 0) {
        html += `
            <div class="agent-notice">
                <strong>🤖 Agent Notice:</strong> Used strategic fallback templates for ${data.agent_fallback_queries.length} queries to ensure quality results.
            </div>
        `;
    }

    if (data.supplemented) {
        html += `
            <div class="supplemented-notice">
                <strong>📈 Enhanced:</strong> Agent supplemented queries with strategic variations for better coverage.
            </div>
        `;
    }

    queriesList.innerHTML = html;
    
    // Add click listeners to query items
    document.querySelectorAll('.query-item').forEach(item => {
        item.addEventListener('click', function() {
            const query = this.dataset.query;
            copyQuery(query);
        });
    });

    // Update copy strategies button handler
    const copyStrategiesBtn = document.getElementById('copyStrategiesBtn');
    if (copyStrategiesBtn) {
        copyStrategiesBtn.onclick = function() {
            const strategiesText = queryStrategies.map((strategy, index) => 
                `${index + 1}. ${queries[index]} (Strategy: ${strategy}, Focus: ${searchFocus[index] || 'general'})`
            ).join('\n');
            
            navigator.clipboard.writeText(strategiesText).then(() => {
                const originalText = copyStrategiesBtn.textContent;
                copyStrategiesBtn.textContent = '✅ Strategies Copied!';
                copyStrategiesBtn.style.background = '#4CAF50';
                
                setTimeout(() => {
                    copyStrategiesBtn.textContent = originalText;
                    copyStrategiesBtn.style.background = '';
                }, 2000);
            });
        };
    }
}

function copyQuery(query) {
    navigator.clipboard.writeText(query).then(function() {
        // Show temporary feedback
        const tooltip = document.createElement('div');
        tooltip.textContent = 'Copied!';
        tooltip.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: #4CAF50;
            color: white;
            padding: 8px 16px;
            border-radius: 4px;
            z-index: 1000;
            font-size: 14px;
        `;
        document.body.appendChild(tooltip);
        
        setTimeout(() => {
            document.body.removeChild(tooltip);
        }, 1000);
    }).catch(function() {
        alert('Failed to copy query: ' + query);
    });
}

function updateProgressDisplay(progress) {
    const subtitle = document.getElementById('loadingSubtitle');
    const progressFill = document.getElementById('progressFill');
    
    if (progress.current_step) {
        subtitle.textContent = progress.current_step;
    }
    
    if (progress.progress_percentage !== undefined) {
        progressFill.style.width = progress.progress_percentage + '%';
    }
    
    // Display partial results if available
    if (progress.partial_results && progress.partial_results.length > 0) {
        const results = progress.partial_results;
        const completed = progress.completed_count || 0;
        const total = progress.total_count || results.length;
        
        if (results.length > 0) {
            displayPartialResults(results, completed, total);
        }
    }
}

function displayPartialResults(partialResults, completed, total) {
    // Clear previous partial results
    resultsContainer.innerHTML = '';
    
    // Show progress header
    resultsCount.innerHTML = `
        <div class="results-summary">
            <span class="results-stats">📊 Processing ${total} articles</span>
            <span class="scraped-stats">✅ ${completed} completed</span>
            <span class="analysis-stats">⏳ ${total - completed} remaining</span>
        </div>
    `;
    
    // Display results as they come in
    partialResults.forEach((item, index) => {
        const li = document.createElement('li');
        li.className = 'result-item fade-in';
        li.style.animationDelay = `${index * 0.05}s`;
        
        const title = item.title || 'Processing...';
        const link = item.link || '#';
        const snippet = item.snippet || '';
        const scraped = item.scraped;
        
        // Show processing status
        const statusBadge = scraped 
            ? `<span class="badge badge-success">✅ Scraped (${item.word_count} words)</span>`
            : `<span class="badge badge-warning">⏳ Processing...</span>`;
        
        const imageBadge = item.image_count > 0 
            ? `<span class="badge badge-warning">🖼️ ${item.image_count} images</span>`
            : '';
        
        li.innerHTML = `
            <div class="result-header">
                <div class="result-title">
                    <a href="${link}" target="_blank" class="result-link">${title}</a>
                </div>
                <div class="result-badges">
                    ${statusBadge}
                    ${imageBadge}
                </div>
            </div>
            <div class="result-snippet">${snippet}</div>
            ${scraped && item.full_content ? `
                <div class="scraped-preview">
                    <p><strong>Content Preview:</strong></p>
                    <p class="content-preview">${item.full_content.substring(0, 200)}...</p>
                </div>
            ` : ''}
            ${item.images && item.images.length > 0 ? `
                <div class="scraped-images">
                    <p><strong>Images found:</strong></p>
                    <div class="image-gallery">
                        ${item.images.slice(0, 3).map(img => `
                            <img src="${img}" alt="Article image" class="preview-image" onerror="this.style.display='none'">
                        `).join('')}
                    </div>
                </div>
            ` : ''}
        `;
        
        resultsContainer.appendChild(li);
    });
}

function displayResults(results) {
    resultsContainer.innerHTML = '';
    
    if (!results || results.length === 0) {
        emptyState.style.display = 'block';
        resultsCount.textContent = '';
        return;
    }

    emptyState.style.display = 'none';
    resultsCount.innerHTML = `
        <div class="results-summary">
            <span class="results-stats">📊 Found ${results.length} articles</span>
            <span class="scraped-stats">✅ All completed</span>
        </div>
    `;

    results.forEach((item, index) => {
        const li = document.createElement('li');
        li.className = 'result-item fade-in';
        li.style.animationDelay = `${index * 0.05}s`;
        
        const title = item.title || 'No title';
        const link = item.link || '#';
        const snippet = item.snippet || 'No description available';
        
        const flaggedBadge = item.flagged 
            ? `<span class="badge badge-danger">🚩 Flagged by AI</span>`
            : `<span class="badge badge-success">✅ Clean</span>`;
        
        const imageBadge = item.image_count > 0 
            ? `<span class="badge badge-info">🖼️ ${item.image_count} images</span>`
            : '';
        
        li.innerHTML = `
            <div class="result-header">
                <div class="result-title">
                    <a href="${link}" target="_blank" class="result-link">${title}</a>
                </div>
                <div class="result-badges">
                    ${flaggedBadge}
                    ${imageBadge}
                    <span class="badge badge-info">📝 ${item.word_count} words</span>
                </div>
            </div>
            <div class="result-snippet">${snippet}</div>
            ${item.full_content ? `
                <div class="scraped-preview">
                    <p><strong>Content Preview:</strong></p>
                    <p class="content-preview">${item.full_content.substring(0, 200)}...</p>
                </div>
            ` : ''}
            ${item.images && item.images.length > 0 ? `
                <div class="scraped-images">
                    <p><strong>Images found:</strong></p>
                    <div class="image-gallery">
                        ${item.images.slice(0, 3).map(img => `
                            <img src="${img}" alt="Article image" class="preview-image" onerror="this.style.display='none'">
                        `).join('')}
                    </div>
                </div>
            ` : ''}
        `;
        
        resultsContainer.appendChild(li);
    });
}

function displayAnalysisResults(data) {
    resultsContainer.innerHTML = '';
    
    if (!data.articles || data.articles.length === 0) {
        emptyState.style.display = 'block';
        resultsCount.textContent = 'No articles found for analysis';
        return;
    }

    emptyState.style.display = 'none';
    resultsCount.innerHTML = `
        <div class="results-summary">
            <span class="results-stats">📊 Analyzed ${data.articles.length} articles</span>
            <span class="flagged-stats">🚩 ${data.flagged_count || 0} flagged</span>
            <span class="clean-stats">✅ ${data.articles.length - (data.flagged_count || 0)} clean</span>
        </div>
    `;

    data.articles.forEach((item, index) => {
        const li = document.createElement('li');
        li.className = 'result-item fade-in';
        li.style.animationDelay = `${index * 0.05}s`;
        
        const title = item.title || 'No title';
        const link = item.link || '#';
        const snippet = item.snippet || 'No description available';
        
        const flaggedBadge = item.flagged 
            ? `<span class="badge badge-danger">🚩 Flagged by AI</span>`
            : `<span class="badge badge-success">✅ Clean</span>`;
        
        const imageBadge = item.image_count > 0 
            ? `<span class="badge badge-info">🖼️ ${item.image_count} images</span>`
            : '';
        
        li.innerHTML = `
            <div class="result-header">
                <div class="result-title">
                    <a href="${link}" target="_blank" class="result-link">${title}</a>
                </div>
                <div class="result-badges">
                    ${flaggedBadge}
                    ${imageBadge}
                    <span class="badge badge-info">📝 ${item.word_count || 0} words</span>
                </div>
            </div>
            <div class="result-snippet">${snippet}</div>
            ${item.flagged && item.flagged_keywords ? `
                <div class="flagged-info">
                    <p><strong>🚩 Flagged Keywords:</strong> ${item.flagged_keywords.join(', ')}</p>
                </div>
            ` : ''}
            ${item.full_content ? `
                <div class="scraped-preview">
                    <p><strong>Content Preview:</strong></p>
                    <p class="content-preview">${item.full_content.substring(0, 200)}...</p>
                </div>
            ` : ''}
        `;
        
        resultsContainer.appendChild(li);
    });
}

function displayFlaggedResults(articles) {
    resultsContainer.innerHTML = '';
    
    if (!articles || articles.length === 0) {
        emptyState.style.display = 'block';
        resultsCount.textContent = 'No flagged articles found';
        return;
    }

    emptyState.style.display = 'none';
    resultsCount.innerHTML = `
        <div class="results-summary">
            <span class="flagged-stats">🚩 ${articles.length} flagged articles</span>
        </div>
    `;

    articles.forEach((item, index) => {
        const li = document.createElement('li');
        li.className = 'result-item flagged fade-in';
        li.style.animationDelay = `${index * 0.05}s`;
        
        const title = item.title || 'No title';
        const link = item.link || '#';
        const snippet = item.snippet || 'No description available';
        
        const imageBadge = item.image_count > 0 
            ? `<span class="badge badge-info">🖼️ ${item.image_count} images</span>`
            : '';
        
        li.innerHTML = `
            <div class="result-header">
                <div class="result-title">
                    <a href="${link}" target="_blank" class="result-link">${title}</a>
                </div>
                <div class="result-badges">
                    <span class="badge badge-danger">🚩 AI Flagged</span>
                    ${imageBadge}
                    <span class="badge badge-info">📝 ${item.word_count || 0} words</span>
                </div>
            </div>
            <div class="result-snippet">${snippet}</div>
            ${item.flagged_keywords ? `
                <div class="flagged-info">
                    <p><strong>🚩 Detected Keywords:</strong> ${item.flagged_keywords.join(', ')}</p>
                </div>
            ` : ''}
            ${item.full_content ? `
                <div class="scraped-preview">
                    <p><strong>Content Preview:</strong></p>
                    <p class="content-preview">${item.full_content.substring(0, 200)}...</p>
                </div>
            ` : ''}
        `;
        
        resultsContainer.appendChild(li);
    });
}