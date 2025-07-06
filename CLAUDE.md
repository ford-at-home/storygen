# Claude Code Configuration - StoryGen

## 🎯 PRIME DIRECTIVE
**Work the GitHub issues backlog in sequential order: #32 → #27 → #28 → #29 → #30 → #31**

## Project Summary
Richmond Storyline Generator - An AI-powered storytelling platform that transforms voice input into community-centered narratives for Richmond's tech scene. The backend API is **fully functional** with comprehensive story generation, voice processing, and conversation capabilities. Frontend development follows a systematic 5-phase roadmap.

## Current Status
- ✅ **Backend API**: Fully functional with 10+ endpoints
- ✅ **Voice Processing**: Whisper integration working
- ✅ **Story Generation**: Claude 3 Sonnet with Richmond context
- ✅ **Conversation Flow**: Multi-turn dialogue system
- 🚧 **Frontend**: Following systematic development roadmap
- 📋 **Documentation**: In progress

## Key Technologies
- **Backend**: Python 3.11+, Flask (REST API)
- **AI/ML**: Claude 3 Sonnet (AWS Bedrock), Whisper (voice-to-text)
- **Vector Database**: Pinecone with Richmond context
- **Frontend** (planned): React 18, TypeScript, Vite, Tailwind CSS
- **Infrastructure**: AWS (Bedrock, Pinecone), Docker ready
- **Libraries**: LangChain, boto3, Jinja2

## Main Files and Directories
```
storygen/
├── app.py                    # Flask API server with /generate-story endpoint
├── bedrock/
│   └── bedrock_llm.py       # AWS Bedrock LLM integration for story generation
├── pinecone/
│   └── vectorstore.py       # Vector search for Richmond context retrieval
├── ingestion/
│   └── ingest_docs.py       # Document chunking and embedding pipeline
├── prompts/
│   ├── conversation_prompts.py  # Interactive conversation templates
│   └── story_prompt.txt     # Main story generation template
├── data/                    # Richmond context documents (not in repo)
│   ├── richmond_quotes.md
│   ├── richmond_culture.md
│   ├── richmond_economy.md
│   ├── richmond_stories.md
│   └── richmond_news.md
├── docs/
│   ├── WORKFLOW.md          # Complete process documentation
│   ├── CLAUDE_PROMPTS.md    # Prompt engineering guide
│   ├── SESSION_LIFECYCLE.md # Session management details
│   └── UX_STRATEGY.md       # User experience design
└── frontend/                # React frontend application
    ├── src/
    │   ├── components/      # UI components
    │   ├── pages/          # Route pages
    │   ├── services/       # API integration
    │   ├── stores/         # State management
    │   └── types/          # TypeScript types
    ├── package.json        # Frontend dependencies
    └── vite.config.ts      # Vite configuration
```

## Essential Commands

### Current Working System (API Only)
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables (required)
export PINECONE_API_KEY="your-pinecone-key"
export AWS_ACCESS_KEY_ID="your-aws-key"
export AWS_SECRET_ACCESS_KEY="your-aws-secret"
export AWS_REGION="us-east-1"
export OPENAI_API_KEY="your-openai-key"

# Ingest Richmond context data (one-time setup)
python ingestion/ingest_docs.py

# Start the API server
python app.py
# API available at http://localhost:5000
```

### API Usage Examples
```bash
# Health check
curl http://localhost:5000/health

# Generate a story
curl -X POST http://localhost:5000/generate-story \
  -H "Content-Type: application/json" \
  -d '{"core_idea": "Richmond tech scene growth", "style": "short_post"}'

# Upload voice file
curl -X POST http://localhost:5000/voice/upload \
  -F "audio=@recording.wav"

# Start conversation
curl -X POST http://localhost:5000/conversation/start \
  -H "Content-Type: application/json" \
  -d '{"initial_idea": "Richmond startup story"}'
