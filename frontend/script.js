// Attach handler for Export AI Filtered button (works even if button is dynamically rendered)
function attachExportAIFilteredBtnHandler() {
    console.log('[DEBUG] attachExportAIFilteredBtnHandler called');
    const exportAIFilteredBtn = document.getElementById('exportAIFilteredBtn');
    console.log('[DEBUG] exportAIFilteredBtn element:', exportAIFilteredBtn);
    
    if (!exportAIFilteredBtn) {
        console.log('[DEBUG] exportAIFilteredBtn not found in DOM');
        return;
    }
    
    if (exportAIFilteredBtn.dataset.listenerAttached) {
        console.log('[DEBUG] exportAIFilteredBtn handler already attached');
        return;
    }
    
    console.log('[DEBUG] Attaching event handler to exportAIFilteredBtn');
    
    exportAIFilteredBtn.addEventListener('click', function(e) {
        console.log('[DEBUG] ===== Export Filtered to Excel button clicked =====');
        console.log('[DEBUG] Event:', e);
        
        exportAIFilteredBtn.disabled = true;
        exportAIFilteredBtn.textContent = '⏳ Exporting & Classifying with AI...';
        
        console.log('[DEBUG] Starting fetch to /export-saved-articles-ai');
        
        fetch('http://localhost:5000/export-saved-articles-ai')
            .then(response => {
                console.log('[DEBUG] Got response:', response);
                if (!response.ok) throw new Error('Failed to export filtered Excel');
                return response.blob();
            })
            .then(blob => {
                console.log('[DEBUG] Got blob, size:', blob.size);
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'ai_filtered_saved_articles.xlsx';
                document.body.appendChild(a);
                a.click();
                a.remove();
                window.URL.revokeObjectURL(url);
                console.log('[DEBUG] Download triggered');
            })
            .catch(err => {
                console.error('[DEBUG] Error:', err);
                alert('Export failed: ' + err.message);
            })
            .finally(() => {
                exportAIFilteredBtn.disabled = false;
                exportAIFilteredBtn.textContent = '🤖 Classify & Export Saved Articles';
                console.log('[DEBUG] Export process completed');
            });
    });
    
    exportAIFilteredBtn.dataset.listenerAttached = 'true';
    console.log('[DEBUG] Event handler successfully attached');
}
// script.js
    // Utility functions (if any) can go here

