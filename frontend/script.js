// Flood Data Mining - JavaScript Functionality
// DOM Elements
const searchForm = document.getElementById('searchForm');
const queryInput = document.getElementById('query');
const resultsContainer = document.getElementById('results');
const loadingIndicator = document.getElementById('loading');
const analyzingIndicator = document.getElementById('analyzingLoading');
const flaggedLoadingIndicator = document.getElementById('flaggedLoading');
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

// Automatically convert pasted queries separated by spaces into newlines
queryInput.addEventListener('paste', function(e) {
    e.preventDefault();
    let pasted = (e.clipboardData || window.clipboardData).getData('text');
    // If pasted text is a long space-separated string, convert to newlines
    if (pasted.split(' ').length > 5 && pasted.indexOf('\n') === -1 && pasted.indexOf(';') === -1) {
        // Split by multiple spaces, then join by newlines
        pasted = pasted.split(/(?<=\S) (?=\S)/g).join('\n');
    }
    document.execCommand('insertText', false, pasted);
});

// ========================================
// SEARCH FUNCTIONALITY
// ========================================

searchForm.addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const query = queryInput.value.trim();
    if (!query) return;

    // Support multiple queries separated by newlines or semicolons
    let queries = query.split(/,|;|\||\n/).map(q => q.trim()).filter(q => q.length > 0);

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
        body: JSON.stringify({ queries })
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
                        // Call displayResults with the final results
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
            // This is a network or parsing error, stop polling
            clearInterval(progressInterval);
        }
    }, 1000);

    // Handle the main search response
    try {
        const response = await searchPromise;
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        // The results will be handled by progress polling, no need to process the response here
    } catch (error) {
        clearInterval(progressInterval);
        loadingIndicator.style.display = 'none';
        console.error('Search error:', error);
        alert('Search failed. Please check if the backend server is running.');
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
                num_queries: count,
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
        .map(el => el.textContent.trim())
        .filter(q => q.length > 0)
        .join(', '); // Each query separated by a comma

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
    
    // Check if partial results are available and display them
    if (progress.partial_results && progress.partial_results.length > 0) {
        displayPartialResults(progress.partial_results);
    }
}

function displayResults(data) {
    resultsContainer.innerHTML = '';
    
    if (!data || !data.results || data.results.length === 0) {
        emptyState.style.display = 'block';
        resultsCount.textContent = 'No results found.';
        return;
    }

    emptyState.style.display = 'none';
    resultsCount.textContent = `Found ${data.total_articles} relevant articles across ${data.total_queries} queries.`;

    data.results.forEach(queryGroup => {
        const queryHeader = document.createElement('h2');
        queryHeader.textContent = `Results for query: "${queryGroup.query}"`;
        resultsContainer.appendChild(queryHeader);

        const groupList = document.createElement('ul');
        queryGroup.articles.forEach((article, index) => {
            const li = document.createElement('li');
            li.className = 'result-item fade-in';
            li.style.animationDelay = `${index * 0.05}s`;
            
            const title = article.title || 'No title';
            const link = article.link || '#';
            const snippet = article.snippet || 'No description available';
            
            const flaggedBadge = article.flagged 
                ? `<span class="badge badge-danger">🚩 Flagged by AI</span>`
                : `<span class="badge badge-success">✅ Clean</span>`;

            const imageBadge = article.image_count > 0 
                ? `<span class="badge badge-info">🖼️ ${article.image_count} images</span>`
                : '';
            
            li.innerHTML = `
                <div class="result-header">
                    <div class="result-title">
                        <a href="${link}" target="_blank" class="result-link">${title}</a>
                    </div>
                    <div class="result-badges">
                        ${flaggedBadge}
                        ${imageBadge}
                        <span class="badge badge-info">📝 ${article.word_count || 0} words</span>
                    </div>
                </div>
                <div class="result-snippet">${snippet}</div>
                ${article.full_content ? `
                    <div class="scraped-preview">
                        <p><strong>Content Preview:</strong></p>
                        <p class="content-preview">${article.full_content.substring(0, 200)}...</p>
                    </div>
                ` : ''}
                ${article.images && article.images.length > 0 ? `
                    <div class="scraped-images">
                        <p><strong>Images found:</strong></p>
                        <div class="image-gallery">
                            ${article.images.slice(0, 3).map(img => `
                                <img src="${img}" alt="Article image" class="preview-image" onerror="this.style.display='none'">
                            `).join('')}
                        </div>
                    </div>
                ` : ''}
            `;
            
            groupList.appendChild(li);
        });
        resultsContainer.appendChild(groupList);
    });
}

// Function to display partial results during scraping (not needed for final display)
function displayPartialResults(partialResults) {
    // This function is no longer needed as the new logic handles a complete response.
    // It's left here to avoid breaking other parts of your code.
    // The new logic in `displayResults` handles the final display.
    console.log("Partial results received but not displayed. Waiting for final response.");
}