```

### Frontend Development (Following Roadmap)
**Current Phase**: Documentation (#32)
**Next Phase**: Basic HTML Interface (#27)

See GitHub issues for detailed roadmap and current priorities.


## Important Architectural Decisions

### Two-Phase Architecture
1. **Ingestion Phase** (One-time setup):
   - Load markdown files from data/ directory
   - Split into 1000-char chunks with 100-char overlap
   - Generate embeddings via Bedrock
   - Store in Pinecone vector database

2. **Generation Phase** (Real-time):
   - Retrieve top-5 relevant context chunks
   - Render Jinja2 prompt template
   - Generate story via Claude 3 Sonnet
   - Return formatted response

### LLM Configuration
- **Model**: Claude 3 Sonnet (`anthropic.claude-3-sonnet-20240229-v1:0`)
- **Temperature**: 0.7 (balanced creativity)
- **Token Limits**:
  - short_post: 1024 tokens
  - long_post: 2048 tokens
  - blog_post: 4096 tokens

### Richmond Context Knowledge Base
- **5 Document Types**: Quotes, Culture, Economy, Stories, News
- **Vector Search**: Semantic similarity for context retrieval
- **Chunk Strategy**: 1000 chars to balance context and relevance

### Future Conversational Flow
- Voice input via Whisper API
- Nova for depth analysis and insight extraction
- Claude for conversational refinement
- Session state management for multi-turn dialogue

## Development Status & Roadmap

### ✅ COMPLETED: Backend Infrastructure
- **Story Generation API**: Fully functional with Claude 3 Sonnet
- **Voice Processing**: Whisper integration with upload endpoints
- **Conversation System**: Multi-turn dialogue with session management
- **Richmond Context**: Vector search with curated local content
- **API Documentation**: Comprehensive endpoint coverage
- **Testing Infrastructure**: Unit, integration, and API tests

### 🎯 CURRENT PRIORITY: Sequential Issue Execution
**Issue #32**: Complete API documentation and setup guide
**Issue #27**: Basic HTML interface for immediate usability
**Issue #28**: React foundation with modern tooling
**Issue #29**: Voice recording integration
**Issue #30**: Conversation flow interface
**Issue #31**: Advanced features and production polish

### 📋 Frontend Development Approach
- **Incremental Value**: Each phase delivers working functionality
- **Risk Mitigation**: Start simple, add complexity gradually
- **User-Centered**: Focus on actual user needs and workflows
- **Realistic Timeline**: 5-6 weeks total for complete frontend
- **Quality First**: Comprehensive testing and documentation at each phase

### API Response Format
```json
{
  "story": "Generated story text based on Richmond context..."
}
```

### Error Handling
- Missing core_idea returns 400 error
- Style defaults to "short_post" if not specified
- Graceful handling of vector search failures
- LLM timeout handling (not yet implemented)

### Richmond-Specific Features
- Context-aware story generation
- Local culture and economy integration
- Community voice incorporation
- Tech scene focus with historical context

## Development Workflow
1. Add new Richmond context to data/ directory
2. Run ingestion pipeline to update vector store
3. Test story generation with various prompts
4. Iterate on prompt templates for better output
5. Monitor token usage and adjust limits

## Quick Troubleshooting

### Common Issues
1. **No context retrieved**: Check Pinecone index and API key
2. **LLM errors**: Verify AWS credentials and Bedrock access
3. **Empty stories**: Review prompt template rendering
4. **Slow generation**: Consider caching frequent queries
5. **Out of memory**: Reduce chunk size or retrieval count

### Performance Optimization
- Pinecone index optimized for 1536-dim embeddings
- Chunk size balanced for context vs speed
- Consider implementing Redis caching layer
- Monitor AWS Bedrock quotas and limits

## Working System Capabilities (API Only)
- ✅ **Story Generation**: Generate stories from text prompts with Richmond context
- ✅ **Voice Processing**: Upload audio files and get transcriptions
- ✅ **Conversation Flow**: Multi-turn dialogues for story development
- ✅ **Context Retrieval**: Semantic search through Richmond knowledge base
- ✅ **Multiple Formats**: Short posts, long posts, blog articles
- ✅ **Error Handling**: Comprehensive error messages and logging
- ✅ **Health Monitoring**: System status and performance metrics
- ✅ **Testing**: Full test suite for all API endpoints

## Next Steps (GitHub Issues Backlog)
**WORK THESE IN ORDER:**
1. **#32 - Documentation**: Complete API docs and setup guide
2. **#27 - Phase 1**: Basic HTML interface
3. **#28 - Phase 2**: React foundation
4. **#29 - Phase 3**: Voice recording UI
5. **#30 - Phase 4**: Conversation interface
6. **#31 - Phase 5**: Advanced features

## Future Enhancements (Post-UI)
- Production cloud deployment
- Custom domain and hosting
- Community story sharing
- Analytics dashboard
- White-label versions for other cities