document.addEventListener('DOMContentLoaded', function() {
    console.log('[DEBUG] DOMContentLoaded fired');
    // Always attach the handler on DOMContentLoaded (in case button is present at load)
    attachExportAIFilteredBtnHandler();
    
    // Add a global test function for debugging
    window.testExportButton = function() {
        const btn = document.getElementById('exportAIFilteredBtn');
        console.log('[DEBUG TEST] Button exists:', !!btn);
        if (btn) {
            console.log('[DEBUG TEST] Button visible:', btn.offsetParent !== null);
            console.log('[DEBUG TEST] Button listener attached:', btn.dataset.listenerAttached);
            console.log('[DEBUG TEST] Manually clicking...');
            btn.click();
        }
    };
    
    // --- AI Filtering Button ---
    const filterAIButton = document.getElementById('filterAIButton');
        if (filterAIButton) {
            filterAIButton.addEventListener('click', async function() {
                // Collect all currently displayed articles
                const articles = [];
                document.querySelectorAll('#results li').forEach(li => {
                    const title = li.querySelector('.result-link')?.textContent || '';
                    const link = li.querySelector('.result-link')?.href || '';
                    const snippet = li.querySelector('.result-snippet')?.textContent || '';
                    const content = li.querySelector('.content-preview')?.textContent || '';
                    articles.push({ title, url: link, snippet, content });
                });
                if (articles.length === 0) {
                    alert('No articles to filter.');
                    return;
                }
                filterAIButton.disabled = true;
                filterAIButton.textContent = 'Filtering...';
                try {
                    const res = await fetch('http://localhost:5000/filter-articles-ai', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ articles })
                    });
                    if (!res.ok) throw new Error('AI filtering failed');
                    const data = await res.json();
                    // Display the filtered/extracted info in a modal or below results
                    showAIFilteredResults(data.filtered_results);
                } catch (err) {
                    alert('AI filtering failed: ' + err.message);
                } finally {
                    filterAIButton.disabled = false;
                    filterAIButton.textContent = '🤖 Filter with AI';
                }
            });
        }

        function showAIFilteredResults(filteredResults) {
            // Remove previous filtered results if any
            let aiDiv = document.getElementById('aiFilteredResults');
            if (aiDiv) aiDiv.remove();
            aiDiv = document.createElement('div');
            aiDiv.id = 'aiFilteredResults';
            aiDiv.style.background = '#f5f5f5';
            aiDiv.style.border = '1px solid #ccc';
            aiDiv.style.padding = '16px';
            aiDiv.style.margin = '16px 0';
            aiDiv.innerHTML = '<h3>🤖 AI Filtered/Extracted Information</h3>';
            if (!filteredResults || filteredResults.length === 0) {
                aiDiv.innerHTML += '<p>No relevant information extracted by AI.</p>';
            } else {
                filteredResults.forEach((item, idx) => {
                    aiDiv.innerHTML += `<div style="margin-bottom:12px;"><strong>Article #${idx+1}</strong><pre style="white-space:pre-wrap;background:#fff;border:1px solid #eee;padding:8px;">${typeof item === 'string' ? item : JSON.stringify(item, null, 2)}</pre></div>`;
                });
            }
            const resultsSection = document.querySelector('.results-section');
            if (resultsSection) resultsSection.prepend(aiDiv);
        }

    // Export to Excel functionality
    const exportBtn = document.getElementById('exportExcelBtn');
        if (exportBtn) {
            exportBtn.addEventListener('click', function() {
                exportBtn.disabled = true;
                exportBtn.textContent = '⏳ Exporting...';
                fetch('http://localhost:5000/export-saved-articles')
                    .then(response => {
                        if (!response.ok) throw new Error('Failed to export Excel');
                        return response.blob();
                    })
                    .then(blob => {
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = 'saved_articles.xlsx';
                        document.body.appendChild(a);
                        a.click();
                        a.remove();
                        window.URL.revokeObjectURL(url);
                    })
                    .catch(err => {
                        alert('Export failed: ' + err.message);
                    })
                    .finally(() => {
                        exportBtn.disabled = false;
                        exportBtn.textContent = '⬇️ Export to Excel';
                    });
            });
        }

    // Helper function to wait for an element to be available
    function waitForElement(id, timeout = 5000) {
        return new Promise((resolve, reject) => {
            const element = document.getElementById(id);
            if (element) {
                resolve(element);
                return;
            }
            
            const startTime = Date.now();
            const checkForElement = () => {
                const element = document.getElementById(id);
                if (element) {
                    resolve(element);
                } else if (Date.now() - startTime > timeout) {
                    reject(new Error(`Element with id '${id}' not found within ${timeout}ms`));
                } else {
                    setTimeout(checkForElement, 50);
                }
            };
            checkForElement();
        });
    }

    // ========================================
    // DOM Elements (Non-Saved) - Safely declared globally
    // ========================================
    const searchForm = document.getElementById('searchForm');
    const queryInput = document.getElementById('query');
    const resultsContainer = document.getElementById('results');
    const loadingIndicator = document.getElementById('loading');
    const analyzingIndicator = document.getElementById('analyzingLoading');
    // NOTE: flaggedLoadingIndicator is now defined LOCALLY in loadSavedArticles for robustness
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

    // Saved articles elements (Only the containing section and button remain global)
    const viewSavedBtn = document.getElementById('viewSavedBtn');
    const savedArticlesSection = document.getElementById('savedArticlesSection');
    const closeSavedBtn = document.getElementById('closeSavedBtn');

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
        if (loadingIndicator) loadingIndicator.style.display = 'block';
        const loadingSubtitle = document.getElementById('loadingSubtitle');
        const progressFill = document.getElementById('progressFill');
        if (loadingSubtitle) loadingSubtitle.textContent = 'Starting search...';
        if (progressFill) progressFill.style.width = '0%';
        
        if (resultsContainer) resultsContainer.innerHTML = '';
        if (resultsCount) resultsCount.textContent = '';
        if (emptyState) emptyState.style.display = 'none';

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
                            if (loadingIndicator) loadingIndicator.style.display = 'none';
                            // Call displayResults with the final results
                            if (progress.final_results) {
                                displayResults(progress.final_results);
                            }
                        }, 1000);
                    } else if (progress.status === 'error') {
                        if (loadingIndicator) loadingIndicator.style.display = 'none';
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
            if (loadingIndicator) loadingIndicator.style.display = 'none';
            console.error('Search error:', error);
            alert('Search failed. Please check if the backend server is running.');
        }
    });

    // ========================================
    // QUERY GENERATION FUNCTIONALITY
    // ========================================

    // Query Generation Event Listeners
    generateQueriesBtn.addEventListener('click', function() {
        if (queryGeneration) queryGeneration.style.display = 'block';
        if (generatedQueries) generatedQueries.style.display = 'none';
        if (keywordsInput) keywordsInput.focus();
    });

    newGenerationBtn.addEventListener('click', function() {
        if (generatedQueries) generatedQueries.style.display = 'none';
        if (keywordsInput) keywordsInput.focus();
    });

    cancelGenerateBtn.addEventListener('click', function() {
        if (queryGeneration) queryGeneration.style.display = 'none';
        if (keywordsInput) keywordsInput.value = '';
        const contextInput = document.getElementById('contextInput');
        if (contextInput) contextInput.value = '';
    });

    generateBtn.addEventListener('click', async function() {
        const keywords = keywordsInput ? keywordsInput.value.trim() : '';
        const contextInput = document.getElementById('contextInput');
        const context = contextInput ? contextInput.value.trim() : '';
        
        if (!keywords) {
            alert('Please enter some keywords');
            return;
        }

        const keywordList = keywords.split(',').map(k => k.trim()).filter(k => k.length > 0);
        const count = parseInt(queryCount ? queryCount.value : 10);
        const language = languagePreference ? languagePreference.value : 'mixed';
        const modelSelection = document.getElementById('modelSelection');
        const model = modelSelection ? modelSelection.value : 'gpt-oss:20b';

        try {
            generateBtn.disabled = true;
            generateBtn.textContent = '🤖 Agent Thinking...';
            
            // Show loading in queries list
            if (queriesList) {
                queriesList.innerHTML = `
                    <div class="query-loading">
                        <div class="spinner"></div>
                        <p>AI Agent is analyzing context and generating strategic search queries...</p>
                        <p class="loading-details">Processing ${count} queries with ${language} language focus</p>
                    </div>
                `;
            }
            if (generatedQueries) generatedQueries.style.display = 'block';

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
            if (queriesList) {
                queriesList.innerHTML = `
                    <div style="text-align: center; padding: 20px; color: #f44336;">
                        <p><strong>❌ Agent Query Generation Failed</strong></p>
                        <p>${error.message}</p>
                        <p><small>Make sure the backend server and AI model are running</small></p>
                    </div>
                `;
            }
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
    // SAVED ARTICLES FUNCTIONALITY
    // ========================================

    // Saved Articles Event Listeners
    console.log('Setting up event listeners...');
    console.log('viewSavedBtn:', viewSavedBtn);
    console.log('savedArticlesSection:', savedArticlesSection);

    if (viewSavedBtn && savedArticlesSection) {
        viewSavedBtn.addEventListener('click', async function() {
            console.log('View saved articles button clicked');
            
            // Hide main search results and show saved section
            if (searchForm) searchForm.parentElement.style.display = 'none';
            if (resultsContainer) resultsContainer.parentElement.style.display = 'none';
            
            savedArticlesSection.style.display = 'block';
            
            try {
                await loadSavedArticles();
            } catch (error) {
                console.error('Error in loadSavedArticles:', error);
                alert('Error loading saved articles: ' + error.message);
            }
        });
    } else {
        console.error('Cannot set up saved articles event listener - missing elements');
    }

    if (closeSavedBtn && savedArticlesSection) {
        closeSavedBtn.addEventListener('click', function() {
            savedArticlesSection.style.display = 'none';
            // Show main search results again
            if (searchForm) searchForm.parentElement.style.display = 'block';
            if (resultsContainer) resultsContainer.parentElement.style.display = 'block';
        });
    }


    // Function to save an article
    async function saveArticle(articleData) {
        try {
            console.log('Attempting to save article:', articleData);
            
            const response = await fetch('http://localhost:5000/save-article', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(articleData)
            });

            console.log('Save response status:', response.status);
            
            if (!response.ok) {
                const errorText = await response.text();
                console.error('Server error response:', errorText);
                return { 
                    success: false, 
                    message: `Server error (${response.status}): ${errorText || 'Unknown error'}` 
                };
            }

            const result = await response.json();
            console.log('Save result:', result);
            
            if (result.success) {
                return { success: true, message: result.message || 'Article saved successfully' };
            } else {
                return { success: false, message: result.message || 'Failed to save article' };
            }
        } catch (error) {
            console.error('Error saving article:', error);
            
            // More specific error messages
            if (error.name === 'TypeError' && error.message.includes('fetch')) {
                return { 
                    success: false, 
                    message: 'Cannot connect to server. Make sure the backend server is running on localhost:5000' 
                };
            } else if (error.name === 'SyntaxError') {
                return { 
                    success: false, 
                    message: 'Server returned invalid response format' 
                };
            } else {
                return { 
                    success: false, 
                    message: `Network error: ${error.message}` 
                };
            }
        }
    }

    // Function to load saved articles
    async function loadSavedArticles() {
        let savedArticlesContainer, savedArticlesCount, emptySavedState, flaggedLoadingIndicator;
        try {
            console.log('Loading saved articles...');
            // Wait for all required elements to be available
            savedArticlesContainer = await waitForElement('savedArticlesContainer');
            savedArticlesCount = await waitForElement('savedArticlesCount');
            emptySavedState = await waitForElement('emptySavedState');
            flaggedLoadingIndicator = await waitForElement('flaggedLoading');
            console.log('All elements found successfully');
            // These lines are safe because the elements were successfully found
            savedArticlesContainer.innerHTML = '<li style="text-align: center; padding: 20px;">Loading saved articles...</li>';
            emptySavedState.style.display = 'none';
            flaggedLoadingIndicator.style.display = 'flex'; 
            const response = await fetch('http://localhost:5000/saved-articles');
            const data = await response.json();
            if (response.ok) {
                displaySavedArticles(data.articles);
                savedArticlesCount.textContent = `${data.total_count} saved articles`;
                // Ensure export AI filtered handler is attached after articles are rendered
                console.log('[DEBUG] About to attach handler after loading articles');
                setTimeout(() => {
                    attachExportAIFilteredBtnHandler();
                }, 100);
            } else {
                // Error from the server (e.g., 500 status)
                savedArticlesContainer.innerHTML = '<li style="text-align: center; padding: 20px; color: red;">Error loading saved articles from server.</li>';
                savedArticlesCount.textContent = `0 saved articles`;
            }
        } catch (error) {
            console.error('Error loading saved articles:', error);
            // Handle element lookup failures
            if (error.message && error.message.includes('not found')) {
                alert("Error: Cannot load saved articles. " + error.message + ". Please refresh the page.");
                return;
            }
            // Network/server error handling
            if (savedArticlesContainer) { 
                savedArticlesContainer.innerHTML = `<li style="text-align: center; padding: 20px; color: red;">Failed to load saved articles. Network or server error.</li>`;
            }
            if (savedArticlesCount) {
                savedArticlesCount.textContent = `0 saved articles`;
            }
        } finally {
            // Ensure the loading indicator is hidden
            if (flaggedLoadingIndicator) flaggedLoadingIndicator.style.display = 'none';
        }
    }

    // Function to delete a saved article
    async function deleteSavedArticle(url) {
        try {
            const response = await fetch('http://localhost:5000/delete-saved-article', {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: url })
            });

            const result = await response.json();
            
            if (response.ok && result.success) {
                // Reload saved articles
                await loadSavedArticles();
                return { success: true, message: result.message };
            } else {
                return { success: false, message: result.message || 'Failed to delete article' };
            }
        } catch (error) {
            console.error('Error deleting article:', error);
            return { success: false, message: 'Network error occurred' };
        }
    }

    // Helper to escape HTML special characters
    function escapeHTML(str) {
        if (typeof str !== 'string') return str;
        return str.replace(/[&<>'"`=]/g, function (c) {
            return {
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                "'": '&#39;',
                '"': '&quot;',
                '`': '&#96;',
                '=': '&#61;'
            }[c];
        });
    }

    // Helper to robustly escape JS string for use in single-quoted HTML attributes
    function jsStringEscape(str) {
        if (typeof str !== 'string') return str;
        return str
            .replace(/\\/g, '\\\\')
            .replace(/'/g, "\\'")
            .replace(/\n/g, "\\n")
            .replace(/\r/g, "\\r")
            .replace(/\t/g, "\\t")
            .replace(/\u2028/g, "\\u2028")
            .replace(/\u2029/g, "\\u2029");
    }

    // Function to display saved articles
    function displaySavedArticles(articles) {
        // Look up container locally to ensure it's not null before proceeding
        const savedArticlesContainer = document.getElementById('savedArticlesContainer');
        const emptySavedState = document.getElementById('emptySavedState');
        if (!savedArticlesContainer) return;
        savedArticlesContainer.innerHTML = '';
        if (!articles || articles.length === 0) {
            if (emptySavedState) emptySavedState.style.display = 'block';
            return;
        }
        if (emptySavedState) emptySavedState.style.display = 'none';
        articles.forEach((article, index) => {
            const li = document.createElement('li');
            li.className = 'saved-article-item fade-in';
            li.style.animationDelay = `${index * 0.05}s`;
            const title = escapeHTML(article.title || 'No title');
            const url = escapeHTML(article.url || '#');
            const snippet = escapeHTML(article.snippet || 'No description available');
            const savedDate = new Date(article.saved_at).toLocaleDateString();
            const flaggedBadge = article.flagged 
                ? `<span class="badge badge-danger">🚩 Flagged</span>`
                : `<span class="badge badge-success">✅ Clean</span>`;
            const imageBadge = article.image_count > 0 
                ? `<span class="badge badge-info">🖼️ ${article.image_count} images</span>`
                : '';
            li.innerHTML = `
                <div class="saved-article-header">
                    <div class="saved-article-title">
                        <a href="${url}" target="_blank">${title}</a>
                    </div>
                    <div class="saved-article-actions">
                        <button class="delete-saved-btn" onclick="handleDeleteSavedArticle('${url}')">🗑️ Delete</button>
                    </div>
                </div>
                <div class="saved-article-badges">
                    ${flaggedBadge}
                    ${imageBadge}
                    <span class="badge badge-info">📝 ${article.word_count || 0} words</span>
                </div>
                <div class="saved-article-snippet">${snippet}</div>
                ${article.images && article.images.length > 0 ? `
                    <div class="scraped-images">
                        <p><strong>Images found:</strong></p>
                        <div class="image-gallery">
                            ${article.images.slice(0, 3).map(img => {
                                let url = '';
                                if (typeof img === 'string') {
                                    url = escapeHTML(img);
                                } else if (img && typeof img === 'object' && img.url) {
                                    url = escapeHTML(img.url);
                                } else {
                                    return '';
                                }
                                return `<div class='image-frame'><img src="${url}" alt="Article image" class="preview-image" onerror="this.style.display='none'"></div>`;
                            }).join('')}
                        </div>
                    </div>
                ` : ''}
                <div class="saved-article-meta">Saved on: ${savedDate}</div>
            `;
            savedArticlesContainer.appendChild(li);
        });
        // Attach the export AI filtered handler after DOM update
        console.log('[DEBUG] About to attach handler after displaySavedArticles');
        setTimeout(() => {
            attachExportAIFilteredBtnHandler();
        }, 100);
    }

    // Handle save article button click
    async function handleSaveArticle(button) {
        const originalText = button.textContent;
        button.disabled = true;
        button.textContent = '💾 Saving...';
        try {
            const url = button.dataset.url || '';
            const title = button.dataset.title || 'No title';
            const snippet = button.dataset.snippet || '';
            const fullContent = button.dataset.fullcontent || '';
            const wordCount = parseInt(button.dataset.wordcount || '0', 10);
            const imageCount = parseInt(button.dataset.imagecount || '0', 10);
            const flagged = button.dataset.flagged === '1';
            let images = [];
            try {
                images = JSON.parse(button.dataset.images || '[]');
            } catch (e) {
                console.error("Error parsing images string:", e);
                images = [];
            }
            console.log('Save article button clicked for URL:', url);
            const articleData = {
                url: url,
                title: title,
                snippet: snippet,
                full_content: fullContent,
                word_count: wordCount,
                image_count: imageCount,
                images: images,
                flagged: flagged
            };
            console.log('Prepared article data:', articleData);
            const result = await saveArticle(articleData);
            if (result.success) {
                console.log('Article saved successfully');
                button.textContent = '✅ Saved';
                button.style.background = '#4CAF50';
                button.style.color = 'white';
                setTimeout(() => {
                    button.textContent = '💾 Saved';
                    button.style.background = '';
                    button.style.color = '';
                    button.disabled = false;
                }, 2000);
            } else {
                console.error('Failed to save article:', result.message);
                button.textContent = '❌ Failed';
                button.style.background = '#f44336';
                button.style.color = 'white';
                console.error('Save error details:', result);
                alert('Failed to save article:\n' + result.message);
                setTimeout(() => {
                    button.textContent = originalText;
                    button.style.background = '';
                    button.style.color = '';
                    button.disabled = false;
                }, 3000);
            }
        } catch (error) {
            console.error('Unexpected error in handleSaveArticle:', error);
            button.textContent = '❌ Error';
            button.style.background = '#f44336';
            button.style.color = 'white';
            alert('Unexpected error occurred while saving article: ' + error.message);
            setTimeout(() => {
                button.textContent = originalText;
                button.style.background = '';
                button.style.color = '';
                button.disabled = false;
            }, 3000);
        }
    }

    // Handle delete saved article button click
    async function handleDeleteSavedArticle(url) {
        if (confirm('Are you sure you want to delete this saved article?')) {
            // Find the button and disable it for feedback
            const deleteButtons = document.querySelectorAll(`[onclick*="handleDeleteSavedArticle('${url}')"]`);
            deleteButtons.forEach(btn => {
                btn.disabled = true;
                btn.textContent = 'Deleting...';
            });

            const result = await deleteSavedArticle(url);
            if (result.success) {
                // Success feedback is handled by reloading the list in deleteSavedArticle
            } else {
                alert('Error: ' + result.message);
                // Re-enable button on failure
                deleteButtons.forEach(btn => {
                    btn.disabled = false;
                    btn.textContent = '🗑️ Delete';
                });
            }
        }
    }

    // Expose functions to global scope for HTML access
    window.handleSaveArticle = handleSaveArticle;
    window.handleDeleteSavedArticle = handleDeleteSavedArticle;

    // ========================================
    // DISPLAY FUNCTIONS
    // ========================================

    function displayGeneratedQueries(data) {
        const queries = data.queries || [];
        const queryStrategies = data.query_strategies || [];
        const searchFocus = data.search_focus || [];
        const languages = data.languages || [];
        
        if (!queriesList) return; // Safety check

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
        if (reasoningElement && reasoningContent) {
            if (data.agent_reasoning) {
                reasoningContent.innerHTML = `<p class="reasoning-text">${data.agent_reasoning}</p>`;
                reasoningElement.style.display = 'block';
            } else {
                reasoningElement.style.display = 'none';
            }
        }

        // Display query strategies if available
        const strategiesDisplay = document.getElementById('queryStrategiesDisplay');
        const strategiesList = document.getElementById('strategiesList');
        if (strategiesDisplay && strategiesList) {
            if (queryStrategies && queryStrategies.length > 0) {
                const uniqueStrategies = [...new Set(queryStrategies)];
                strategiesList.innerHTML = uniqueStrategies.map(strategy => 
                    `<span class="strategy-tag">${strategy}</span>`
                ).join('');
                strategiesDisplay.style.display = 'block';
            } else {
                strategiesDisplay.style.display = 'none';
            }
        }

        // Display search focus areas if available
        const focusDisplay = document.getElementById('searchFocusDisplay');
        const focusList = document.getElementById('focusList');
        if (focusDisplay && focusList) {
            if (searchFocus && searchFocus.length > 0) {
                const uniqueFocus = [...new Set(searchFocus)];
                focusList.innerHTML = uniqueFocus.map(focus => 
                    `<span class="focus-tag">${focus}</span>`
                ).join('');
                focusDisplay.style.display = 'block';
            } else {
                focusDisplay.style.display = 'none';
            }
        }

        // Display query statistics
        const queriesStats = document.getElementById('queriesStats');
        if (queriesStats) {
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
        }

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
            if (subtitle) subtitle.textContent = progress.current_step;
        }
        
        if (progress.progress_percentage !== undefined) {
            if (progressFill) progressFill.style.width = progress.progress_percentage + '%';
        }
        
        // Check if partial results are available and display them
        if (progress.partial_results && progress.partial_results.length > 0) {
            displayPartialResults(progress.partial_results);
        }
    }

    function displayResults(data) {
        if (!resultsContainer) return;

        resultsContainer.innerHTML = '';
        
        if (!data || !data.results || data.results.length === 0) {
            if (emptyState) emptyState.style.display = 'block';
            if (resultsCount) resultsCount.textContent = 'No results found.';
            return;
        }

        if (emptyState) emptyState.style.display = 'none';
        if (resultsCount) resultsCount.textContent = `Found ${data.total_articles} relevant articles across ${data.total_queries} queries.`;

        data.results.forEach(queryGroup => {
            const queryHeader = document.createElement('h2');
            queryHeader.textContent = `Results for query: "${queryGroup.query}"`;
            resultsContainer.appendChild(queryHeader);

            const groupList = document.createElement('ul');
            queryGroup.articles.forEach((article, index) => {
                const li = document.createElement('li');
                li.className = 'result-item fade-in';
                li.style.animationDelay = `${index * 0.05}s`;
                
                const title = escapeHTML(article.title || 'No title');
                const link = escapeHTML(article.link || '#');
                const snippet = escapeHTML(article.snippet || 'No description available');
                
                // Handle flagged status from AI analysis
                const isFlagged = article.ai_analysis && article.ai_analysis.is_relevant;

                const flaggedBadge = isFlagged 
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
                            <button class="save-article-btn"
        data-url="${escapeHTML(article.link || '')}"
        data-title="${escapeHTML(article.title || 'No title')}"
        data-snippet="${escapeHTML(article.snippet || '')}"
        data-fullcontent="${escapeHTML(article.full_content || '')}"
        data-wordcount="${article.word_count || 0}"
        data-imagecount="${article.image_count || 0}"
        data-flagged="${isFlagged ? 1 : 0}"
        data-images="${escapeHTML(JSON.stringify(article.images || []))}"
        onclick="handleSaveArticle(this)">💾 Save</button>
                        </div>
                    </div>
                    <div class="result-snippet">${snippet}</div>
                    ${article.full_content ? `
                        <div class="scraped-preview">
                            <p><strong>Content Preview:</strong></p>
                            <p class="content-preview">${escapeHTML(article.full_content.substring(0, 200))}...</p>
                        </div>
                    ` : ''}
                    ${article.images && article.images.length > 0 ? `
                        <div class="scraped-images">
                            <p><strong>Images found:</strong></p>
                            <div class="image-gallery">
                                ${article.images.slice(0, 3).map(img => {
                                    let url = '';
                                    if (typeof img === 'string') {
                                        url = escapeHTML(img);
                                    } else if (img && typeof img === 'object' && img.url) {
                                        url = escapeHTML(img.url);
                                    } else {
                                        return '';
                                    }
                                        return `<div class='image-frame'><img src="${url}" alt="Article image" class="preview-image" onerror="this.style.display='none'"></div>`;
                                }).join('')}
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
        console.log("Partial results received but not displayed. Waiting for final response.");
    }
}); // End of DOMContentLoaded event listener