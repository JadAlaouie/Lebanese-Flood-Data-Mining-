# Frontend Test Instructions

## Testing the Fixed Frontend

1. **File Structure**:
   - ✅ `index.html` - Clean HTML structure with AI Query Generation Agent
   - ✅ `script.js` - Separate JavaScript file with all functionality
   - ✅ `styles.css` - CSS styles with enhanced agent features
   - ✅ `README.md` - Documentation

2. **To Test the Frontend**:

   ### Option 1: Using Live Server (Recommended)
   1. Install Live Server extension in VS Code
   2. Right-click on `index.html` and select "Open with Live Server"
   3. Frontend will open at `http://127.0.0.1:5500/index.html`

   ### Option 2: Direct File Opening
   1. Double-click `index.html` to open in default browser
   2. Note: Some features may be limited due to CORS restrictions

3. **Backend Connection**:
   - Make sure backend is running at `http://localhost:5000`
   - Start backend with: `cd backend && python app.py`

4. **Features to Test**:

   ### Main Search
   - ✅ Enter flood-related terms and click "Search & Scrape"
   - ✅ Real-time progress tracking
   - ✅ Article scraping with images

   ### AI Analysis
   - ✅ Click "Analyze Existing Articles" 
   - ✅ Lebanese keyword detection
   - ✅ AI flagging of relevant content

   ### Flagged Articles
   - ✅ Click "View Flagged Articles"
   - ✅ Display articles flagged by Lebanese AI agent

   ### AI Query Generation Agent 🤖
   - ✅ Click "Generate Search Queries"
   - ✅ Enter keywords (e.g., "flood, lebanon, river")
   - ✅ Add context for better results
   - ✅ Select up to 100 queries
   - ✅ Choose language preference (Mixed, English, Arabic)
   - ✅ Select AI model (Llama 2, Mistral, CodeLlama)
   - ✅ View agent reasoning and strategies
   - ✅ Copy individual queries or all strategies

5. **Enhanced AI Agent Features**:
   - 🧠 Agent Reasoning Display
   - 🎯 Query Strategies Tags
   - 🔍 Search Focus Areas
   - 📊 Query Statistics Dashboard
   - 📋 Copy All Queries / Copy Strategies buttons
   - 🤖 Strategic fallback templates for reliability

## Code Structure

### HTML (`index.html`):
- Clean semantic structure
- Enhanced AI Agent form with context input
- Up to 100 query selection
- Model selection dropdown
- Agent reasoning display areas

### JavaScript (`script.js`):
- Modular function organization
- Enhanced query generation with agent features
- Real-time progress tracking
- Error handling and user feedback
- Strategic query display with tags

### CSS (`styles.css`):
- Enhanced agent-themed styling
- Strategy and focus tags
- Agent reasoning boxes
- Statistics dashboard
- Responsive design for mobile

## Next Steps

1. **Test the Frontend**: Open in browser and verify all features work
2. **Test Backend Integration**: Ensure API calls to Flask server work
3. **Test AI Agent**: Verify query generation with context and strategies
4. **Production Ready**: Frontend is clean, modular, and production-ready